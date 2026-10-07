"""Official Codex sign-in and execution bridge. Never reads or exports OAuth tokens."""
from __future__ import annotations
import atexit
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from urllib.parse import urlsplit
from .providers import ProviderError, Cancelled
from .graphify_process import OwnedProcess

REGISTRY = {}
REGISTRY_LOCK = threading.RLock()


def find_executable(configured=''):
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
    candidates = [configured, str(root/'vendor'/'codex.exe'), str(root/'vendor'/'codex'), shutil.which('codex')]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and Path(candidate).suffix.lower() not in {'.cmd','.bat','.ps1'}:
            return str(Path(candidate).resolve())
    # npm shims are not executed through a shell; locate their native binary instead.
    npm = Path(os.getenv('APPDATA', str(Path.home()))) / 'npm' / 'node_modules' / '@openai'
    for pattern in ['codex/vendor/**/codex.exe', 'codex/node_modules/@openai/codex-win32-*/vendor/**/codex.exe', 'codex-win32-*/vendor/**/codex.exe']:
        for path in npm.glob(pattern):
            if path.is_file():
                return str(path.resolve())
    raise ProviderError('Codex runtime was not found. Use the Windows release with the bundled runtime, or select an installed native Codex executable in Connections.')


def safe_login_url(url):
    p = urlsplit(url)
    return p.scheme == 'https' and p.hostname in {'auth.openai.com','chatgpt.com','auth0.openai.com'} and not p.username and not p.password


class Codex:
    def __init__(self, root, executable=''):
        self.exe = find_executable(executable)
        self.home = Path(root)/'codex-account'
        self.home.mkdir(parents=True, exist_ok=True)
        try:
            self.home.chmod(0o700)
        except OSError:
            pass
        config = self.home/'config.toml'
        if not config.exists():
            config.write_text('forced_login_method = "chatgpt"\ncli_auth_credentials_store = "auto"\napproval_policy = "never"\nsandbox_mode = "read-only"\nweb_search = "disabled"\n[features]\nshell_tool = false\n',encoding='utf-8')
        self.env = {k:v for k,v in os.environ.items() if not k.endswith(('_API_KEY','_TOKEN')) and k not in {'OPENAI_BASE_URL','CODEX_HOME'}}
        self.env['CODEX_HOME'] = str(self.home)
        self.env['PYTHONIOENCODING'] = 'utf-8'
        self.proc = None
        self.pending = {}
        self.lock = threading.RLock()
        self.sequence = 0
        self.login_id = None
        self.login_error = ''

    def start(self):
        with self.lock:
            if self.proc and self.proc.poll() is None:
                return
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            self.proc = subprocess.Popen([self.exe,'app-server'],cwd=self.home,env=self.env,
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                text=True,encoding='utf-8',errors='strict',bufsize=1,creationflags=flags)
            threading.Thread(target=self._read,args=(self.proc,),daemon=True,name='graphpaper-codex-auth').start()
        self.rpc('initialize',{'clientInfo':{'name':'graphpaper','title':'GraphPaper','version':'0.3.1'}})
        self._send({'method':'initialized','params':{}})

    def _send(self, value):
        with self.lock:
            if not self.proc or self.proc.poll() is not None:
                raise ProviderError('Codex stopped. Reconnect in Connections.')
            self.proc.stdin.write(json.dumps(value,ensure_ascii=False)+'\n')
            self.proc.stdin.flush()

    def _read(self, proc):
        try:
            while True:
                line = proc.stdout.readline(2_000_001)
                if not line:
                    break
                if len(line) > 2_000_000:
                    raise ValueError('Oversized protocol message')
                data = json.loads(line)
                if 'id' in data and 'method' not in data:
                    waiter = self.pending.get(data['id'])
                    if waiter:
                        waiter.put(data)
                elif 'id' in data:
                    # Sign-in needs no command/file permission; never approve agent operations here.
                    self._send({'id':data['id'],'error':{'code':-32601,'message':'GraphPaper does not authorize tool execution through the authentication connection.'}})
                elif data.get('method') == 'account/login/completed':
                    self.login_error = '' if data.get('params',{}).get('success') else 'Sign-in did not complete. Try again.'
        except Exception:
            self.login_error = 'The Codex connection stopped. Reconnect and try again.'
        finally:
            for waiter in list(self.pending.values()):
                waiter.put({'error':{'message':'Codex connection closed'}})

    def rpc(self, method, params=None, timeout=40):
        with self.lock:
            self.sequence += 1
            ident = self.sequence
            waiter = queue.Queue()
            self.pending[ident] = waiter
        try:
            self._send({'id':ident,'method':method,'params':params or {}})
            try:
                value = waiter.get(timeout=timeout)
            except queue.Empty as exc:
                raise ProviderError('Codex did not respond. Check the installed runtime and reconnect.') from exc
            if 'error' in value:
                raise ProviderError(f'Codex could not complete {method}. Reconnect or update the official runtime; no credentials were exposed.')
            return value.get('result',{})
        finally:
            self.pending.pop(ident,None)

    def status(self):
        self.start()
        account = self.rpc('account/read',{'refreshToken':False}).get('account') or {}
        return {'installed':True,'signed_in':account.get('type')=='chatgpt', 'email':account.get('email',''),
                'plan':account.get('planType',''), 'auth_type':account.get('type'), 'error':self.login_error,
                'note':'Uses your Codex/ChatGPT account allowance. JEV is a separate optional service; no API key is required for writing.'}

    def login(self):
        self.start()
        result = self.rpc('account/login/start',{'type':'chatgpt'})
        url = result.get('authUrl','')
        if not safe_login_url(url):
            raise ProviderError('Codex returned an unexpected sign-in destination. No browser was opened.')
        self.login_id = result.get('loginId')
        self.login_error = ''
        webbrowser.open(url)
        return {'started':True,'auth_url':url,'note':'Complete sign-in in your browser, then check connection status. Codex handles the local OAuth callback and credential storage.'}

    def logout(self):
        self.start()
        self.rpc('account/logout')
        return {'signed_in':False}

    def models(self):
        self.start()
        from .reasoning import normalize_model
        rows = []; cursor = None
        for _ in range(10):
            params = {'limit':100}
            if cursor: params['cursor'] = cursor
            result = self.rpc('model/list',params)
            rows.extend(normalize_model(m,'codex') for m in result.get('data',[]) if m.get('model') or m.get('id'))
            cursor = result.get('nextCursor')
            if not cursor: break
        return rows

    def complete(self, system, user, model, job=None, max_calls=80, reasoning_effort="default", timeout_seconds=600):
        if not self.status()['signed_in']:
            raise ProviderError('Sign in with ChatGPT in Connections before using the Codex provider. API-key sessions are not used by this option.')
        if reasoning_effort != 'default':
            from .reasoning import validate_effort
            catalog = self.models()
            info = next((m for m in catalog if m['id']==model),None) if model else next((m for m in catalog if m.get('is_default')),None)
            validate_effort(reasoning_effort, info, 'codex')
        if job:
            job.before_call('Codex',max_calls)
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        with tempfile.TemporaryDirectory(prefix='graphpaper-codex-') as temp:
            output = Path(temp)/'answer.txt'
            args = [self.exe,'exec','--ephemeral','--skip-git-repo-check','--sandbox','read-only','--json',
                    '-c','approval_policy="never"','-c','features.shell_tool=false','-c','web_search="disabled"',
                    '-o',str(output),'-']
            if model:
                args[-1:-1] = ['--model',model]
            if reasoning_effort != 'default':
                args[-1:-1] = ['-c','model_reasoning_effort='+json.dumps(reasoning_effort)]
            prompt = ('You are the prose/structured-output engine inside GraphPaper. This is a text transformation, not a coding task. '
                      'Do not use tools, inspect files, execute commands or access the network. Return only the requested answer.\n\n'
                      + system + '\n\n' + user)
            owned = OwnedProcess(args,cwd=temp,env=self.env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                text=True,encoding='utf-8',errors='replace')
            proc = owned.proc
            started = time.monotonic()
            try:
                first = True
                while True:
                    if job:
                        job.check()
                    if time.monotonic()-started > timeout_seconds:
                        raise ProviderError('Codex exceeded the configured request timeout; the previous document remains intact.')
                    try:
                        stdout, stderr = proc.communicate(input=prompt if first else None,timeout=.5)
                        break
                    except subprocess.TimeoutExpired:
                        first = False
                usage = {}
                for line in stdout.splitlines():
                    try:
                        event = json.loads(line)
                        if event.get('type') == 'turn.completed':
                            usage = event.get('usage',{})
                    except (ValueError,TypeError):
                        continue
                if job:
                    job.record_usage('Codex subscription',usage,model or 'Codex default')
                    if job.receipts:job.receipts[-1]['reasoning_effort']=reasoning_effort
                if proc.returncode or not output.exists():
                    raise ProviderError('Codex could not finish this request. Check sign-in, your subscription usage limit, model availability and the runtime version. No API fallback was attempted.')
                if output.stat().st_size > 2_000_000:
                    raise ProviderError('Codex returned an oversized answer.')
                text = output.read_text(encoding='utf-8').strip()
                if not text:
                    raise ProviderError('Codex returned an empty answer.')
                return text
            finally:
                owned.close()

    def close(self):
        with self.lock:
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    self.proc.kill()


def get_codex(root, executable=''):
    key = (str(Path(root).resolve()),executable)
    with REGISTRY_LOCK:
        if key not in REGISTRY:
            REGISTRY[key] = Codex(root,executable)
        return REGISTRY[key]


def close_all():
    for client in list(REGISTRY.values()):
        client.close()
    REGISTRY.clear()

atexit.register(close_all)

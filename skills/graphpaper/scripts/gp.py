#!/usr/bin/env python3
"""GraphPaper agent skill: a headless host and small loopback API client.

The client uses only Python's standard library. Serving requires the GraphPaper
source dependencies. Writing, voice, System One and persistence remain in the
real backend: this file does not implement a second writing pipeline.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import http.cookiejar
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

MAX_FILE = 20 * 1024 * 1024
MAX_RESPONSE = 100 * 1024 * 1024
ACTIONS = ('graph', 'angles', 'outline', 'draft', 'review', 'revise', 'voice',
           'humanize', 'deslop', 'both', 'system-one-audit', 'science-plan',
           'science-search', 'science-screen', 'science-fulltext', 'science-appraise',
           'science-outline', 'science-draft', 'science-review')


class ClientError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class JobError(ClientError):
    def __init__(self, job: dict):
        super().__init__(job.get('error') or 'GraphPaper job did not complete.')
        self.job = job


class JobTimeout(JobError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ClientError('Redirect refused. GraphPaper must remain on the specified loopback address.', code)


def local_url(value: str) -> str:
    if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{1,5}/?', value):
        raise ValueError('Use http://127.0.0.1:PORT only; remote hosts, proxies and redirects are not supported.')
    if not 1 <= urllib.parse.urlsplit(value).port <= 65535:
        raise ValueError('Port must be between 1 and 65535.')
    return value.rstrip('/')


def api_path(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    decoded = parsed.path
    for _ in range(8):
        new = urllib.parse.unquote(decoded)
        if new == decoded:
            break
        decoded = new
    if (parsed.scheme or parsed.netloc or parsed.fragment or not decoded.startswith('/api/')
            or '\\' in decoded or '..' in decoded.split('/') or '%' in decoded
            or re.search(r'[\x00-\x20\x7f]', value) or '\x00' in decoded):
        raise ValueError('Use an /api/... path, without traversal, fragments or a second host.')
    return value


def identifier(value: str) -> str:
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,200}', value):
        raise ValueError('Use the exact project, voice or job ID returned by GraphPaper.')
    return value


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8')


def read_json(filename: str | None) -> dict:
    raw = sys.stdin.buffer.read(MAX_FILE + 1) if filename == '-' else Path(filename).read_bytes() if filename else b'{}'
    if len(raw) > MAX_FILE:
        raise ValueError('JSON request is too large.')
    value = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError('The request must be a JSON object.')
    return value


def save_bytes(path: Path, data: bytes, overwrite: bool = False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not overwrite:
        with path.open('xb') as out:
            out.write(data)
        return
    if path.is_symlink():
        raise ValueError('Refusing to replace a symlink. Choose a regular output file.')
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(data)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


class Client:
    def __init__(self, url: str, timeout: float = 60):
        self.url = local_url(url)
        self.timeout = timeout
        self.cookies = http.cookiejar.CookieJar()
        # Never pass local manuscript traffic through an environment HTTP proxy.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
                                                 urllib.request.HTTPCookieProcessor(self.cookies))
        self.connected = False

    def _send(self, method: str, path: str, data=None, content_type=None, timeout=None) -> bytes:
        headers = {'X-GraphPaper': '1'}
        if content_type:
            headers['Content-Type'] = content_type
        request = urllib.request.Request(self.url + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=self.timeout if timeout is None else timeout) as response:
                body = response.read(MAX_RESPONSE + 1)
        except urllib.error.HTTPError as error:
            raw = error.read(8000)
            try:
                detail = json.loads(raw).get('detail', 'Request rejected')
            except (ValueError, AttributeError):
                detail = 'Request rejected; inspect local application diagnostics.'
            # Do not echo submitted request fields, including credentials.
            if not isinstance(detail, str):
                detail = 'Validation failed; check the documented request schema.'
            raise ClientError(f'HTTP {error.code}: {detail[:1200]}', error.code) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise ClientError('Loopback request failed or timed out. No automatic retry: inspect current jobs before resubmitting a write or paid action.') from None
        if len(body) > MAX_RESPONSE:
            raise ClientError('Response exceeds the 100 MiB client budget; narrow the request.')
        return body

    def connect(self):
        if not self.connected:
            self._send('GET', '/')
            if not any(c.name == 'gp_session' for c in self.cookies):
                raise ClientError('The server did not establish a GraphPaper session.')
            self.connected = True

    def request(self, method: str, path: str, body=None, *, binary=False, timeout=None):
        path = api_path(path)
        if method not in {'GET', 'POST', 'PUT', 'PATCH', 'DELETE'}:
            raise ValueError('Unsupported HTTP method.')
        encoded = json_bytes(body) if body is not None else None
        if encoded is not None and len(encoded) > 26 * 1024 * 1024:
            raise ValueError('Request exceeds GraphPaper\'s transport budget.')
        self.connect()
        data = self._send(method, path, encoded, 'application/json' if body is not None else None, timeout)
        if binary:
            return data
        try:
            return json.loads(data)
        except ValueError:
            raise ClientError('GraphPaper returned non-JSON data; use export for binary files.') from None

    def upload(self, path: str, filename: Path, role: str | None = None):
        path = api_path(path)
        if role not in {None, 'evidence', 'canon', 'inspiration', 'voice'}:
            raise ValueError('Unknown source role.')
        filename = Path(filename)
        if filename.stat().st_size > MAX_FILE:
            raise ValueError('Upload exceeds 20 MiB. Nothing was submitted.')
        with filename.open('rb') as stream:
            data = stream.read(MAX_FILE + 1)
        if len(data) > MAX_FILE:
            raise ValueError('Upload grew past the size limit.')
        name = re.sub(r'[\r\n"\\]', '_', filename.name)
        boundary = 'GraphPaper' + uuid.uuid4().hex
        body = bytearray()
        if role:
            body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="role"\r\n\r\n{role}\r\n'.encode())
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode('utf-8'))
        body.extend(data)
        body.extend(f'\r\n--{boundary}--\r\n'.encode())
        self.connect()
        return json.loads(self._send('POST', path, bytes(body), 'multipart/form-data; boundary=' + boundary))

    def wait(self, jid: str, seconds: float = 1800, interval: float = .5):
        jid = identifier(jid)
        if seconds <= 0 or interval <= 0:
            raise ValueError('Polling deadline and interval must be positive.')
        deadline = time.monotonic() + seconds
        job = {'id': jid, 'state': 'unknown'}
        while time.monotonic() < deadline:
            job = self.request('GET', '/api/jobs/' + jid, timeout=min(self.timeout, max(.01, deadline-time.monotonic())))
            if job.get('state') == 'completed':
                return job
            if job.get('state') in {'failed', 'cancelled'}:
                raise JobError(job)
            if job.get('state') not in {'queued', 'running'}:
                raise ClientError('Unknown job state; do not assume the job succeeded.')
            time.sleep(min(interval, max(0, deadline-time.monotonic())))
        raise JobTimeout({**job, 'error': 'Polling deadline reached. The job may still be running; resume with wait or explicitly cancel this job ID. Do not start it again.'})

    def configure(self, changes: dict, key_env: list[str], allow_cloud: bool = False):
        if changes.get('allow_cloud') and not allow_cloud:
            raise ValueError('Enabling cloud processing requires the explicit --allow-cloud flag and the user\'s authorization.')
        if 'api_keys' in changes:
            raise ValueError('Use --key-env instead of putting secrets in a JSON file.')
        keys = {}
        for item in key_env:
            slot, sep, name = item.partition('=')
            if not sep or slot not in {'llm', 'openrouter', 'typesafe'} or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name):
                raise ValueError('Use --key-env typesafe=ENVIRONMENT_VARIABLE (or llm/openrouter).')
            if not os.environ.get(name):
                raise ValueError('The specified credential environment variable is not set.')
            keys[slot] = os.environ[name]
        current = self.request('GET', '/api/settings')
        if keys and current.get('remember_keys') and any(current.get('keys', {}).values()):
            raise ClientError('Persistent credentials already exist. Reuse them, or explicitly authorize clearing saved credentials separately before provisioning temporary keys.')
        for field in ('keys', 'key_storage', 'effective_jev', 'data_directory'):
            current.pop(field, None)
        value = {**current, **changes}
        if allow_cloud:
            value['allow_cloud'] = True
        if keys:
            value['api_keys'] = keys
            value['remember_keys'] = False
        return self.request('PUT', '/api/settings', value)


@contextmanager
def workspace_lock(root: Path, adopt=False):
    """One skill host per workspace; never silently open the desktop database."""
    root = Path(root).expanduser().absolute()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    marker = root / '.graphpaper-agent.json'
    if (root/'studio.sqlite3').exists() and not marker.exists() and not adopt:
        raise ClientError('This is an existing non-agent workspace. Use a separate directory or --adopt-workspace only after explicit permission and after closing the desktop app.')
    stream = (root/'.graphpaper-agent.lock').open('a+b')
    acquired = False
    try:
        # Windows byte-range locks may extend beyond EOF. Do not read or
        # initialize the byte first: an existing mandatory lock denies that IO
        # before we can translate contention into the expected ClientError.
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except OSError:
            raise ClientError('An agent host already owns this workspace; use its URL rather than starting a second host.') from None
        if not marker.exists():
            save_bytes(marker, json_bytes({'format':'graphpaper-agent-workspace-1'}))
        yield root.resolve()
    finally:
        if acquired:
            stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        stream.close()


def serve(repo: str | None, data_dir: str, port: int, adopt=False):
    if not 1 <= port <= 65535:
        raise ValueError('Port must be between 1 and 65535.')
    candidate = Path(repo or os.environ['GRAPHPAPER_REPO']).expanduser().resolve() if repo or os.environ.get('GRAPHPAPER_REPO') else None
    if candidate is None:
        candidate = next((p for p in Path(__file__).resolve().parents if (p/'graphpaper/server.py').is_file()), None)
    if candidate:
        if not (candidate/'graphpaper/server.py').is_file():
            raise ValueError('--repo must name a GraphPaper source checkout, not the Windows executable folder.')
        sys.path.insert(0, str(candidate))
    try:
        import graphpaper
        from graphpaper.server import create_app
        import uvicorn
    except ModuleNotFoundError:
        raise ClientError('Install the GraphPaper source requirements in this Python environment. Supply --repo or GRAPHPAPER_REPO after copying the skill elsewhere. No desktop dependencies are needed.') from None
    if candidate and not Path(graphpaper.__file__).resolve().is_relative_to(candidate):
        raise ClientError('A different GraphPaper package was already imported. Use a fresh Python process.')
    version = tuple(int(x) for x in graphpaper.__version__.split('.')[:3])
    if version < (0, 7, 1):
        raise ClientError('This skill requires the GraphPaper 0.7.1 or newer backend with System One support.')
    with workspace_lock(Path(data_dir), adopt=adopt) as root:
        app = create_app(root)
        print(json.dumps({'status':'starting', 'url':f'http://127.0.0.1:{port}', 'data_directory':str(root), 'version':graphpaper.__version__}), flush=True)
        try:
            # One process only: jobs, session cookies and in-memory keys are process-local.
            uvicorn.run(app, host='127.0.0.1', port=port, access_log=False, log_level='warning')
        finally:
            for job in app.state.runner.jobs.values():
                job.cancel.set()
            app.state.runner.pool.shutdown(wait=False, cancel_futures=True)


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default=os.environ.get('GRAPHPAPER_AGENT_URL','http://127.0.0.1:8765'))
    parser.add_argument('--timeout', type=float, default=60, help='HTTP request timeout in seconds; never auto-retries writes')
    sub = parser.add_subparsers(dest='command', required=True)
    host = sub.add_parser('serve', help='Run the actual backend without a browser, .NET or desktop window')
    host.add_argument('--repo');host.add_argument('--data-dir', required=True);host.add_argument('--port', type=int, default=8765)
    host.add_argument('--adopt-workspace', action='store_true')
    sub.add_parser('doctor', help='Read local configuration and data directory; no provider call')
    call = sub.add_parser('api', help='Call an existing GraphPaper JSON endpoint')
    call.add_argument('method', choices=['GET','POST','PATCH','PUT','DELETE']);call.add_argument('path');call.add_argument('--json-file')
    config = sub.add_parser('configure', help='Merge settings and optional environment-supplied keys')
    config.add_argument('--json-file');config.add_argument('--key-env', action='append', default=[]);config.add_argument('--allow-cloud', action='store_true')
    upload = sub.add_parser('upload', help='Upload directly once, rather than also copying into Inbox')
    target=upload.add_mutually_exclusive_group(required=True);target.add_argument('--project');target.add_argument('--voice')
    upload.add_argument('--role',choices=['evidence','canon','inspiration','voice'],default='evidence');upload.add_argument('file')
    run=sub.add_parser('job',help='Start one job, record its ID, and wait for the actual result')
    run.add_argument('project');run.add_argument('action',choices=ACTIONS);run.add_argument('--instruction-file');run.add_argument('--wait-seconds',type=float,default=1800)
    wait=sub.add_parser('wait',help='Resume polling an existing job without submitting it again')
    wait.add_argument('job');wait.add_argument('--wait-seconds',type=float,default=1800)
    cancel=sub.add_parser('cancel',help='Request cancellation of one exact job ID');cancel.add_argument('job')
    export=sub.add_parser('export',help='Save a project or voice export without a native Save As dialog')
    export.add_argument('path',help='Existing /api/.../export/... route');export.add_argument('destination');export.add_argument('--overwrite',action='store_true')
    for command in (call,config,upload,run,wait):
        command.add_argument('--output');command.add_argument('--overwrite',action='store_true')
    args=parser.parse_args(argv)
    try:
        if args.timeout <= 0:
            raise ValueError('HTTP timeout must be positive.')
        if args.command=='serve':
            serve(args.repo,args.data_dir,args.port,args.adopt_workspace);return 0
        output = getattr(args, 'output', None) or (args.destination if args.command == 'export' else None)
        if output and Path(output).exists() and not getattr(args, 'overwrite', False):
            raise FileExistsError('Output already exists; choose a new path or explicitly --overwrite before doing work.')
        client=Client(args.url,args.timeout)
        if args.command=='doctor':
            b=client.request('GET','/api/bootstrap');s=b['settings']
            result={'ready':True,'version':b['version'],'data_directory':s['data_directory'],
                    'projects':b['projects'],'jobs':b['jobs'],'provider':s['provider'],'model':s['model'],
                    'allow_cloud':s['allow_cloud'],'jev_route':s['effective_jev'],'keys_configured':s['keys'],
                    'graph_engine':s['graph_engine'],'max_calls':s['max_calls']}
        elif args.command=='api':
            result=client.request(args.method,args.path,read_json(args.json_file) if args.json_file or args.method=='POST' else None)
        elif args.command=='configure':
            result=client.configure(read_json(args.json_file),args.key_env,args.allow_cloud)
        elif args.command=='upload':
            path='/api/voices/'+identifier(args.voice)+'/samples/file' if args.voice else '/api/projects/'+identifier(args.project)+'/sources/file'
            result=client.upload(path,Path(args.file),None if args.voice else args.role)
        elif args.command=='job':
            instruction=Path(args.instruction_file).read_text(encoding='utf-8-sig') if args.instruction_file else ''
            if len(instruction)>8000: raise ValueError('Instruction exceeds the backend limit of 8,000 characters; it was not truncated.')
            if args.wait_seconds<=0: raise ValueError('Waiting deadline must be positive.')
            result=client.request('POST','/api/projects/'+identifier(args.project)+'/jobs',{'action':args.action,'instruction':instruction})
            print(json.dumps({'submitted_job':result['id'],'action':args.action}),file=sys.stderr,flush=True)
            result=client.wait(result['id'],args.wait_seconds)
        elif args.command=='wait':
            result=client.wait(args.job,args.wait_seconds)
        elif args.command=='cancel':
            result=client.request('POST','/api/jobs/'+identifier(args.job)+'/cancel',{})
        else:
            data=client.request('GET',args.path,binary=True)
            save_bytes(Path(args.destination),data,args.overwrite)
            result={'saved':str(Path(args.destination).resolve()),'bytes':len(data)}
        if getattr(args,'output',None):
            save_bytes(Path(args.output),json_bytes(result),args.overwrite)
            result={'saved':str(Path(args.output).resolve())}
        print(json.dumps(result,ensure_ascii=False,allow_nan=False))
        return 0
    except (ClientError,ValueError,OSError) as error:
        result={'ok':False,'error':str(error)}
        if isinstance(error,ClientError): result['status']=error.status
        if isinstance(error,JobError): result['job']=error.job
        print(json.dumps(result,ensure_ascii=False),file=sys.stderr)
        return 4 if isinstance(error,JobTimeout) else 3 if isinstance(error,JobError) else 2
    except KeyboardInterrupt:
        print(json.dumps({'ok':False,'error':'Interrupted. A submitted job may still be running; inspect its ID before retrying.'}),file=sys.stderr)
        return 130


if __name__=='__main__':
    raise SystemExit(main())

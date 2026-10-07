"""Job-scoped loopback OpenAI-compatible bridge to the configured GraphPaper provider.

Only Graphify's two-message text extraction is accepted. No tools, arbitrary
models, forwarding destinations, browser origins or public listener are exposed.
"""
from __future__ import annotations
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import secrets
import threading
import time
from .providers import Cancelled, ProviderError

MAX_REQUEST_BYTES = 6_000_000


class JobScope:
    """Deadline/cancellation and frozen accounting for a single external run."""
    def __init__(self, parent, seconds):
        self.parent=parent; self.deadline=time.monotonic()+seconds
        self.stop=threading.Event(); self.closed=False
        self.lock=threading.RLock()

    @property
    def cancel(self): return self.parent.cancel
    @property
    def receipts(self): return self.parent.receipts
    @property
    def usage(self): return self.parent.usage
    def check(self):
        self.parent.check()
        if self.stop.is_set(): raise Cancelled('Graphify request stopped.')
        if time.monotonic()>=self.deadline: raise ProviderError('Graphify exceeded the configured extraction timeout.')
    def note(self,*a,**k):
        with self.lock:
            if not self.closed:
                self.check(); self.parent.note(*a,**k)
    def before_call(self,*a,**k):
        with self.lock:
            self.check(); self.parent.before_call(*a,**k)
    def record_usage(self,*a,**k):
        with self.lock:
            # After cancellation, a non-interruptible API response can still be
            # billed. Never mutate an already-persisted project's accounting.
            if not self.closed: self.parent.record_usage(*a,**k)
    def close(self):
        with self.lock:
            self.closed=True; self.stop.set()


class Gateway:
    def __init__(self, clients, scope):
        self.clients=clients; self.scope=scope
        self.token='gp-graphify-'+secrets.token_urlsafe(40)
        self.model='graphpaper-extraction'  # a fixed local alias, never a provider selector
        self.lock=threading.Lock()
        self.error=None; self.completed=0; self.receipts=[]
        self.active=threading.Event()
        outer=self
        class Handler(BaseHTTPRequestHandler):
            protocol_version='HTTP/1.0'
            def log_message(self,*args): pass
            def setup(self):
                super().setup(); self.connection.settimeout(5)
            def send_json(self,status,value):
                data=json.dumps(value,ensure_ascii=False,allow_nan=False).encode()
                try:
                    self.send_response(status); self.send_header('Content-Type','application/json')
                    self.send_header('Content-Length',str(len(data))); self.send_header('Cache-Control','no-store')
                    self.end_headers(); self.wfile.write(data)
                except (BrokenPipeError,ConnectionResetError,TimeoutError): pass
            def allowed(self):
                host=f'127.0.0.1:{self.server.server_port}'
                if self.headers.get('Host')!=host or self.headers.get('Origin') or self.headers.get('Transfer-Encoding'):
                    self.send_json(403,{'error':{'message':'Graphify local request refused.'}}); return False
                expected='Bearer '+outer.token
                if not hmac.compare_digest(self.headers.get('Authorization',''),expected):
                    self.send_json(401,{'error':{'message':'Graphify job authorization required.'}}); return False
                return True
            def do_GET(self):
                if not self.allowed(): return
                if self.path=='/v1/models':
                    self.send_json(200,{'object':'list','data':[{'id':outer.model,'object':'model','owned_by':'graphpaper'}]})
                else: self.send_json(404,{'error':{'message':'No such gateway operation.'}})
            def do_POST(self):
                if not self.allowed(): return
                if self.path!='/v1/chat/completions':
                    self.send_json(404,{'error':{'message':'No such gateway operation.'}}); return
                try:
                    size=int(self.headers.get('Content-Length','0'))
                    if size<1 or size>MAX_REQUEST_BYTES: raise ValueError('Invalid request length.')
                    data=self.rfile.read(size)
                    if len(data)!=size: raise ValueError('Incomplete request.')
                    raw=json.loads(data,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Non-finite input.')))
                    system,user=outer.parse(raw)
                except (ValueError,TypeError,TimeoutError):
                    self.send_json(400,{'error':{'message':'Graphify must send bounded, non-streamed text extraction messages.'}}); return
                if not outer.lock.acquire(blocking=False):
                    self.send_json(409,{'error':{'message':'One Graphify inference request at a time.'}}); return
                try:
                    outer.scope.check()
                    if outer.error: raise ProviderError('An earlier extraction request failed; no retry was attempted.')
                    outer.active.set()
                    outer.scope.note(f'Graphify: extracting document relationships (model call {outer.completed+1}).')
                    before=dict(outer.scope.usage)
                    value=outer.clients.complete(system,user,role='extraction',json_mode=True,
                                                max_tokens=outer.clients.settings.max_output_tokens)
                    outer.scope.check()
                    if not isinstance(value,dict) or not isinstance(value.get('nodes'),list) or not isinstance(value.get('edges'),list):
                        raise ProviderError('The extraction model returned malformed graph JSON; the previous graph was preserved.')
                    content=json.dumps(value,ensure_ascii=False,allow_nan=False)
                    if len(content.encode())>6_000_000: raise ProviderError('The extraction graph response exceeded its limit.')
                    outer.completed+=1
                    after=outer.scope.usage
                    usage={'prompt_tokens':max(0,after.get('input_tokens',0)-before.get('input_tokens',0)),
                           'completion_tokens':max(0,after.get('output_tokens',0)-before.get('output_tokens',0))}
                    usage['total_tokens']=sum(usage.values())
                    outer.receipts.append({'call':outer.completed,'model':outer.clients.settings.extraction_model or outer.clients.settings.model or 'provider default',
                        'provider':outer.clients.settings.provider,'reasoning_effort':outer.clients.settings.extraction_reasoning_effort,**usage})
                    self.send_json(200,{'id':'graphpaper-'+str(outer.completed),'object':'chat.completion','created':int(time.time()),
                        'model':outer.model,'choices':[{'index':0,'message':{'role':'assistant','content':content},'finish_reason':'stop'}],'usage':usage})
                except (ValueError,ProviderError,Cancelled) as exc:
                    outer.error=exc
                    self.send_json(400,{'error':{'message':'GraphPaper extraction failed or stopped; see its job status.'}})
                except Exception:
                    outer.error=ProviderError('The Graphify model bridge failed; the previous graph was preserved.')
                    self.send_json(500,{'error':{'message':'GraphPaper extraction bridge failed.'}})
                finally:
                    outer.active.clear(); outer.lock.release()
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.server.daemon_threads=True; self.server.block_on_close=False
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.1},name='graphpaper-graphify-gateway',daemon=True)
        self.thread.start()

    @property
    def url(self): return f'http://127.0.0.1:{self.server.server_port}/v1'

    def parse(self,raw):
        if not isinstance(raw,dict) or raw.get('model')!=self.model or raw.get('stream') or raw.get('tools') or raw.get('functions'):
            raise ValueError('Unsupported request.')
        messages=raw.get('messages')
        if not isinstance(messages,list) or len(messages)!=2 or [m.get('role') for m in messages if isinstance(m,dict)]!=['system','user']:
            raise ValueError('Expected extraction messages.')
        def content(m):
            value=m.get('content')
            if isinstance(value,list):
                if not all(isinstance(v,dict) and v.get('type')=='text' and isinstance(v.get('text'),str) for v in value):
                    raise ValueError('Only text is allowed.')
                value='\n'.join(v['text'] for v in value)
            if not isinstance(value,str) or not value.strip(): raise ValueError('Expected text.')
            return value
        system,user=map(content,messages)
        if len(system)+len(user)>self.clients.settings.context_chars: raise ValueError('Context limit.')
        return system,user

    def close(self):
        self.scope.stop.set()
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=2)
        # Codex checks cancellation while awaiting the child. An in-flight API
        # HTTP request may take longer and is explicitly not advertised as free.
        deadline=time.monotonic()+6
        while self.active.is_set() and time.monotonic()<deadline: time.sleep(.05)
        self.scope.close()

    def __enter__(self): return self
    def __exit__(self,*args): self.close()

"""Loopback-only synthetic model server for testing the compiled application."""
import json
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer


class FixtureServer:
    def __init__(self):
        self.requests=[]
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def respond(self,value):
                payload=json.dumps(value).encode()
                self.send_response(200);self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
            def do_GET(self):
                self.respond({'data':[{'id':'fixture-writer','reasoning_efforts':['low','high']},{'id':'fixture-extractor','reasoning_efforts':['low','high']}]})
            def do_POST(self):
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<6000000:self.send_error(400);return
                value=json.loads(self.rfile.read(size));owner.requests.append(value)
                graph={'nodes':[{'id':'eva','label':'Eva','file_type':'document','source_file':'source-0001.md'},
                    {'id':'observatory','label':'Observatory','file_type':'document','source_file':'source-0001.md'},
                    {'id':'grant','label':'Research grant','file_type':'document','source_file':'source-0002.md'}],
                    'edges':[{'source':'eva','target':'observatory','relation':'maintains','confidence':'EXTRACTED','source_file':'source-0001.md'},
                        {'source':'grant','target':'observatory','relation':'funds','confidence':'EXTRACTED','source_file':'source-0002.md'}]}
                self.respond({'id':'synthetic-response','object':'chat.completion','model':value.get('model'),
                    'choices':[{'index':0,'message':{'role':'assistant','content':json.dumps(graph)},'finish_reason':'stop'}],
                    'usage':{'prompt_tokens':120,'completion_tokens':90,'cost':0.0}})
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.server.daemon_threads=True
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    @property
    def url(self):return f'http://127.0.0.1:{self.server.server_port}/v1'
    def close(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=3)
    def __enter__(self):return self
    def __exit__(self,*args):self.close()

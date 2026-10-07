"""Actual browser/provider-transport checks with public Graphify and synthetic model replies."""
from pathlib import Path
import argparse
import json
import socket
import sys
import tempfile
import threading
import time
import traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from graphpaper.server import create_app
from playwright.sync_api import sync_playwright
from graphify_ui_checks import exercise
import uvicorn


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'test-results/graphify-ui')
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    report={'real_http_browser':True,'real_graphify_process':True,'live_model':False,'checks':[],'page_errors':[],'ok':False}
    def check(label):report['checks'].append(label);print('PASS',label,flush=True)
    with tempfile.TemporaryDirectory(prefix='GraphPaper-graphify-browser-') as temp:
        app=create_app(Path(temp));sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        server=uvicorn.Server(uvicorn.Config(app,log_level='error'))
        thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
        deadline=time.monotonic()+15
        while not server.started and time.monotonic()<deadline:time.sleep(.05)
        assert server.started
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            page=browser.new_page(viewport={'width':1440,'height':1040});page.set_default_timeout(15000)
            page.on('pageerror',lambda err:report['page_errors'].append(str(err)))
            try:
                page.goto(f'http://127.0.0.1:{port}/');page.wait_for_selector('.welcome')
                page.get_by_role('button',name='New project',exact=True).click()
                page.locator('#project-title').fill('External Graphify UI fixture')
                page.get_by_role('button',name='Create project',exact=True).click();page.wait_for_selector('#dropzone')
                report['extraction']=exercise(page,check,out)
                assert not report['page_errors'],report['page_errors']
                report['ok']=True
            except Exception:
                report['error']=traceback.format_exc();page.screenshot(path=str(out/'failure.png'));raise
            finally:
                (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
                browser.close();server.should_exit=True;thread.join(timeout=5);sock.close()
                app.state.runner.pool.shutdown(wait=True,cancel_futures=True)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()

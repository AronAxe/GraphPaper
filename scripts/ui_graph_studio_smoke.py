"""Real HTTP browser acceptance checks for the graph redesign."""
from pathlib import Path
import argparse,json,socket,sys,tempfile,threading,time,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from graphpaper.server import create_app
from playwright.sync_api import sync_playwright
from graph_studio_ui_checks import exercise
import uvicorn

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--chromium');parser.add_argument('--out',type=Path,default=ROOT/'test-results/graph-studio')
    args=parser.parse_args();out=args.out;out.mkdir(parents=True,exist_ok=True)
    report={'checks':[],'page_errors':[],'ok':False,'live_models':False}
    def check(s):report['checks'].append(s);print('PASS',s,flush=True)
    with tempfile.TemporaryDirectory(prefix='GraphPaper-graph-design-') as temp:
        app=create_app(Path(temp));sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        server=uvicorn.Server(uvicorn.Config(app,log_level='error'));thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
        for _ in range(200):
            if server.started:break
            time.sleep(.05)
        assert server.started
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,**({'executable_path':args.chromium} if args.chromium else {}))
            page=browser.new_page(viewport={'width':1580,'height':1120});page.set_default_timeout(8000)
            page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
            try:
                page.goto(f'http://127.0.0.1:{port}/');page.wait_for_selector('.welcome')
                page.get_by_role('button',name='The city after dark',exact=True).click();page.wait_for_selector('#graph-svg')
                report['graph']=exercise(page,check,out)
                for width in [1000,720,390]:
                    page.set_viewport_size({'width':width,'height':900});page.wait_for_timeout(200)
                    assert page.evaluate('() => document.documentElement.scrollWidth')<=width,(width,page.evaluate('() => document.documentElement.scrollWidth'))
                check('Responsive graph and controls stay within 1000, 720 and 390 pixel viewports')
                assert not report['page_errors'],report['page_errors'];report['ok']=True
            except Exception:
                report['error']=traceback.format_exc();page.screenshot(path=str(out/'failure.png'),full_page=True);raise
            finally:
                (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');browser.close();server.should_exit=True;thread.join(timeout=5);sock.close();app.state.runner.pool.shutdown(wait=True,cancel_futures=True)
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()

"""Graph Atlas integration against the real local HTTP server."""
from pathlib import Path
import json,socket,sys,tempfile,threading,time,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from graphpaper.server import create_app
from playwright.sync_api import sync_playwright
from atlas_ui_checks import exercise
import uvicorn


def main():
    out=ROOT/'test-results/atlas-ui';out.mkdir(parents=True,exist_ok=True)
    report={'checks':[],'page_errors':[],'live_models':False,'ok':False}
    def check(label):report['checks'].append(label);print('PASS',label,flush=True)
    with tempfile.TemporaryDirectory(prefix='graphpaper-atlas-') as temp:
        app=create_app(Path(temp));sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        server=uvicorn.Server(uvicorn.Config(app,log_level='error'))
        thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
        for _ in range(300):
            if server.started:break
            time.sleep(.05)
        assert server.started
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1586,'height':1000},accept_downloads=True)
            page.set_default_timeout(20000);page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
            try:
                page.goto(f'http://127.0.0.1:{port}/');page.wait_for_selector('.welcome')
                report['atlas']=exercise(page,check,out)
                page.get_by_role('button',name='Switch theme',exact=True).click()
                page.wait_for_function('()=>document.documentElement.dataset.theme==="light"')
                page.screenshot(path=str(out/'atlas-light.png'),full_page=True)
                page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(150)
                assert page.evaluate('() => document.documentElement.scrollWidth')<=390
                page.screenshot(path=str(out/'atlas-mobile.png'),full_page=True)
                check('Light theme and narrow-window layout render without horizontal page overflow')
                assert not report['page_errors'],report['page_errors']
                report['ok']=True
            except Exception:
                report['error']=traceback.format_exc();page.screenshot(path=str(out/'failure.png'));raise
            finally:
                (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
                browser.close();server.should_exit=True;thread.join(timeout=5);sock.close()
                app.state.runner.pool.shutdown(wait=True,cancel_futures=True)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()

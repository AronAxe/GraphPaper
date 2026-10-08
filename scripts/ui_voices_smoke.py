"""Real HTTP graphical voice-library workflow. No model calls."""
from pathlib import Path
import argparse,json,socket,sys,tempfile,threading,time,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from graphpaper.server import create_app
from playwright.sync_api import sync_playwright,expect
from voice_ui_checks import exercise
import uvicorn


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'test-results/voices-ui')
    out=parser.parse_args().out;out.mkdir(parents=True,exist_ok=True)
    report={'checks':[],'page_errors':[],'live_models':False,'ok':False}
    def check(label):report['checks'].append(label);print('PASS',label,flush=True)
    with tempfile.TemporaryDirectory(prefix='graphpaper-voices-') as temp:
        app=create_app(Path(temp));sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        server=uvicorn.Server(uvicorn.Config(app,log_level='error'))
        thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
        for _ in range(300):
            if server.started:break
            time.sleep(.05)
        assert server.started
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True)
            page.set_default_timeout(20000);page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
            try:
                page.goto(f'http://127.0.0.1:{port}/');page.wait_for_selector('.welcome')
                page.get_by_role('button',name='New project',exact=True).click();page.locator('#project-title').fill('First isolated article')
                page.locator('#project-mode').select_option('science')
                page.get_by_role('button',name='Create project',exact=True).click();page.wait_for_selector('.science-stats')
                assert page.evaluate('() => state.tab')=='research'
                before=page.evaluate('() => ({id:state.p.id,sources:state.p.sources,graph:state.p.graph,draft:state.p.draft})')
                page.locator('[data-action="writing-mode"]').click()
                page.locator('#writing-mode').select_option('polemic')
                page.get_by_role('button',name='Apply writing mode',exact=True).click()
                expect(page.locator('.modal')).to_have_count(0)
                page.wait_for_selector('#dropzone')
                expect(page.get_by_role('button',name='Creative brief',exact=True)).to_be_visible()
                assert page.evaluate('() => state.tab')=='sources'
                assert page.evaluate('() => ({id:state.p.id,sources:state.p.sources,graph:state.p.graph,draft:state.p.draft})')==before
                check('Leaving the Science-only research tab restores a usable writing workspace without changing material')
                report['library']=exercise(page,check,out)
                page.set_viewport_size({'width':1000,'height':800});page.wait_for_timeout(100)
                assert page.evaluate('() => document.documentElement.scrollWidth')<=1000
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

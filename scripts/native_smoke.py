"""Interactive Windows/WebView2 regression; never uses the user's project directory.

Uses the actual native window, Windows messages and its WebView2 via CDP. No
browser substitute, model calls, login, app-policy changes or user-data access.
The debug port exists only in the child test process. Requires an interactive
Windows desktop. Pass --executable for the actual packaged release binary.
"""
from __future__ import annotations
import argparse,ctypes,json,os,socket,sqlite3,subprocess,sys,tempfile,time,traceback
from ctypes import wintypes
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable',type=Path)
    parser.add_argument('--science',action='store_true',help='Exercise the Science workspace in the actual native shell')
    parser.add_argument('--out',type=Path,default=ROOT/'test-results/native')
    args=parser.parse_args()
    if sys.platform!='win32':raise SystemExit('This regression requires a native Windows desktop.')
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    u=ctypes.WinDLL('user32',use_last_error=True)
    cbtype=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    u.EnumWindows.argtypes=[cbtype,wintypes.LPARAM]
    u.EnumChildWindows.argtypes=[wintypes.HWND,cbtype,wintypes.LPARAM]
    u.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    u.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
    u.GetClassNameW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
    u.IsWindowVisible.argtypes=[wintypes.HWND];u.IsHungAppWindow.argtypes=[wintypes.HWND]
    u.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
    u.SendMessageTimeoutW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM,wintypes.UINT,wintypes.UINT,ctypes.POINTER(ctypes.c_size_t)]
    u.SendMessageTimeoutW.restype=ctypes.c_size_t
    report={'native_windows':True,'packaged_executable':bool(args.executable),'science_mode':bool(args.science),'live_models':False,'checks':[],'page_errors':[],'ok':False}
    def check(name):report['checks'].append(name);print('PASS',name,flush=True)
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    data=Path(tempfile.mkdtemp(prefix='GraphPaper-native-test-'))
    env=dict(os.environ,GRAPHPAPER_DATA_DIR=str(data),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=f'--remote-debugging-port={port}')
    if args.executable:command=[str(args.executable.resolve())]
    else:
        # Avoid Windows venv's redirector process so proc.pid owns the window.
        command=[str(Path(sys.base_prefix)/'python.exe'),'-m','graphpaper.desktop']
        env['PYTHONPATH']=os.pathsep.join([str(ROOT),*sys.path])
    log=(out/'native.log').open('w',encoding='utf-8')
    proc=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    def windows(parent=None):
        rows=[]
        def cb(hwnd,_):
            pid=wintypes.DWORD();u.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
            if parent is not None or pid.value==proc.pid:
                title=ctypes.create_unicode_buffer(512);cls=ctypes.create_unicode_buffer(256)
                u.GetWindowTextW(hwnd,title,512);u.GetClassNameW(hwnd,cls,256)
                rows.append({'hwnd':int(hwnd),'title':title.value,'class':cls.value,'visible':bool(u.IsWindowVisible(hwnd)),'hung':bool(u.IsHungAppWindow(hwnd))})
            return True
        if parent is None:u.EnumWindows(cbtype(cb),0)
        else:u.EnumChildWindows(parent,cbtype(cb),0)
        return rows
    def message(hwnd,msg,wparam=0,lparam=0):
        result=ctypes.c_size_t()
        ok=u.SendMessageTimeoutW(hwnd,msg,wparam,lparam,2,2000,ctypes.byref(result))
        if not ok:raise AssertionError(f'Native window stopped processing Windows message {msg:#x}')
    def responsive(hwnd):
        message(hwnd,0)
        assert not u.IsHungAppWindow(hwnd),'Windows marks the native window as hung'
    def wait_test(predicate,seconds=10):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            value=predicate()
            if value:return value
            time.sleep(.1)
        raise AssertionError('Native test condition did not become true')
    try:
        def cdp_ready():
            if proc.poll() is not None:raise AssertionError(f'Native application exited during startup: {proc.returncode}')
            try:
                with urlopen(f'http://127.0.0.1:{port}/json',timeout=1) as r:targets=json.load(r)
                return any(t.get('url','').startswith('http://127.0.0.1:') for t in targets)
            except OSError:return False
        wait_test(cdp_ready,25)
        native=wait_test(lambda:next((w for w in windows() if w['visible'] and w['title'].startswith('GraphPaper')),None))
        hwnd=native['hwnd'];responsive(hwnd);check('Actual Windows/WebView2 window starts and responds to Windows messages')
        with sync_playwright() as pw:
            b=pw.chromium.connect_over_cdp(f'http://127.0.0.1:{port}',timeout=8000)
            page=b.contexts[0].pages[0];page.set_default_timeout(8000)
            page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
            page.wait_for_selector('.welcome')
            expected={'cancel_close','notify_ready','request_close','save_export'}
            wait_test(lambda:set(page.evaluate('() => Object.keys(window.pywebview?.api||{})'))==expected)
            report['bridge_methods']=sorted(expected)
            result=page.evaluate("() => Promise.race([window.pywebview.api.notify_ready(),new Promise(r=>setTimeout(()=>r('timeout'),3000))])")
            assert result is True,result;check('Native bridge initializes with only four explicit methods and resolves its promise')
            response=page.request.get(page.url)
            assert "'unsafe-eval'" not in response.headers['content-security-policy'];check('Strict application CSP remains enabled')
            # Dispatch genuine Win32 mouse messages to the WebView input surface.
            children=windows(hwnd);report['native_child_classes']=sorted(set(w['class'] for w in children))
            target=next((w for w in children if w['class']=='Chrome_RenderWidgetHostHWND'),None)
            assert target,'WebView2 native input surface was not found'
            box=page.get_by_role('button',name='New project',exact=True).bounding_box()
            ratio=page.evaluate('() => window.devicePixelRatio')
            x=int((box['x']+box['width']/2)*ratio);y=int((box['y']+box['height']/2)*ratio)
            pos=(y<<16)|(x&0xffff)
            message(target['hwnd'],0x200,0,pos);message(target['hwnd'],0x201,1,pos);message(target['hwnd'],0x202,0,pos)
            page.wait_for_selector('#project-title');responsive(hwnd)
            check('A Windows mouse click opens the project dialog without freezing the host')
            page.locator('#project-title').fill('Native regression project')
            if args.science:
                page.locator('#project-mode').select_option('science')
                page.locator('#project-premise').fill('A scientific test question')
            page.get_by_role('button',name='Create project',exact=True).click();page.wait_for_selector('.science-stats' if args.science else '#dropzone')
            pid=page.evaluate('() => state.p.id');check('Native window supports typing and project creation')
            if args.science:
                page.get_by_role('button',name='Research protocol',exact=True).click()
                page.locator('#rp-queries').fill('memory AND sleep')
                page.get_by_role('button',name='Save research plan',exact=True).click()
                expect(page.locator('.modal')).to_have_count(0)
                assert page.evaluate('() => state.p.research.plan.queries[0]')=='memory AND sleep'
                check('Native Science research protocol edits and saves without a model call')
            page.locator('[data-action="settings"]').click();page.wait_for_selector('#s-provider')
            expect(page.locator('#s-reasoning_effort')).to_have_count(1)
            page.get_by_role('button',name='Close dialog',exact=True).click();responsive(hwnd)
            check('Connections dialog opens and closes in the native window')
            page.locator('.nav-link[data-tab="write"]').click();page.wait_for_selector('#manuscript')
            page.locator('#manuscript').fill('# Native test\n\nA saved line.')
            page.evaluate('() => flush()')
            # Invoke a real native Save As dialog through the actual JS bridge;
            # cancel it using the OS close button message, not a mocked return.
            page.evaluate("id => {window.__saveTest=null;window.pywebview.api.save_export(id,'md').then(r=>window.__saveTest=r).catch(e=>window.__saveTest={error:String(e)});}",pid)
            dlg=wait_test(lambda:next((w for w in windows() if w['visible'] and w['class']=='#32770'),None))
            u.PostMessageW(dlg['hwnd'],0x10,0,0)
            result=wait_test(lambda:page.evaluate('() => window.__saveTest'))
            assert result=={'saved':False},result;responsive(hwnd)
            check('Native Save As dialog opens, cancels and returns without blocking the interface')
            page.screenshot(path=str(out/'native-writing.png'))
            # Trigger close before the 650 ms autosave debounce can fire.
            draft='# Native test\n\nThis pending edit must survive the native close button.'
            page.locator('#manuscript').fill(draft)
            assert page.evaluate('() => Object.keys(pending).length')>0
            u.PostMessageW(hwnd,0x10,0,0)
            proc.wait(timeout=15)
            assert proc.returncode==0,proc.returncode
            check('Windows close completes the save handshake and exits normally')
            with sqlite3.connect(data/'studio.sqlite3') as c:stored=json.loads(c.execute('SELECT data FROM projects WHERE id=?',(pid,)).fetchone()[0])
            assert stored['draft']==draft,stored['draft'];check('Pending manuscript text is persisted before the native process exits')
            assert not report['page_errors'],report['page_errors']
            report['ok']=True
    except Exception:
        report['error']=traceback.format_exc();raise
    finally:
        if proc.poll() is None:
            subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True)
            proc.wait(timeout=10)
        log.close()
        report['exit_code']=proc.returncode
        report['recursion_errors']='maximum recursion depth' in (out/'native.log').read_text(encoding='utf-8',errors='replace')
        if report['recursion_errors']:report['ok']=False
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        # Test data alone; never clear the user's GraphPaper directory.
        import shutil
        shutil.rmtree(data,ignore_errors=True)
    print(json.dumps(report,indent=2))
    if not report["ok"]:raise SystemExit(1)

if __name__=='__main__':main()

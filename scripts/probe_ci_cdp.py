"""Disposable GitHub-runner diagnostics, never invoked by the application."""
from pathlib import Path
import json,os,socket,subprocess,sys,tempfile,time
from urllib.request import urlopen,build_opener,ProxyHandler
if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('RUNNER_ENVIRONMENT')!='github-hosted':
    raise SystemExit('This diagnostic is restricted to a disposable GitHub-hosted runner.')
import webview
root=Path(__file__).resolve().parents[1]
for name in ['platforms/edgechromium.py','platforms/webview2core.py','platforms/winforms.py']:
    p=Path(webview.__file__).parent/name
    if not p.exists():continue
    lines=p.read_text(encoding='utf-8').splitlines()
    for i,line in enumerate(lines):
        if 'REMOTE_DEBUG' in line or 'ADDITIONAL_BROWSER' in line or (name.endswith('winforms.py') and i in range(803,809)):
            print('INSTALLED',name,i+1,'\n'.join(lines[max(0,i-2):i+4]),flush=True)
for explicit in [False,True]:
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    data=Path(tempfile.mkdtemp(prefix='GraphPaper-CI-CDP-'))
    env=dict(os.environ,GRAPHPAPER_DATA_DIR=str(data),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=f'--remote-debugging-port={port}',PYWEBVIEW_LOG='debug',PYTHONUTF8='1')
    env['PYTHONPATH']=os.pathsep.join([str(root),*sys.path])
    code='import webview;'
    if explicit:code+=f'webview.settings["REMOTE_DEBUGGING_PORT"]={port};'
    code+='from graphpaper.desktop import main;main()'
    with (data/'process.log').open('w',encoding='utf-8') as log:
        proc=subprocess.Popen([sys.executable,'-c',code],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
        print('CASE',json.dumps({'explicit_webview_setting':explicit,'pid':proc.pid,'port':port}),flush=True)
        try:
            time.sleep(8)
            for path in ['/json','/json/list','/json/version']:
                for opener in [urlopen,build_opener(ProxyHandler({})).open]:
                    try:
                        with opener(f'http://127.0.0.1:{port}'+path,timeout=2) as response:
                            print('CDP',path,response.status,response.read().decode('utf-8')[:4000],flush=True)
                    except Exception as e:print('CDP',path,type(e).__name__,str(e),flush=True)
            command=f'''$all=Get-CimInstance Win32_Process; $ids=@({proc.pid}); for($i=0;$i -lt 4;$i++){{$ids+=@($all | Where-Object {{$_.ParentProcessId -in $ids}} | Select-Object -ExpandProperty ProcessId)}}; $all | Where-Object {{$_.ProcessId -in $ids}} | Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Depth 3'''
            result=subprocess.run(['powershell.exe','-NoProfile','-Command',command],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=15)
            print('OWNED_PROCESS_TREE',result.stdout,flush=True)
        finally:
            subprocess.run(['taskkill.exe','/PID',str(proc.pid),'/T','/F'],capture_output=True)
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
    print('APP_LOG', (data/'process.log').read_text(encoding='utf-8',errors='replace')[-8000:],flush=True)

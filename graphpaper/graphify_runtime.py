"""Pinned public Graphify discovery and isolated launch configuration."""
from __future__ import annotations
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from .graphify_process import OwnedProcess
from .graphify_worker import PINNED_VERSION

REQUIREMENT=f'graphifyy[openai]=={PINNED_VERSION}'


def worker_command():
    if getattr(sys,'frozen',False):
        return [sys.executable,'--graphify-worker']
    python=Path(sys.executable)
    if python.name.lower()=='pythonw.exe' and python.with_name('python.exe').is_file():
        python=python.with_name('python.exe')
    return [str(python),str(Path(__file__).with_name('graphify_worker.py'))]


def isolated_environment(home: Path) -> dict[str,str]:
    home.mkdir(parents=True,exist_ok=True)
    # Provider keys, OAuth tokens, proxy variables, user hooks, Python path
    # overrides and Graphify custom-provider config do not cross this boundary.
    names={'systemroot','windir','systemdrive','comspec','path','pathext','processor_architecture','number_of_processors','lang','lc_all','ld_library_path','dyld_library_path'}
    env={k:v for k,v in os.environ.items() if k.lower() in names}
    for name in ['HOME','USERPROFILE','APPDATA','LOCALAPPDATA','XDG_CONFIG_HOME','XDG_CACHE_HOME','TEMP','TMP','TMPDIR']:
        env[name]=str(home)
    # Upstream restarts as `python -m graphify` when no hash seed is supplied.
    # A frozen GraphPaper.exe is not a general Python CLI; supply the seed
    # before launching its worker so the unmodified upstream CLI stays there.
    env.update({'PYTHONHASHSEED':'0','PYTHONIOENCODING':'utf-8','PYTHONUTF8':'1','PYTHONNOUSERSITE':'1',
        'GRAPHIFY_NO_AUTO_REFRESH':'1','GRAPHIFY_QUERY_LOG_DISABLE':'1','GRAPHIFY_GOOGLE_WORKSPACE':'0',
        'GRAPHIFY_MAX_RETRIES':'0','GRAPHIFY_MAX_RETRY_DEPTH':'0','GRAPHIFY_MAX_WORKERS':'1',
        'GRAPHIFY_LLM_TEMPERATURE':'none','NO_PROXY':'127.0.0.1,localhost','no_proxy':'127.0.0.1,localhost'})
    package_root=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))
    cache=package_root/'vendor/tiktoken'
    if cache.is_dir(): env['TIKTOKEN_CACHE_DIR']=str(cache)
    return env


def check_runtime(configured='') -> dict:
    if configured:
        path=Path(configured).expanduser()
        if not path.is_file() or path.suffix.lower() in {'.bat','.cmd','.ps1','.sh'}:
            return {'available':False,'selection':'custom','error':'The configured Graphify path is not a native executable. Clear it to use the bundled runtime.', 'requirement':REQUIREMENT}
        command=[str(path.resolve())]
        with tempfile.TemporaryDirectory(prefix='graphpaper-graphify-probe-') as temp:
            env=isolated_environment(Path(temp)/'home')
            try:
                with OwnedProcess([*command,'--version'],cwd=temp,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE) as proc:
                    out,err=proc.communicate(timeout=15)
                version=re.search(r'\b(\d+\.\d+\.\d+)\b',out.decode('utf-8',errors='replace')[:2000])
                found=version[1] if version else ''
                available=proc.returncode==0 and found==PINNED_VERSION
                return {'available':available,'selection':'custom','command':command,'version':found,'requirement':REQUIREMENT,
                    'error':'' if available else f'This adapter is verified with Graphify {PINNED_VERSION}. Clear the custom path to use the bundled runtime, or install {REQUIREMENT} in a separate environment.'}
            except (OSError,RuntimeError,subprocess.TimeoutExpired):
                return {'available':False,'selection':'custom','requirement':REQUIREMENT,'error':'The configured Graphify executable did not pass its bounded version check. Clear its path to use the bundled runtime.'}
    command=worker_command()
    with tempfile.TemporaryDirectory(prefix='graphpaper-graphify-probe-') as temp:
        root=Path(temp);env=isolated_environment(root/'home');report=root/'probe.json'
        env['GRAPHPAPER_GRAPHIFY_PROBE_FILE']=str(report)
        try:
            with OwnedProcess([*command,'--graphpaper-probe'],cwd=temp,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL) as proc:
                proc.wait(timeout=20)
            result=json.loads(report.read_text(encoding='utf-8')) if report.is_file() and report.stat().st_size<50000 else {}
            return {**result,'available':bool(result.get('available') and proc.returncode==0),
                'selection':'bundled' if getattr(sys,'frozen',False) or '--graphify-worker' in command else 'python-environment',
                'command':command,'requirement':REQUIREMENT,
                'error':result.get('error') or ('' if result.get('available') else 'Graphify runtime is missing. Use the complete Windows release or install requirements-graphify.txt in the source environment.')}
        except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired):
            return {'available':False,'selection':'bundled' if getattr(sys,'frozen',False) or '--graphify-worker' in command else 'python-environment','requirement':REQUIREMENT,
                'error':'Graphify could not start. Use the complete release or install requirements-graphify.txt; Native extraction remains separately available.'}

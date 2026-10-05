"""Live-runtime, signed-out protocol check. Does not authenticate or make a model call."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from graphpaper.codex import Codex

runtime=ROOT/'vendor/codex.exe'
version=subprocess.check_output([str(runtime),'--version'],text=True,timeout=20).strip()
help_text=subprocess.check_output([str(runtime),'exec','--help'],text=True,timeout=20)
for flag in ['--ephemeral','--json','--sandbox','--output-last-message']:
    assert flag in help_text, 'Required runtime option missing: '+flag
with tempfile.TemporaryDirectory() as tmp:
    c=Codex(Path(tmp),str(runtime))
    try:
        status=c.status()
        assert status['installed'] and not status['signed_in'],status
    finally:c.close()
report={'ok':True,'version':version,'unauthenticated_app_server_handshake':True,'live_model_call':False,'browser_oauth_completed':False}
path=ROOT/'test-results/codex-runtime.json';path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))

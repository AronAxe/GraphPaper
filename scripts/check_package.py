"""Windows CI check of a frozen binary's local backend + bundled assets."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile

folder=Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory() as tmp:
    result=Path(tmp)/"self-test.json"
    proc=subprocess.run([str(folder/"GraphPaper.exe"),"--self-test",str(result)],timeout=60)
    assert proc.returncode==0 and result.exists(), "Packaged binary did not finish its self-test"
    report=json.loads(result.read_text())
    assert report["ok"],report
    print(json.dumps(report,indent=2))

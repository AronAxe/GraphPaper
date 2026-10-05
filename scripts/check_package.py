"""Windows CI check of a frozen binary's local backend and bundled assets."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile

folder = Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory() as tmp:
    result = Path(tmp)/"self-test.json"
    proc = subprocess.run([str(folder/"GraphPaper.exe"), "--self-test", str(result)], timeout=60)
    if not result.exists():
        raise RuntimeError(f"Packaged binary exited {proc.returncode} without a diagnostic report")
    report = json.loads(result.read_text(encoding='utf-8'))
    print(json.dumps(report, indent=2))
    output = Path('test-results/package.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    assert proc.returncode == 0 and report['ok'], report

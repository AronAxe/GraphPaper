"""Test a fresh extraction of the actual ZIP with simulated Windows Internet-zone marks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path)
    parser.add_argument('--out',type=Path,default=Path('test-results/downloaded-package'))
    args=parser.parse_args()
    if sys.platform!='win32' or os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('RUNNER_ENVIRONMENT')!='github-hosted':
        raise SystemExit('Requires an isolated GitHub-hosted Windows runner.')
    archive=args.archive.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    with archive.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    with tempfile.TemporaryDirectory(prefix='GraphPaper-downloaded-') as temporary:
        target=Path(temporary)
        with zipfile.ZipFile(archive) as bundle:
            for entry in bundle.infolist():
                if not (target/entry.filename).resolve().is_relative_to(target):raise ValueError('Unsafe ZIP entry')
            bundle.extractall(target)
        executable=target/'GraphPaper/GraphPaper.exe'
        assert executable.is_file()
        subprocess.run([sys.executable,str(Path(__file__).with_name('native_smoke.py')),
            '--executable',str(executable),'--downloaded-runtime','--science','--graphify',
            '--polemic','--voices','--graph-studio','--system-one','--out',str(out)],check=True)
        report=json.loads((out/'report.json').read_text(encoding='utf-8'))
        assert report['ok'] and report['downloaded_runtime']['native_consent']
        report['archive_sha256']=digest
        report['scope']='Actual frozen Windows app from the release ZIP. Internet-zone tags simulated on bundled DLLs; tests do not simulate SmartScreen, all antivirus products, or every Windows policy.'
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Downloaded-runtime and complete native workflows passed for archive',digest)


if __name__=='__main__':main()

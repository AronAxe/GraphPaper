"""Embed per-build DLL checksums; verify actual frozen destinations before release."""
from __future__ import annotations
import argparse
import importlib.metadata as metadata
from pathlib import Path
import pprint
import runpy
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from graphpaper.windows_runtime import PREFIXES, PRIMARY, file_hash, verify_bundle


def generate():
    files={}
    for name in ('pythonnet','pywebview','clr_loader'):
        dist=metadata.distribution(name)
        for item in dist.files or []:
            relative=item.as_posix()
            if relative.startswith(PREFIXES) and relative.lower().endswith('.dll'):
                files[relative]=file_hash(Path(dist.locate_file(item)))
    if PRIMARY not in files:raise RuntimeError('Python.NET runtime missing from build environment')
    output=ROOT/'graphpaper/_runtime_hashes.py'
    output.write_text('"""Generated DLL checksums embedded in this build; not publisher authentication."""\nFILES = '+pprint.pformat(dict(sorted(files.items())),sort_dicts=True)+'\n',encoding='utf-8')
    print('Embedded',len(files),'window-runtime DLL hashes')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',type=Path)
    args=parser.parse_args()
    if args.verify:
        hashes=runpy.run_path(str(ROOT/'graphpaper/_runtime_hashes.py'))['FILES']
        paths=verify_bundle(args.verify,hashes)
        print('Verified frozen paths and bytes for',len(paths),'runtime DLLs')
    else:generate()

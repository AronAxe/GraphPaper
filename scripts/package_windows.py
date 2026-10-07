"""Stream a portable Windows build into a verified ZIP without buffering binaries in RAM."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import zipfile


def sha256(path: Path) -> str:
    result=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            result.update(chunk)
    return result.hexdigest()


def package(folder: Path, destination: Path) -> tuple[int,str]:
    folder=folder.resolve();destination=destination.resolve()
    if not folder.is_dir() or not (folder/'GraphPaper.exe').is_file():
        raise ValueError('Expected the complete GraphPaper executable folder.')
    if destination==folder or folder in destination.parents:
        raise ValueError('The ZIP must be outside the application folder.')
    files=sorted(p for p in folder.rglob('*') if p.is_file())
    if any(p.is_symlink() for p in folder.rglob('*')):
        raise ValueError('A release folder must not contain symbolic links.')
    if not any(p.name=='app.js' for p in files):
        raise ValueError('The bundled interface is missing.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    temp=destination.with_suffix(destination.suffix+'.tmp')
    try:
        with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as archive:
            for i,path in enumerate(files,1):
                archive.write(path,arcname=(Path(folder.name)/path.relative_to(folder)).as_posix())
                if i%250==0:print(f'Packaged {i}/{len(files)} files',flush=True)
        with zipfile.ZipFile(temp) as archive:
            corrupt=archive.testzip()
            if corrupt:raise ValueError('Archive CRC verification failed: '+corrupt)
        digest=sha256(temp)
        temp.replace(destination)
        return destination.stat().st_size,digest
    finally:
        if temp.exists():temp.unlink()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    size,digest=package(args.folder,args.destination)
    sums=args.destination.parent/'SHA256SUMS.txt'
    sums.write_text(digest+'  '+args.destination.name+'\n',encoding='ascii',newline='\n')
    print(f'Verified {args.destination.name}: {size} bytes; SHA-256 {digest}',flush=True)

if __name__=='__main__':main()

"""Rebuild illustrative assets and a code-only publishing manifest in a clean CI checkout."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def basics():
    from PIL import Image, ImageDraw
    from graphpaper.demo import make_demo
    image = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, 255, 255), 68, fill='#cde5c1')
    for points in [((76,84),(180,96),(128,192),(76,84)), ((76,84),(128,124),(180,96)), ((128,124),(128,192))]:
        draw.line(points, fill='#244035', width=9, joint='curve')
    for x,y,r in [(76,84,20),(180,96,20),(128,192,20),(128,124,12)]:
        draw.ellipse((x-r,y-r,x+r,y+r), fill='#244035')
    image.save(ROOT/'ui/graphpaper.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    (ROOT/'examples').mkdir(exist_ok=True)
    for mode in ['nonfiction','fiction']:
        (ROOT/'examples'/f'{mode}.json').write_text(make_demo(mode).model_dump_json(indent=2), encoding='utf-8')


def reports():
    from PIL import Image
    dest = ROOT/'docs/images'
    dest.mkdir(parents=True, exist_ok=True)
    for name in ['welcome','graph','angles','writing','light']:
        with Image.open(ROOT/'test-results/ui'/f'{name}.png') as image:
            image.convert('RGB').save(dest/f'{name}.webp', quality=86)
    dest = ROOT/'docs/validation'
    dest.mkdir(parents=True, exist_ok=True)
    for source, target in [('test-results/ui/report.json','browser.json'),('test-results/results.xml','pytest.xml'),('test-results/loopback.json','loopback.json')]:
        shutil.copyfile(ROOT/source, dest/target)


def manifest():
    allowed_roots = {'.github','docs','examples','graphpaper','scripts','tests','ui'}
    allowed_top = {'README.md','CHANGELOG.md','LICENSE','.gitignore','.gitattributes','pyproject.toml','requirements.txt','requirements-dev.txt','requirements-desktop.txt','GraphPaper.pyw','Open GraphPaper.vbs','Publish GraphPaper.pyw','Publish GraphPaper.vbs'}
    paths = set(subprocess.check_output(['git','ls-files','-z'], cwd=ROOT).decode().split('\0'))
    for folder in ['docs/images','docs/validation','examples','ui']:
        paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT/folder).rglob('*') if p.is_file())
    files = {}
    for name in sorted(paths):
        p = ROOT/name
        parts = Path(name).parts
        if not parts or not p.is_file() or p.is_symlink():
            continue
        if name not in allowed_top and parts[0] not in allowed_roots:
            continue
        if any(x in {'__pycache__','.venv','.git','test-results'} for x in parts) or p.suffix in {'.pyc','.db','.dpapi','.log'}:
            continue
        files[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    (ROOT/'publish-manifest.json').write_text(json.dumps({'repository':'AronAxe/GraphPaper','files':files}, indent=2)+'\n', encoding='utf-8')
    print('Manifest:', len(files), 'source and illustrative asset files')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--reports', action='store_true')
    parser.add_argument('--manifest', action='store_true')
    args = parser.parse_args()
    if args.manifest:
        manifest()
    elif args.reports:
        reports()
    else:
        basics()

"""Exact integration against the reviewed v0.5 source; run once on the feature branch."""
from pathlib import Path
import io,time,urllib.request
from PIL import Image


def replace(path,old,new):
    p=Path(path);s=p.read_text(encoding='utf-8')
    if new in s:return
    if s.count(old)!=1:raise RuntimeError(f'Unexpected anchor in {path}: {s.count(old)}')
    p.write_text(s.replace(old,new),encoding='utf-8')

replace('ui/index.html','</head>','<link rel="stylesheet" href="/static/atlas.css">\n<script src="/static/graph-scene.js" defer></script>\n<script src="/static/graph-atlas.js" defer></script>\n</head>')
replace('graphpaper/server.py','    app.mount("/static", StaticFiles(directory=asset_directory()), name="static")','    from .graph_editor import register as register_graph_editor\n    register_graph_editor(app, store, runner)\n    app.mount("/static", StaticFiles(directory=asset_directory()), name="static")')
replace('graphpaper/__init__.py','0.5.0','0.6.0')
replace('pyproject.toml','version = "0.5.0"','version = "0.6.0"')
replace('pyproject.toml','"ui/graphpaper.ico"]','"ui/graphpaper.ico", "ui/atlas.css", "ui/graph-atlas.js", "ui/graph-scene.js", "ui/atlas-mark.svg", "ui/graph-paper.jpg", "ui/ASSET-CREDITS.txt"]')
replace('ui/app.js','GraphPaper · 0.5.0','GraphPaper · 0.6.0')
replace('scripts/native_smoke.py',"    parser.add_argument('--out',type=Path,default=ROOT/'test-results/native')","    parser.add_argument('--atlas',action='store_true',help='Exercise spatial graph editing with isolated projects')\n    parser.add_argument('--out',type=Path,default=ROOT/'test-results/native')")
replace('scripts/native_smoke.py',"            page.locator('[data-action=\"settings\"]').click();page.wait_for_selector('#s-provider')","            if args.atlas:\n                from atlas_ui_checks import exercise as atlas_exercise\n                report['graph_atlas']=atlas_exercise(page,check,out)\n                responsive(hwnd)\n            page.locator('[data-action=\"settings\"]').click();page.wait_for_selector('#s-provider')")
p=Path('README.md');s=p.read_text(encoding='utf-8');s=s.replace('v0.5.0','v0.6.0');s+='\n\n## Graph Atlas\n\nThe new [editable spatial graph](docs/GRAPH-ATLAS.md) adds orbit, focus, clusters and colored relationships. The light sidebar uses [real scanned graph paper](docs/ASSET-CREDITS.md), not a generated mockup.\n';p.write_text(s,encoding='utf-8')
p=Path('docs/README.md');s=p.read_text(encoding='utf-8');s+='\n\n[Graph Atlas: spatial navigation and click-to-edit](GRAPH-ATLAS.md) · [Interface asset credits](ASSET-CREDITS.md)\n';p.write_text(s,encoding='utf-8')
p=Path('CHANGELOG.md');s=p.read_text(encoding='utf-8');p.write_text('# 0.6.0 — Graph Atlas\n\nReal squared-paper sidebar, ink palette, orbitable graph with typed lines, dense-graph clusters, neighborhood focus, persistent node/edge editing and atomic one-step undo. Existing writing, sources and voices are preserved.\n\n'+s,encoding='utf-8')
url='https://upload.wikimedia.org/wikipedia/commons/4/4d/Graph_paper_notepad_%284562203394%29.jpg'
photo=Path('ui/graph-paper.jpg')
if not photo.exists():
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'GraphPaper/0.6 (https://github.com/AronAxe/GraphPaper; CC-BY attribution asset) '})
            with urllib.request.urlopen(req,timeout=60) as r:raw=r.read(12_000_000)
            image=Image.open(io.BytesIO(raw)).convert('RGB');image.thumbnail((1400,2000),Image.Resampling.LANCZOS);image.save(photo,quality=92,optimize=True)
            assert photo.stat().st_size>10000
            print('Bundled real Calsidyrose graph-paper scan',image.size,photo.stat().st_size)
            break
        except Exception:
            if attempt==2:raise
            time.sleep(3*(attempt+1))
print('Integrated Graph Atlas without changing provider or authorial instructions.')

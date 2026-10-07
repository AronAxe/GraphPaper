"""Validate maintained docs, render a wiki, or explicitly publish its managed pages.

Only documentation is written. Existing independently edited wiki pages are never
silently overwritten. Publication uses normal authorized Git credentials, never
force-pushes, and leaves unrelated wiki pages intact.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
from urllib.parse import quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MD_LINK = re.compile(r'(!?\[[^\]\n]*\]\()([^\s)]+)([^)]*\))')
HTML_LINK = re.compile(r'\b(href|src)=("|\')([^"\']+)(\2)', re.I)
MANIFEST = '.graphpaper-wiki.json'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def configuration(root: Path):
    conf = json.loads((root / 'docs/wiki-pages.json').read_text(encoding='utf-8'))
    if conf.get('repository') != 'AronAxe/GraphPaper':
        raise ValueError('Unexpected documentation target repository.')
    titles, sources = set(), set()
    for page in conf['pages']:
        title, source = page['title'], page['source']
        pure = PurePosixPath(source)
        if not re.fullmatch(r'[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*', title):
            raise ValueError('Unsafe wiki page title: ' + title)
        if title.casefold() in titles or source in sources:
            raise ValueError('Duplicate wiki mapping: ' + title)
        if pure.is_absolute() or '..' in pure.parts or pure.parts[0] != 'docs' or pure.suffix != '.md' or '\\' in source:
            raise ValueError('Unsafe documentation source path.')
        path = (root / source).resolve()
        if root.resolve() not in path.parents or not path.is_file():
            raise ValueError('Missing documentation source: ' + source)
        titles.add(title.casefold()); sources.add(source)
    if 'home' not in titles:
        raise ValueError('The wiki needs a Home page.')
    return conf


def unfenced(text: str) -> str:
    """Remove fenced code without confusing literal example paths with links."""
    rows = []; fence = None
    for line in text.splitlines():
        match = re.match(r'^\s*(`{3,}|~{3,})', line)
        if match:
            marker = match[1]
            if fence is None:
                fence = marker[0]
            elif fence == marker[0]:
                fence = None
            rows.append(''); continue
        rows.append('' if fence else line)
    return '\n'.join(rows)


def anchors(text: str):
    used = {}; result = set()
    for line in unfenced(text).splitlines():
        match = re.match(r'^#{1,6}\s+(.+?)\s*#*$', line)
        if not match:
            continue
        value = re.sub(r'<[^>]*>', '', match[1]).replace('`', '')
        value = re.sub(r'[^\w\- ]', '', html.unescape(value).lower()).replace(' ', '-')
        count = used.get(value, 0); used[value] = count + 1
        result.add(value + ('-' + str(count) if count else ''))
    return result


def destinations(text: str):
    body = unfenced(text)
    yield from (m[2] for m in MD_LINK.finditer(body))
    yield from (m[3] for m in HTML_LINK.finditer(body))


def check(root: Path):
    conf = configuration(root)
    files = [root/'README.md', root/'CONTRIBUTING.md', root/'SECURITY.md']
    files += [root/p['source'] for p in conf['pages']]
    issues, count = [], 0
    for path in files:
        text = path.read_text(encoding='utf-8')
        for dest in destinations(text):
            count += 1
            parsed = urlsplit(html.unescape(dest))
            if parsed.scheme or parsed.netloc:
                continue
            local = unquote(parsed.path)
            target = (path.parent/local).resolve() if local else path.resolve()
            if target != root.resolve() and root.resolve() not in target.parents:
                issues.append(f'{path.relative_to(root)}: path escapes repository: {dest}'); continue
            if not target.exists():
                issues.append(f'{path.relative_to(root)}: missing target: {dest}'); continue
            if parsed.fragment and target.suffix.lower() == '.md':
                if unquote(parsed.fragment) not in anchors(target.read_text(encoding='utf-8')):
                    issues.append(f'{path.relative_to(root)}: missing heading: {dest}')
        if '\ufffd' in text:
            issues.append(f'{path.relative_to(root)}: replacement character in UTF-8 text')
    if issues:
        raise ValueError('\n'.join(issues))
    print(f'Validated {len(files)} maintained Markdown files, {count} link/image targets and {len(conf["pages"])} wiki pages.')
    return {'documents':len(files), 'links':count, 'wiki_pages':len(conf['pages'])}


def wiki_destination(root: Path, source: Path, destination: str, conf: dict, *, image=False):
    raw = html.unescape(destination); parsed = urlsplit(raw)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return destination
    resolved = (source.parent / unquote(parsed.path)).resolve()
    if root.resolve() not in resolved.parents:
        raise ValueError('Link leaves the repository: ' + raw)
    relative = resolved.relative_to(root.resolve()).as_posix()
    mapping = {p['source']:p['title'] for p in conf['pages']}
    repo = conf['repository']
    suffix = ('?'+parsed.query if parsed.query else '')+('#'+parsed.fragment if parsed.fragment else '')
    if not image and relative in mapping:
        return f'https://github.com/{repo}/wiki/{mapping[relative]}' + suffix
    if image:
        return f'https://raw.githubusercontent.com/{repo}/main/{quote(relative, safe="/")}' + suffix
    kind = 'tree' if resolved.is_dir() else 'blob'
    return f'https://github.com/{repo}/{kind}/main/{quote(relative, safe="/")}' + suffix


def render(root: Path):
    conf = configuration(root); pages = {}
    for entry in conf['pages']:
        source = root/entry['source']; original = source.read_text(encoding='utf-8')
        def md(match):
            return match[1]+wiki_destination(root,source,match[2],conf,image=match[1].startswith('!'))+match[3]
        def tag(match):
            url = wiki_destination(root,source,match[3],conf,image=match[1].lower()=='src')
            return match[1]+'='+match[2]+url+match[4]
        converted = MD_LINK.sub(md, original)
        converted = HTML_LINK.sub(tag, converted)
        intro = f'> GraphPaper {conf["docs_version"]} · [Documentation source](https://github.com/{conf["repository"]}/blob/main/{entry["source"]}) · [Suggest an edit](https://github.com/{conf["repository"]}/edit/main/{entry["source"]})\n\n'
        pages[entry['title']+'.md'] = intro+converted
    side = ['## GraphPaper', '', '[Download for Windows](https://github.com/'+conf['repository']+'/releases/latest)', '']
    section = None
    for page in conf['pages']:
        if page['section'] != section:
            section = page['section']; side += ['### '+section, '']
        label = page['title'].replace('-', ' ')
        side.append(f'- [{label}](https://github.com/{conf["repository"]}/wiki/{page["title"]})')
    pages['_Sidebar.md'] = '\n'.join(side)+'\n'
    pages['_Footer.md'] = f'**GraphPaper** · [Repository](https://github.com/{conf["repository"]}) · [Releases](https://github.com/{conf["repository"]}/releases) · [Issues](https://github.com/{conf["repository"]}/issues) · [MIT license](https://github.com/{conf["repository"]}/blob/main/LICENSE)\n\nMaintained in the repository’s `docs/` directory and published from the same source. These guides describe version {conf["docs_version"]}.\n'
    return conf, pages


def write_pages(output: Path, pages: dict[str,str]):
    output.mkdir(parents=True, exist_ok=True)
    for name, content in pages.items():
        (output/name).write_text(content,encoding='utf-8',newline='\n')


def reconciliation(folder: Path, conf: dict, pages: dict[str,str], adopt_home=False):
    manifest = folder/MANIFEST
    if manifest.is_symlink():
        raise ValueError('Unsafe wiki manifest symlink.')
    previous = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {'repository':conf['repository'],'files':{}}
    if previous.get('repository') != conf['repository']:
        raise ValueError('Wiki manifest belongs to another repository.')
    old = previous['files']; conflicts=[]; removed=[]
    for name, content in pages.items():
        path = folder/name
        if path.is_symlink():raise ValueError('Managed wiki page is a symlink: '+name)
        if not path.exists(): continue
        actual = sha(path.read_bytes())
        if actual == sha(content.encode()): continue
        if name in old and actual == old[name]: continue
        if name=='Home.md' and not manifest.exists() and adopt_home: continue
        conflicts.append(name)
    for name, expected in old.items():
        if name in pages: continue
        if not re.fullmatch(r'(?:[A-Za-z0-9-]+|_Sidebar|_Footer)\.md',name):
            raise ValueError('Unsafe filename in existing wiki manifest.')
        path=folder/name
        if path.is_symlink():raise ValueError('Managed wiki page is a symlink: '+name)
        if path.exists():
            if sha(path.read_bytes())!=expected:conflicts.append(name)
            else:removed.append(name)
    if conflicts:
        raise ValueError('Wiki pages were independently edited; reconcile before publishing: '+', '.join(sorted(set(conflicts))))
    return removed


def publish(root: Path, adopt_home=False):
    check(root);conf,pages=render(root)
    env=os.environ.copy();env['GIT_TERMINAL_PROMPT']='0'
    prefix=['git','-c','core.autocrlf=false']
    if env.get('GH_TOKEN') or env.get('GITHUB_TOKEN'):
        # The helper handles credentials; no token is placed in a URL or printed.
        prefix += ['-c','credential.helper=', '-c','credential.helper=!gh auth git-credential']
    def run(*args, cwd=None, allowed=(0,)):
        proc=subprocess.run(prefix+list(args),cwd=cwd,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
        if proc.returncode not in allowed:
            raise RuntimeError('Wiki Git operation failed. Check access and that an initial wiki page exists.\n'+proc.stderr[-2000:])
        return proc
    with tempfile.TemporaryDirectory(prefix='graphpaper-wiki-publish-') as temp:
        folder=Path(temp)/'wiki'
        run('clone','--depth','1',f'https://github.com/{conf["repository"]}.wiki.git',str(folder))
        removed=reconciliation(folder,conf,pages,adopt_home)
        write_pages(folder,pages)
        for name in removed:(folder/name).unlink()
        state={'repository':conf['repository'],'docs_version':conf['docs_version'],'files':{name:sha(content.encode()) for name,content in sorted(pages.items())}}
        (folder/MANIFEST).write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8',newline='\n')
        run('add','--',*sorted(pages),*removed,MANIFEST,cwd=folder)
        if run('diff','--cached','--quiet',cwd=folder,allowed=(0,1)).returncode==0:
            print('Wiki already matches the maintained documentation.');return
        author='github-actions[bot]' if env.get('GITHUB_ACTIONS')=='true' else 'Aron Bijl'
        email='41898282+github-actions[bot]@users.noreply.github.com' if env.get('GITHUB_ACTIONS')=='true' else '33731256+AronAxe@users.noreply.github.com'
        run('-c','user.name='+author,'-c','user.email='+email,'commit','-m','Publish maintained GraphPaper documentation',cwd=folder)
        branch=run('branch','--show-current',cwd=folder).stdout.strip()
        run('push','origin','HEAD:'+branch,cwd=folder)
        ident=run('rev-parse','HEAD',cwd=folder).stdout.strip()
        print(json.dumps({'wiki':'https://github.com/'+conf['repository']+'/wiki','pages':len(conf['pages']),'navigation_files':2,'commit':ident},indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('check')
    renderer=sub.add_parser('render-wiki');renderer.add_argument('--output',type=Path,required=True)
    publisher=sub.add_parser('publish-wiki');publisher.add_argument('--adopt-home',action='store_true',help='First publication only: replace the explicitly initialized Home placeholder')
    args=parser.parse_args()
    if args.command=='check':check(ROOT)
    elif args.command=='render-wiki':
        check(ROOT);conf,pages=render(ROOT);write_pages(args.output,pages)
        print(f'Rendered {len(conf["pages"])} wiki pages and sidebar/footer to {args.output}.')
    else:publish(ROOT,args.adopt_home)


if __name__=='__main__':main()

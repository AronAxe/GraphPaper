"""Bounded link discovery for a user-specified author page. No hidden site crawl."""
from __future__ import annotations
import http.client
from urllib.parse import urljoin, urlsplit, urlunsplit
from bs4 import BeautifulSoup
from .ingest import resolve_public, PinnedHTTPS, MAX_BYTES


def extract_links(html, base):
    host = urlsplit(base).hostname
    soup = BeautifulSoup(html, 'html.parser')
    found = {base:{'url':base,'title':soup.title.get_text(' ',strip=True) if soup.title else 'This page'}}
    for a in soup.select('article a[href], main a[href], .post a[href], .entry-title a[href], a[href]'):
        href = urljoin(base,a.get('href',''))
        p = urlsplit(href)
        if p.scheme not in {'http','https'} or p.hostname != host or p.username or p.password:
            continue
        if p.query or any(s in p.path.lower() for s in ['/login','/signup','/privacy','/terms','/tag/','/category/','/feed','/wp-json','/search']):
            continue
        if p.path.lower().endswith(('.jpg','.png','.svg','.zip','.js','.css')):
            continue
        url = urlunsplit((p.scheme,p.netloc,p.path,'',''))
        title = a.get_text(' ',strip=True)
        if len(title) < 8 or url in found:
            continue
        found[url] = {'url':url,'title':title[:250]}
        if len(found) >= 30:
            break
    return list(found.values())


def discover(url):
    for _ in range(5):
        p, host, port, ip = resolve_public(url)
        conn = PinnedHTTPS(host,ip,port) if p.scheme == 'https' else http.client.HTTPConnection(ip,port,timeout=25)
        try:
            conn.request('GET',(p.path or '/')+('?' + p.query if p.query else ''), headers={'Host':host,'User-Agent':'GraphPaper/0.2 author-source-discovery','Accept-Encoding':'identity'})
            response = conn.getresponse()
            if response.status in {301,302,303,307,308}:
                destination = response.getheader('Location')
                if not destination:
                    raise ValueError('Redirect did not include a destination.')
                url = urljoin(url,destination)
                continue
            if response.status != 200:
                raise ValueError(f'This page returned HTTP {response.status}. Paste text or upload saved articles instead.')
            if response.getheader('Content-Encoding','identity') not in {'','identity'}:
                raise ValueError('The site returned unsupported compressed content.')
            data = response.read(MAX_BYTES+1)
            if len(data) > MAX_BYTES:
                raise ValueError('Author page exceeds 20 MB.')
            if 'html' not in response.getheader('Content-Type','text/html').lower():
                return {'pages':[{'url':url,'title':'Import this source'}], 'note':'Direct document link.'}
            return {'pages':extract_links(data.decode('utf-8',errors='replace'),url),
                    'note':'These are same-site candidate pages, not verified authorship. Select only your writing. Nothing is imported or sent to a model until you choose it.'}
        finally:
            conn.close()
    raise ValueError('Too many redirects.')

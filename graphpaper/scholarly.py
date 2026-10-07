"""Live scholarly search with bounded requests, source provenance, and explicit partial failures."""
from __future__ import annotations
import hashlib
import re
import threading
import time
from datetime import datetime, timezone
from urllib.parse import quote, urlsplit
import httpx
from bs4 import BeautifulSoup
from defusedxml import ElementTree as ET
from .science_models import ResearchAuthor, ScholarlyMeta, ResearchRecord

NAMES = {'pubmed':'PubMed', 'semantic_scholar':'Semantic Scholar', 'arxiv':'arXiv', 'crossref':'Crossref', 'europe_pmc':'Europe PMC'}
_LOCKS = {k: threading.Lock() for k in NAMES}
_LAST = {k: 0.0 for k in NAMES}
_INTERVAL = {'pubmed':.35, 'semantic_scholar':1.05, 'arxiv':3.05, 'crossref':.15, 'europe_pmc':.15}

def stamp():
    return datetime.now(timezone.utc).isoformat()

def text(node):
    return ''.join(node.itertext()).strip() if node is not None else ''

def doi(value):
    value = re.sub(r'^(?:https?://(?:dx\.)?doi.org/|doi:\s*)', '', str(value or '').strip(), flags=re.I)
    return value.lower().rstrip(' .') if re.match(r'^10\.\d{4,9}/\S+$', value) else ''

def parsed_author(name):
    name = str(name).strip()
    if ',' in name:
        family, given = name.split(',', 1)
        return ResearchAuthor(family=family.strip(), given=given.strip())
    words = name.split()
    if len(words) < 2 or re.search(r'consortium|group|collaboration|committee|team', name, re.I):
        return ResearchAuthor(literal=name)
    return ResearchAuthor(family=words[-1], given=' '.join(words[:-1]))

def year_of(value):
    m = re.search(r'\b(1[4-9]\d{2}|20\d{2}|21\d{2})\b', str(value or ''))
    return int(m[1]) if m else None

def safe_url(value):
    value = str(value or '')
    try:
        p = urlsplit(value)
        return value if p.scheme in {'https','http'} and p.hostname and not p.username and not p.password else ''
    except ValueError:
        return ''

def record(meta: ScholarlyMeta, abstract=''):
    identity = meta.doi or meta.pmid or meta.arxiv_id or (meta.title.casefold()+str(meta.year))
    return ResearchRecord(id='paper_'+hashlib.sha256(identity.encode()).hexdigest()[:16], metadata=meta, abstract=abstract[:100000])

def parse_pubmed(raw: bytes):
    root = ET.fromstring(raw)
    out = []
    for item in root.findall('.//PubmedArticle'):
        article = item.find('./MedlineCitation/Article')
        if article is None:
            continue
        pmid = text(item.find('./MedlineCitation/PMID'))
        ids = {n.attrib.get('IdType'):text(n) for n in item.findall('./PubmedData/ArticleIdList/ArticleId')}
        journal = article.find('Journal')
        date = text(article.find('ArticleDate/Year')) or text(article.find('Journal/JournalIssue/PubDate/Year')) or text(article.find('Journal/JournalIssue/PubDate/MedlineDate'))
        authors = []
        for a in article.findall('AuthorList/Author'):
            if a.find('CollectiveName') is not None:
                authors.append(ResearchAuthor(literal=text(a.find('CollectiveName'))))
            else:
                authors.append(ResearchAuthor(family=text(a.find('LastName')), given=text(a.find('ForeName')) or text(a.find('Initials'))))
        abstract = '\n'.join((n.attrib.get('Label','')+': ' if n.attrib.get('Label') else '')+text(n) for n in article.findall('Abstract/AbstractText'))
        types = '; '.join(text(n) for n in article.findall('PublicationTypeList/PublicationType'))
        meta = ScholarlyMeta(title=text(article.find('ArticleTitle')), authors=authors, year=year_of(date),
            journal=text(journal.find('Title')) if journal is not None else '', volume=text(article.find('Journal/JournalIssue/Volume')),
            issue=text(article.find('Journal/JournalIssue/Issue')), pages=text(article.find('Pagination/StartPage')) or text(article.find('Pagination/MedlinePgn')),
            doi=doi(ids.get('doi')), pmid=pmid, pmcid=ids.get('pmc',''), url='https://pubmed.ncbi.nlm.nih.gov/'+pmid+'/',
            publication_type=types, preprint='preprint' in types.lower(), retracted='retracted publication' in types.lower(),
            metadata_sources=['pubmed'], retrieved_at=stamp(), content_scope='abstract' if abstract else 'metadata')
        if meta.title:
            out.append(record(meta, abstract))
    return out

def parse_semantic(raw: dict):
    out=[]
    for p in raw.get('data',[]):
        ext=p.get('externalIds') or {};journal=p.get('journal') or {};abstract=p.get('abstract') or ''
        types='; '.join(p.get('publicationTypes') or [])
        arxiv=str(ext.get('ArXiv',''));d=doi(ext.get('DOI'))
        meta=ScholarlyMeta(title=p.get('title',''),authors=[parsed_author(a.get('name','')) for a in p.get('authors',[])],year=year_of(p.get('year')),
            journal=journal.get('name') or p.get('venue') or '',volume=str(journal.get('volume') or ''),pages=str(journal.get('pages') or ''),
            doi=d,pmid=str(ext.get('PubMed') or ''),pmcid=str(ext.get('PubMedCentral') or ''),arxiv_id=arxiv,
            url=safe_url(p.get('url')),fulltext_url=safe_url((p.get('openAccessPdf') or {}).get('url')),
            publication_type=types,preprint=('preprint' in types.lower() or bool(arxiv and not d and not journal)),
            metadata_sources=['semantic_scholar'],retrieved_at=stamp(),content_scope='abstract' if abstract else 'metadata')
        if meta.title:out.append(record(meta,abstract))
    return out

def parse_arxiv(raw:bytes):
    root=ET.fromstring(raw);ns={'a':'http://www.w3.org/2005/Atom','x':'http://arxiv.org/schemas/atom','o':'http://a9.com/-/spec/opensearch/1.1/'}
    total=int(text(root.find('o:totalResults',ns)) or 0);out=[]
    for p in root.findall('a:entry',ns):
        address=text(p.find('a:id',ns));title=' '.join(text(p.find('a:title',ns)).split())
        if not title or '/api/errors' in address:continue
        ident=address.split('/abs/')[-1];abstract=' '.join(text(p.find('a:summary',ns)).split())
        pdf=next((l.attrib.get('href','') for l in p.findall('a:link',ns) if l.attrib.get('title')=='pdf'),'')
        meta=ScholarlyMeta(title=title,authors=[parsed_author(text(a.find('a:name',ns))) for a in p.findall('a:author',ns)],
            year=year_of(text(p.find('a:published',ns))),doi=doi(text(p.find('x:doi',ns))),arxiv_id=ident,
            journal=text(p.find('x:journal_ref',ns)),url='https://arxiv.org/abs/'+ident,
            fulltext_url=safe_url(pdf).replace('http://','https://',1),publication_type='Preprint',preprint=True,
            metadata_sources=['arxiv'],retrieved_at=stamp(),content_scope='abstract' if abstract else 'metadata')
        out.append(record(meta,abstract))
    return out,total

def parse_crossref(raw:dict):
    out=[]
    for p in raw.get('message',{}).get('items',[]):
        titles=p.get('title') or [];title=titles[0] if titles else ''
        if not title:continue
        dp=(p.get('published') or p.get('published-print') or p.get('published-online') or {}).get('date-parts') or [[]]
        abstract=BeautifulSoup(p.get('abstract') or '', 'html.parser').get_text(' ',strip=True)
        journal=(p.get('container-title') or [''])[0];typ=p.get('type','')
        retracted=any('retract' in str(x.get('type','')).lower() for x in p.get('update-to',[]))
        meta=ScholarlyMeta(title=title,authors=[ResearchAuthor(family=a.get('family',''),given=a.get('given',''),literal=a.get('name','')) for a in p.get('author',[])],
            year=year_of(dp[0][0] if dp[0] else None),journal=journal,volume=p.get('volume',''),issue=p.get('issue',''),pages=p.get('page') or p.get('article-number') or '',
            doi=doi(p.get('DOI')),url=safe_url(p.get('URL')),publication_type=typ,preprint=typ=='posted-content',retracted=retracted,
            metadata_sources=['crossref'],retrieved_at=stamp(),content_scope='abstract' if abstract else 'metadata')
        out.append(record(meta,abstract))
    return out

def parse_europe(raw:dict):
    out=[]
    for p in raw.get('resultList',{}).get('result',[]):
        journal=p.get('journalInfo') or {};abstract=BeautifulSoup(p.get('abstractText') or '', 'html.parser').get_text(' ',strip=True)
        authors=[]
        for a in (p.get('authorList') or {}).get('author',[]):
            authors.append(ResearchAuthor(family=a.get('lastName',''),given=a.get('firstName',''),literal=a.get('collectiveName','')))
        if not authors:authors=[parsed_author(a.strip()) for a in p.get('authorString','').split(',') if a.strip()]
        meta=ScholarlyMeta(title=p.get('title',''),authors=authors,year=year_of(p.get('pubYear')),journal=(journal.get('journal') or {}).get('title',''),
            volume=journal.get('volume',''),issue=journal.get('issue',''),pages=p.get('pageInfo',''),doi=doi(p.get('doi')),pmid=str(p.get('pmid') or ''),pmcid=p.get('pmcid',''),
            url='https://europepmc.org/article/'+str(p.get('source','MED'))+'/'+str(p.get('id','')),
            publication_type='; '.join((p.get('pubTypeList') or {}).get('pubType',[])),preprint=p.get('source')=='PPR',retracted=p.get('isRetracted')=='Y',
            metadata_sources=['europe_pmc'],retrieved_at=stamp(),content_scope='abstract' if abstract else 'metadata')
        if meta.title:out.append(record(meta,abstract))
    return out

class ScholarlyClient:
    def __init__(self,vault=None,job=None,transport=None):
        self.vault,self.job,self.transport=vault,job,transport
    def check(self):
        if self.job:self.job.check()
    def get(self,db,url,params=None,headers=None):
        self.check()
        for attempt in range(2):
            with _LOCKS[db]:
                wait=max(0,_INTERVAL[db]-(time.monotonic()-_LAST[db]))
                if self.transport is None:
                    if self.job:
                        if self.job.cancel.wait(wait):self.job.check()
                    else:time.sleep(wait)
                _LAST[db]=time.monotonic()
                with httpx.Client(timeout=30,follow_redirects=False,transport=self.transport) as c:
                    with c.stream('GET',url,params=params,headers={'User-Agent':'GraphPaper/0.3 scholarly research (https://github.com/AronAxe/GraphPaper)',**(headers or {})}) as res:
                        if res.status_code in {429,502,503} and attempt==0:
                            if self.transport is None:
                                delay=min(15,max(2,int(res.headers.get('Retry-After','3')))) if res.headers.get('Retry-After','3').isdigit() else 3
                                if self.job:
                                    if self.job.cancel.wait(delay):self.job.check()
                                else:time.sleep(delay)
                            continue
                        if res.status_code!=200:raise ValueError(f'{NAMES[db]} returned HTTP {res.status_code}. '+('Add its optional API key or try later.' if res.status_code in {401,403,429} else 'This database did not complete.'))
                        chunks=[];size=0
                        for chunk in res.iter_bytes():
                            size+=len(chunk);self.check()
                            if size>12_000_000:raise ValueError('Scholarly response exceeds 12 MB.')
                            chunks.append(chunk)
                        return b''.join(chunks)
        raise ValueError(f'{NAMES[db]} temporarily unavailable.')
    def key(self,name):
        return self.vault.get(name) if self.vault else ''
    def search(self,db,query,plan):
        import json
        limit=plan.per_database;start=plan.year_from;end=plan.year_to
        actual=query
        if db=='pubmed':
            if start or end:actual+=f' AND ("{start or 1400}"[Date - Publication] : "{end or 2200}"[Date - Publication])'
            extra={'api_key':self.key('ncbi')} if self.key('ncbi') else {}
            base='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
            data=json.loads(self.get(db,base+'esearch.fcgi',{'db':'pubmed','term':actual,'retmode':'json','retmax':limit,'sort':'relevance','tool':'GraphPaper',**extra}))['esearchresult']
            ids=data.get('idlist',[]);total=int(data.get('count',0))
            rows=parse_pubmed(self.get(db,base+'efetch.fcgi',{'db':'pubmed','id':','.join(ids),'retmode':'xml','tool':'GraphPaper',**extra})) if ids else []
        elif db=='semantic_scholar':
            params={'query':actual,'limit':limit,'fields':'title,abstract,year,authors,externalIds,url,venue,journal,publicationTypes,openAccessPdf'}
            if start or end:params['year']=f'{start or ""}:{end or ""}'
            headers={'x-api-key':self.key('semantic_scholar')} if self.key('semantic_scholar') else {}
            data=json.loads(self.get(db,'https://api.semanticscholar.org/graph/v1/paper/search',params,headers))
            rows,total=parse_semantic(data),int(data.get('total',0))
        elif db=='arxiv':
            if not re.search(r'\b(?:all|ti|au|abs|cat|id):',actual):
                actual=' AND '.join('all:'+w for w in re.findall(r'\w+',actual)[:24])
            if start or end:actual+=f' AND submittedDate:[{start or 1400}01010000 TO {end or 2200}12312359]'
            rows,total=parse_arxiv(self.get(db,'https://export.arxiv.org/api/query',{'search_query':actual,'start':0,'max_results':limit,'sortBy':'relevance','sortOrder':'descending'}))
        elif db=='crossref':
            params={'query':actual,'rows':limit};filters=['type:journal-article']
            if start:filters.append(f'from-pub-date:{start}-01-01')
            if end:filters.append(f'until-pub-date:{end}-12-31')
            if filters:params['filter']=','.join(filters)
            data=json.loads(self.get(db,'https://api.crossref.org/works',params))
            rows,total=parse_crossref(data),int(data.get('message',{}).get('total-results',0))
        elif db=='europe_pmc':
            if start or end:actual+=f' AND FIRST_PDATE:[{start or 1400}-01-01 TO {end or 2200}-12-31]'
            data=json.loads(self.get(db,'https://www.ebi.ac.uk/europepmc/webservices/rest/search',{'query':actual,'format':'json','resultType':'core','pageSize':limit}))
            rows,total=parse_europe(data),int(data.get('hitCount',0))
        else:raise ValueError('Unknown scholarly database')
        return rows,{'database':db,'query':actual,'requested_query':query,'total_hits':total,'retrieved':len(rows),'limit':limit,'truncated':total>len(rows),'searched_at':stamp(),'status':'ok','error':''}
    def fulltext(self,record):
        meta=record.metadata
        if meta.pmcid:
            pmcid=meta.pmcid if meta.pmcid.startswith('PMC') else 'PMC'+meta.pmcid
            if not re.fullmatch(r'PMC\d+',pmcid):raise ValueError('Invalid PMC identifier')
            raw=self.get('europe_pmc',f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML')
            root=ET.fromstring(raw)
            body=root.find('body')
            if body is None:raise ValueError('No accessible full-text body was returned.')
            parts=[text(n) for n in body.iter() if n.tag in {'title','p'}]
            content='\n\n'.join(parts)
            if not content.strip():raise ValueError('The full-text response was empty.')
            return content[:2_000_000],f'https://europepmc.org/articles/{pmcid}',len(content)>2_000_000
        url=meta.fulltext_url
        if not url and meta.arxiv_id:url='https://arxiv.org/pdf/'+meta.arxiv_id
        if not url:raise ValueError('No open full-text link. Upload a licensed copy and attach it to this paper.')
        from .ingest import fetch_url
        title,content,url,warnings=fetch_url(url)
        if any('Web text only' in w for w in warnings):raise ValueError('The full-text link returned an HTML landing page, not a verified complete paper. Upload the full document instead.')
        if len(content)<300:raise ValueError('Full-text link returned too little readable content. Upload the paper instead.')
        return content,url,False

def keys_for(r):
    m=r.metadata;keys=[]
    if m.doi:keys.append('doi:'+m.doi.lower())
    if m.pmid:keys.append('pmid:'+m.pmid)
    if m.arxiv_id:keys.append('arxiv:'+re.sub(r'v\d+$','',m.arxiv_id))
    title=re.sub(r'\W+','',m.title.casefold())
    if len(title)>30 and m.year:keys.append('title:'+title+':'+str(m.year))
    return keys or ['id:'+r.id]

def merge_records(existing, incoming):
    result=[r.model_copy(deep=True) for r in existing];index={k:r for r in result for k in keys_for(r)};duplicates=0
    for new in incoming:
        prior=next((index[k] for k in keys_for(new) if k in index),None)
        if prior is None:
            if len(result)>=600:raise ValueError('Research library reached 600 unique records. Narrow the search.')
            result.append(new);prior=new
        else:
            duplicates+=1
            prior.metadata.metadata_sources=list(dict.fromkeys(prior.metadata.metadata_sources+new.metadata.metadata_sources))
            prior.searches=list(dict.fromkeys(prior.searches+new.searches))
            if len(new.abstract)>len(prior.abstract) and not prior.source_id:prior.abstract=new.abstract
            for k in ['doi','pmid','pmcid','arxiv_id','journal','volume','issue','pages','year','fulltext_url']:
                if not getattr(prior.metadata,k):setattr(prior.metadata,k,getattr(new.metadata,k))
            if not prior.metadata.authors:prior.metadata.authors=new.metadata.authors
            prior.metadata.retracted |= new.metadata.retracted
            if prior.abstract and prior.metadata.content_scope=='metadata':prior.metadata.content_scope='abstract'
        for k in keys_for(new):index[k]=prior
        for k in keys_for(prior):index[k]=prior
    return result,duplicates

"""APA author-year citations and references from structured scholarly metadata."""
from __future__ import annotations
import re
from collections import defaultdict


def initials(given):
    if re.fullmatch(r'[A-Z]{1,6}',given.strip()):
        return ' '.join(c+'.' for c in given.strip())
    return ' '.join('-'.join(x[0].upper()+'.' for x in part.split('-') if x) for part in re.findall(r'[\w]+(?:-[\w]+)*',given) if part)


def author_reference(author):
    return author.literal or author.family+(', '+initials(author.given) if author.given else '')


def authors_reference(authors):
    names=[author_reference(a) for a in authors]
    if len(names)>20:return ', '.join(names[:19])+', . . . '+names[-1]
    if len(names)>1:return ', '.join(names[:-1])+', & '+names[-1]
    return names[0] if names else ''


def author_label(meta):
    names=[a.literal or a.family for a in meta.authors]
    if not names:return '"'+meta.title[:65].rstrip('.')+'"'
    if len(names)==1:return names[0]
    if len(names)==2:return ' & '.join(names)
    return names[0]+' et al.'


def bibliography_sources(project,only_cited=True):
    used=set(re.findall(r'\[(S\d+)\]',project.draft))
    return [s for s in project.sources if s.enabled and s.role=='evidence' and s.scholarly and (not only_cited or s.id in used)]


def citation_map(project):
    sources=bibliography_sources(project,False)
    groups=defaultdict(list)
    used=set(re.findall(r'\[(S\d+)\]',project.draft))
    selected=[s for s in sources if s.id in used] if used else sources
    for s in selected:
        m=s.scholarly
        groups[(tuple((a.family,a.given,a.literal) for a in m.authors),m.year)].append(s)
    suffix={}
    for values in groups.values():
        if len(values)>1:
            for i,s in enumerate(sorted(values,key=lambda s:s.scholarly.title.casefold())):
                suffix[s.id]=chr(97+i) if i<26 else str(i+1)
    labels={}
    collisions=defaultdict(list)
    for s in sources:collisions[(author_label(s.scholarly),s.scholarly.year)].append(s)
    for s in sources:
        m=s.scholarly
        label=author_label(m)
        peers=collisions[(label,m.year)]
        if len(m.authors)>2 and len({tuple((a.family,a.given,a.literal) for a in x.scholarly.authors) for x in peers})>1:
            names=[a.literal or a.family for a in m.authors]
            for count in range(2,len(names)+1):
                prefix=tuple(names[:count])
                if sum(tuple((a.literal or a.family) for a in x.scholarly.authors[:count])==prefix for x in peers)==1:
                    label=', '.join(names[:count])+(', et al.' if count<len(names) else '')
                    break
        labels[s.id]={'label':label,'year':str(m.year or 'n.d.')+suffix.get(s.id,''),'suffix':suffix.get(s.id,'')}
    return labels


def inline_citations(project,body):
    mapping=citation_map(project)
    # Keep citations inside sentence-ending punctuation, as APA requires.
    body=re.sub(r'([.!?])[ \t]+(\[S\d+\](?:[ \t]*\[S\d+\])*)',r' \2\1',body)
    def replace(group):
        ids=re.findall(r'\[(S\d+)\]',group[0]);groups=defaultdict(list);unknown=[]
        for ident in dict.fromkeys(ids):
            m=mapping.get(ident)
            if m:groups[m['label']].append(m['year'])
            else:unknown.append('[UNRESOLVED CITATION '+ident+']')
        parts=[label+', '+', '.join(sorted(set(years))) for label,years in sorted(groups.items(),key=lambda item:item[0].casefold())]
        return '('+'; '.join(parts+unknown)+')'
    return re.sub(r'\[S\d+\](?:[ \t]*\[S\d+\])*',replace,body)


def reference_parts(source,mapping):
    m=source.scholarly
    if m.reference_override.strip():
        return [(x.strip('*') if x.startswith('*') else x, x.startswith('*')) for x in re.split(r'(\*[^*]+\*)', m.reference_override.strip()) if x]
    date=mapping[source.id]['year']
    name=authors_reference(m.authors)
    title=m.title.strip().rstrip('.')
    parts=[]
    if name:parts.append((name+' ('+date+'). ',False))
    if m.preprint:
        parts.append((title,True))
        if not name:parts.append((' ('+date+').',False))
        parts.append((' [Preprint]. '+('arXiv' if m.arxiv_id else 'Preprint repository')+'. ',False))
        address='https://arxiv.org/abs/'+m.arxiv_id if m.arxiv_id else ('https://doi.org/'+m.doi if m.doi else m.url)
        parts.append((address,False))
        return parts
    parts.append((title+'. ',not bool(m.journal)))
    if not name:parts.append(('('+date+'). ',False))
    if m.journal:
        parts.append((m.journal.rstrip('.'),True))
        if m.volume:
            parts.append((', '+m.volume,True))
            if m.issue:parts.append(('('+m.issue+')',False))
        elif m.issue:parts.append((' ('+m.issue+')',False))
        if m.pages:parts.append((', '+m.pages.replace('-','–'),False))
        parts.append(('. ',False))
    address='https://doi.org/'+m.doi if m.doi else m.url
    if address:parts.append((address,False))
    return parts


def references(project):
    mapping=citation_map(project)
    sources=sorted(bibliography_sources(project),key=lambda s:((authors_reference(s.scholarly.authors) or s.scholarly.title).casefold(),mapping[s.id]['year'],s.scholarly.title.casefold()))
    return [(s,reference_parts(s,mapping)) for s in sources]


def title_of(project):
    match=re.match(r'^#\s+(.+)',project.draft)
    return match[1] if match else project.title


def body_of(project):
    return re.sub(r'^#\s+[^\n]+\n*','',project.draft,count=1).strip()


def markdown(project):
    plan=project.research.plan
    content='# '+title_of(project)+'\n\n'+plan.author_names+'\n\n'+plan.affiliation+'\n\n'
    content+='## Abstract\n\n'+project.research.abstract+'\n\n*Keywords:* '+', '.join(project.research.keywords)+'\n\n'
    content+=inline_citations(project,body_of(project))+'\n\n## References\n\n'
    content+='\n\n'.join(''.join('*'+t+'*' if italic else t for t,italic in parts) for _,parts in references(project))
    return content.strip()+'\n'

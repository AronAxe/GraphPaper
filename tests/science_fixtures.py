"""Clearly synthetic science/provider responses for reproducible UI and pipeline tests."""
import json
from .conftest import ScriptedClients
from graphpaper.science_models import ScholarlyMeta, ResearchAuthor
from graphpaper.scholarly import record, stamp


def papers():
    result=[]
    for index in range(2):
        meta=ScholarlyMeta(title=f'Synthetic test fixture: memory study {index+1}',authors=[ResearchAuthor(family='Example',given='Alex'),ResearchAuthor(family='Researcher',given='Bea')],year=2024+index,journal='Test Fixture Journal',volume='2',issue='1',pages='10-18',doi=f'10.9999/graphpaper-fixture-{index+1}',url=f'https://example.org/test-fixture-{index+1}',metadata_sources=['pubmed'],retrieved_at=stamp(),content_scope='abstract')
        result.append(record(meta,'This is synthetic test material, not an actual scientific paper. Participants completed a memory task. The observed difference was uncertain. The small sample limits interpretation.'))
    return result


class FakeScholar:
    def __init__(self,*args,**kwargs):pass
    def search(self,db,query,plan):
        rows=papers()
        for row in rows:row.metadata.metadata_sources=[db]
        return rows,{'database':db,'query':query,'requested_query':query,'total_hits':2,'retrieved':2,'limit':plan.per_database,'truncated':False,'searched_at':stamp(),'status':'ok','error':''}
    def fulltext(self,r):
        return r.abstract+'\n\nMethod\nThis full-text fixture contains no actual experiment.\n\nDiscussion\nInterpret cautiously.','https://example.org/fulltext-fixture',False


class ScienceClients(ScriptedClients):
    scholarly_factory=FakeScholar
    def complete(self,system,user,*,role='writer',json_mode=False,max_tokens=None):
        try:data=json.loads(user)
        except ValueError:return super().complete(system,user,role=role,json_mode=json_mode,max_tokens=max_tokens)
        task=data.get('task','')
        if task.startswith('Propose a reproducible'):
            self._record(role)
            return {'queries':['memory AND sleep'],'inclusion':'Human memory studies','exclusion':'Unrelated outcomes','rationale':'Compare relevant evidence and limitations.'}
        if task.startswith('Appraise this paper'):
            self._record(role)
            return {'summary':'The accessible fixture reports an uncertain difference.','design':'Memory task; further design information is not reported.','sample':'Small sample; exact size not reported.','findings':'The observed difference was uncertain.','limitations':['Small sample and synthetic fixture.'],'contrary_evidence':'Uncertainty does not support a strong positive conclusion.','claims':[{'claim':'The observed difference was uncertain.','quote':'The observed difference was uncertain.'}],'appraisal_note':'No claim of real research.'}
        if task.startswith('Outline an APA'):
            self._record(role)
            return {'title':'Memory and sleep: A synthetic research workflow test','sections':[{'title':name,'purpose':'Explain the question and its evidence.','beats':['Present the supplied material and uncertainty.'],'source_ids':['S1','S2'],'target_words':600} for name in data['required_sections']]}
        if task.startswith('Write this manuscript section'):
            self._record(role)
            return 'The synthetic records describe a memory task, but the observed difference was uncertain. [S1] [S2] The available evidence therefore does not establish a robust causal effect. The small sample limits interpretation.'
        if task.startswith('Write a 150-250 word abstract'):
            self._record(role)
            return {'abstract':'This synthetic manuscript tests a literature-research workflow. Two synthetic records were retrieved and screened. The available findings were uncertain; no actual experiment or scientific result is claimed. The exercise demonstrates source-linked drafting and reference export.','keywords':['memory','literature review','test fixture']}
        return super().complete(system,user,role=role,json_mode=json_mode,max_tokens=max_tokens)

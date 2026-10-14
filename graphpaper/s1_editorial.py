"""Meaning, authorial intent and editorial actions are independent judgments."""
from __future__ import annotations
import difflib
import json
import re
from .system_one import Engine, noul, score, choice, probability, normalized, angle_policy, choice_action, YES, NO
from .editorial import context, contract

CRAFT = ['A generic restatement without a developed point.','An identifiable point with some specific development.','A distinctive, concrete point with a purposeful opening or payoff.','A distinctive point developed through precise, compelling rhetorical movement.']
NOVELTY = ['Repeats a supplied point without adding a connection.','Adds an example of an already stated connection.','Combines supplied ideas into a useful new perspective.','Uncovers a specific unexpected connection worth developing.']


def angle_questions(item=None):
    qs={
        'craft':score('How specifically developed is the proposed argument or story premise?',CRAFT),
        'novelty':score('What new connection does this proposal contribute beyond its supplied material?',NOVELTY),
        'stance_fidelity':noul('Does the proposal retain the author’s stated position? In exploratory work, does it keep the question open as requested?'),
        'reasoning_preserved':noul('Does the proposal retain the distinct essential steps of the author’s reasoning rather than collapse them into one generic slogan?'),
        'voice_fidelity':noul('Does its rhetorical delivery match the requested voice and force? Strong language is not a defect.'),
        'grounded':noul('Are the factual premises supported by the supplied evidence or established fiction canon? Moral judgments and explicit analogies do not require empirical proof of the judgment itself.'),
        'added_allegation':noul('Does the proposal add a factual allegation, diagnosis or hidden motive absent from the brief and supplied evidence?'),
        'irrelevant_caveat':noul('Does it volunteer a disclaimer or objection to a stronger or different claim the author never made?'),
        'needs_research':noul('Does a specifically asserted, essential factual premise lack supporting evidence in the supplied material? Do not request evidence merely for a value judgment or joke.'),
    }
    for i,test in enumerate((item or {}).get('evaluation_questions',[])[:3]):
        qs['tailored_'+str(i)]=noul('Candidate-specific editorial test, subject to the authorial contract: '+str(test)[:500])
    return qs


def assess_angles(p,clients,evidence=None):
    items=[]
    if evidence is None:
        from .pipeline import source_pack
        evidence={a.id:source_pack(p,a.thesis,9000,a.source_ids)['passages'] for a in p.angles}
    for a in p.angles:
        item={'id':a.id,'title':a.title,'thesis':a.thesis,'hook':a.hook,'evidence':(evidence or {}).get(a.id,[]),
              'source_ids':a.source_ids,'evaluation_questions':p.system_one.get('angle_tests',{}).get(a.id,[])}
        items.append(item)
    answers=Engine(clients,p).evaluate('angle fidelity',items,angle_questions,context(p,compact=True,include_selection=False))
    policies=p.system_one.setdefault('angle_policies',{})
    for a in p.angles:
        row=answers.get(a.id,{})
        decision=angle_policy(row,p.mode=='polemic' or p.brief.stance_policy=='preserve')
        policies[a.id]=decision
        if row:
            a.scores={k:normalized(v) for k,v in row.items()}
            # Scores are descriptive scales; probabilities remain separate in receipts.
            a.score=round(100*(.6*normalized(row.get('craft'))+.4*normalized(row.get('novelty'))),1)
            a.score_engine='System One craft/novelty · fidelity checked separately'
        else:
            a.scores={};a.score=None;a.score_engine='unscored'
        a.decision={'repair_intent':'Restore author intent','research':'Research first','author_review':'Author review · uncertain','ready':'Ready to develop','unscored':'Unscored · author choice'}[decision['action']]
    p.angles.sort(key=lambda a:(policies[a.id]['eligible'], a.score is not None, a.score or 0),reverse=True)
    return answers


def repair_angles(p,clients,job,evidence=None):
    """One targeted repair call, never a demand that the author moderate a view."""
    if not getattr(clients.settings,'system_one_fidelity',True):return
    policies=p.system_one.get('angle_policies',{})
    targets=[a for a in p.angles if policies.get(a.id,{}).get('action')=='repair_intent']
    if not targets:return
    from .editorial import system
    job.note('System One identified authorial drift; repairing only the affected angle proposals.')
    from .providers import ProviderError
    try:
        raw=clients.complete(system(p,'angles'),json.dumps({'task':'Repair only the listed angle proposals under the authorial contract. Restore each missing argument, voice or conclusion. Fix only the listed issues; do not introduce a balancing stance. Preserve IDs. Return {"angles":[{"id":"existing ID","title":"title","thesis":"repaired thesis","hook":"opening"}]}.',
            'targets':[{'angle':a.model_dump(),'repairs':policies[a.id]['reasons'],'evidence':(evidence or {}).get(a.id,[])} for a in targets],**context(p)},ensure_ascii=False),json_mode=True)
    except ProviderError as exc:
        job.note('Kept generated proposals: the optional intent repair was unavailable. '+str(exc)[:160])
        return
    proposals={x.get('id'):x for x in raw.get('angles',[]) if isinstance(x,dict)}
    originals=p.system_one.setdefault('angle_originals',{})
    for a in targets:
        new=proposals.get(a.id)
        if not new or not isinstance(new.get('thesis'),str) or not new['thesis'].strip():continue
        originals[a.id]=a.model_dump()
        for key,limit in [('title',300),('thesis',4000),('hook',2000)]:
            if isinstance(new.get(key),str):setattr(a,key,new[key][:limit])
    assess_angles(p,clients,evidence)


def changed_passages(original,candidate,limit=24):
    """Changed blocks plus neighbors; every omission is explicitly accounted for."""
    before=original.split('\n\n');after=candidate.split('\n\n')
    changes=[]
    for tag,a,b,c,d in difflib.SequenceMatcher(a=before,b=after,autojunk=False).get_opcodes():
        if tag=='equal':continue
        changes.append({'id':'change_'+str(len(changes)),'operation':tag,
            'original':'\n\n'.join(before[max(0,a-1):min(len(before),b+1)]),
            'candidate':'\n\n'.join(after[max(0,c-1):min(len(after),d+1)]),
            'before_range':[a,b],'after_range':[c,d]})
    return changes[:limit]


def assess_edit(p,clients,original,candidate,instruction=''):
    if not Engine(clients,p).enabled or not getattr(clients.settings,'system_one_fidelity',True):
        return {'decision':'escalate','meaning_preserved':None,'summary':'System One disabled; use the contextual editor.','checks':{}}
    total=changed_passages(original,candidate,10001);items=total[:24]
    complete=len(total)<=24 and all(len(x['original'])+len(x['candidate'])<18000 for x in items)
    eligible=[x for x in items if len(x['original'])+len(x['candidate'])<18000]
    qs={'meaning_drift':noul('Does the candidate change a material proposition, causal direction, narrator fact or intended ending in the original, beyond the current author instruction?'),
        'stance_fidelity':noul('Does the candidate preserve the intended judgment and its force, unless the current instruction asks for a change?'),
        'voice_fidelity':noul('Does the candidate preserve or improve the author’s requested rhetorical delivery?'),
        'improved':noul('Does the candidate fix a concrete prose or argument problem in the original?'),
        'lost_reasoning':noul('Does the candidate remove an essential step of the reasoning or story consequence?')}
    rows=Engine(clients,p).evaluate('changed passage fidelity',eligible,qs,{**context(p,compact=True),'author_instruction':instruction},reserve=3)
    if not total:return {'decision':'unchanged','meaning_preserved':True,'stance_preserved':True,'voice_preserved':True,'summary':'No changed prose.','warnings':[],'improvements':[]}
    unsafe=any(probability(a,'meaning_drift')>=YES or probability(a,'lost_reasoning')>=YES or probability(a,'stance_fidelity')<=NO for a in rows.values())
    safe=complete and len(rows)==len(items) and all(probability(a,'meaning_drift')<=NO and probability(a,'lost_reasoning')<=NO and probability(a,'stance_fidelity')>=YES and probability(a,'voice_fidelity')>=YES for a in rows.values())
    decision='reject' if unsafe else 'present' if safe else 'escalate'
    return {'decision':decision,'meaning_preserved':False if unsafe else True if safe else None,'stance_preserved':not unsafe if safe or unsafe else None,
        'voice_preserved':True if safe else None,'summary':{'reject':'A focused check detected meaning or authorial drift. The original remains in place.','present':'Focused changed-passage checks support presenting this edit for the author to compare.','escalate':'Some changed passages need a full contextual editorial review.'}[decision],
        'warnings':[] if safe else ['Inspect the changed passages and the original conclusion.'],
        'improvements':['Focused comparison completed.'] if safe else [],'coverage':{'checked':len(rows),'total_changes':len(total),'complete':complete},
        'checks':rows,'improved':any(probability(a,'improved')>=YES for a in rows.values())}


def audit_passages(p,clients,text,pack):
    """Independent local checks, not just repeating the LLM editor's findings."""
    paragraphs=[x for x in re.split(r'\n\s*\n',text) if x.strip() and not x.lstrip().startswith('#')]
    selected=sorted(range(len(paragraphs)),key=lambda i:(bool(re.search(r'\[S\d+\]|\d',paragraphs[i])),len(paragraphs[i])),reverse=True)[:16]
    items=[]
    for i in selected:
        passage=paragraphs[i]
        if len(passage)>6000:continue
        ids=set(re.findall(r'\[(S\d+)\]',passage))
        evidence=[e for e in pack.get('passages',[]) if e['source_id'] in ids] if ids else pack.get('passages',[])[:2]
        # Context is bounded and coverage explicitly says excerpts, not full corpus.
        items.append({'id':'paragraph_'+str(i),'paragraph':passage,'source_excerpts':evidence[:2],
                      'canon':p.brief.canon if p.mode=='fiction' else '', 'scope':'Selected source excerpts only.'})
    qs={'factual_assertion':noul('Does the paragraph assert an externally checkable factual proposition, rather than only a value judgment, analogy or joke?'),
        'supported':noul('Are its material factual premises supported by the supplied source excerpts or established fiction canon? If the text only states values or jokes answer yes; absence of an excerpt is not proof of falsity.'),
        'irrelevant_caveat':noul('Does it weaken a moral judgment using a disclaimer about an empirical allegation the author did not make?'),
        'canon_conflict':noul('For fiction only: does the paragraph contradict an explicit supplied canon fact? Answer no for other modes.')}
    rows=Engine(clients,p).evaluate('independent passage audit',items,qs,context(p,compact=True))
    findings=[]
    for item in items:
        a=rows.get(item['id'],{})
        if probability(a,'factual_assertion',0)>=YES and probability(a,'supported')<=NO:
            findings.append({'severity':'major','category':'evidence','excerpt':item['paragraph'],'problem':'System One could not establish a material factual premise from the supplied excerpts.','suggestion':'Inspect the source context; a missing excerpt is not a claim that the premise is false.'})
        if probability(a,'irrelevant_caveat',0)>=YES:
            findings.append({'severity':'major','category':'authorial_drift','excerpt':item['paragraph'],'problem':'A disclaimer appears to answer an allegation the author did not make.','suggestion':'Remove that detour while preserving necessary factual qualifications.'})
        if probability(a,'canon_conflict',0)>=YES:
            findings.append({'severity':'major','category':'continuity','excerpt':item['paragraph'],'problem':'The passage may contradict supplied canon.','suggestion':'Check the identified passage against the canon; retain the intended story.'})
    p.system_one['passage_audit']={'checked':len(rows),'total_paragraphs':len(paragraphs),'scope':'Bounded independent passage checks, not exhaustive truth certification.','findings':findings}
    return findings


def review_action(p,clients,findings):
    specs={'action':choice('What action follows from these concrete findings under the author’s contract?',{
        'research':'An essential asserted factual premise needs additional evidence.',
        'revise':'A known, local, material flaw can be repaired with available material.',
        'author_review':'Keep the draft for the author; no high-confidence automatic repair is justified.'}),
        'material_issue':noul('Do the findings identify a specific consequential factual, logical, narrative or authorial-fidelity problem?'),
        'fixable':noul('Can the listed material issue be corrected using already supplied material, without inventing evidence or moderating the author’s position?')}
    rows=Engine(clients,p).evaluate('next editorial action',[{'id':'review','findings':findings}],specs,context(p,compact=True))
    a=rows.get('review',{});action=choice_action(a.get('action'))
    if action=='revise' and (probability(a,'material_issue')<YES or probability(a,'fixable')<YES):action='author_review'
    if a:a['executed_action']={'type':'policy','choice':action,'reason':'Distribution, margin and material-issue checks govern automatic action.'}
    return a,action

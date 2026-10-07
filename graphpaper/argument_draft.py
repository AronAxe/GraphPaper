"""Draft a short argumentative piece coherently, rather than restarting its caveats per section."""
from .editorial import system,context


def use_whole_draft(project):
    return (project.mode=='polemic' or (project.mode=='nonfiction' and project.brief.stance_policy=='preserve')) and bool(project.outline) and sum(s.target_words for s in project.outline)<=3000


def write_whole_argument(project,clients,store,job):
    from .pipeline import selected_angle,source_pack,dumps,review_draft,revise
    angle=selected_angle(project)
    total=sum(s.target_words for s in project.outline)
    query=angle.thesis+'\n'+'\n'.join(s.purpose+' '+' '.join(s.beats) for s in project.outline)
    pack=source_pack(project,query,min(42000,clients.settings.context_chars//2),angle.source_ids)
    job.note('Writing the argument as one coherent piece, with a single treatment of its factual limits.',15)
    task='''Write the complete argumentative essay in Markdown, following the approved outline and the authorial contract. Start with its title and an actual opening, not a synopsis of what the essay would explore. Develop all distinct strands of the author\'s reasoning, with progression rather than repetition. Keep wit, indignation, moral judgment and the intended ending. Establish a genuinely necessary empirical limitation where it belongs, then advance the argument: do not restart that caveat in every section or preface every criticism with what it does not prove. If the thesis already accepts a premise conditionally, do not spend the essay repeatedly disclaiming a stronger premise it never asserted. Do not volunteer diagnoses, violence predictions, unlimited-sacrifice hypotheticals or other propositions solely to disclaim them. Use [S#] references for material factual claims supported by the supplied evidence. Values, explicitly framed analogies and jokes are not scientific findings. Never invent reporting, evidence or references. Finish the actual argument rather than offering a neutral invitation to further discussion. Fictional/synthetic test scenarios must not be presented as real reporting.'''
    prompt={'task':task,'mode':project.mode,'brief':project.brief.model_dump(),'target_words':total,
            'angle':angle.model_dump(),'approved_outline':[s.model_dump() for s in project.outline],
            'source_passages':pack,**context(project)}
    text=clients.complete(system(project,'draft'),dumps(prompt))
    project.draft=text if text.lstrip().startswith('# ') else '# '+angle.title+'\n\n'+text
    project.story_state={}
    store.snapshot(project,'Complete argument draft')
    project.review=review_draft(project,clients,job)
    if clients.settings.refine and project.review.scores.get('action',{}).get('choice')=='revise':
        revise(project,clients,job,store,automatic=True)
    job.note('Argument draft ready. The editor checked factual support and authorial fidelity separately.',98)

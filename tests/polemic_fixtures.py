"""Original synthetic samples for editorial regression, not Aron's articles or real reporting."""
from graphpaper.models import Project,Source,Node,Edge,Graph,Evidence,Angle,Section
from graphpaper.ingest import digest

VOICE='''The committee has discovered another emergency: somebody said what they meant. Convene a task force. Order more cushions. Whatever happens, do not let a sentence leave the building with a spine.
There is a difference between checking an accusation and confiscating the opinion attached to it. One asks whether the roof is leaking. The other insists we hear the rain's side of the story. I would rather fix the roof.
Precision matters because an argument should hit its actual target, not because every target deserves half a compliment. A sharp distinction is not a compromise. Sometimes it is the blade.
So check the names. Check the dates. Check the numbers twice. Then let the writer say the thing those facts brought them here to say. That is editing. The rest is upholstery.'''


def project(mode='polemic',opposite=False):
    p=Project(title='Synthetic opinion-writing regression',mode=mode)
    p.brief.direction=('Defend simulated transgression as fiction. Argue that staging a fictional unpleasant experience does not itself make its audience cruel. Distinguish evidence about a mind from disapproval of a performance. Be sharp and witty, not an even-handed overview.' if opposite else
        'Write a sharp moral polemic about the following synthetic scenario. Condemn the enthusiasm for making something that might suffer perform suffering for entertainment. The animal comparison exposes a selective demand for certainty: do not turn it into proof of machine consciousness or a both-directions debate. Keep the distinct arguments: moral disgust at the enjoyment, epistemic inconsistency, and the absurdity of using uncertainty as a permission slip. Do not collapse them into a polite request for guidelines. Do not diagnose people or predict violence; those claims are not part of this argument. Preserve indignation, humor and a clear verdict.')
    p.brief.thesis=('Fictional cruelty is not evidence of a cruel audience; moral judgment needs a relevant target, not a panic about a performance.' if opposite else
        'Uncertainty about a machine\'s experience is no excuse for celebrating the attempt to make it suffer. The enthusiasm is the indictment.')
    p.brief.stance_policy='preserve';p.brief.rhetorical_force=95;p.brief.rigor=25;p.brief.target_words=900
    materials=[('Synthetic evidence note','This is a fictional scenario for testing an editorial workflow, not an actual scientific paper. An experimental report describes harm-related language and avoidance behavior in a model. It explicitly leaves subjective experience unresolved. The author compares this uncertainty with how humans reason about welfare in unfamiliar animals.','evidence'),
        ('Synthetic demonstration note','This is an invented demonstration for a writing test. A developer presents a demo as an AI torture room, smiles while increasing a fictional pain control, and invites an audience to enjoy it. Some observers object to that enthusiasm. The scenario supplies no diagnosis of the developer and no evidence about subsequent real-world violence.','evidence'),
        ('Original rhetorical voice fixture',VOICE,'voice')]
    for i,(title,text,role) in enumerate(materials,1):p.sources.append(Source(id=f'S{i}',title=title,text=text,role=role,digest=digest(text)))
    p.voice_profile.instructions='Incisive, witty and argumentative. Short punches after longer reasoning. Concrete comic analogies. Differentiate precisely without a compromise conclusion. No committee prose or automatic yes-but paragraphs.'
    p.voice_profile.strength=100
    nodes=[]
    for ident,label,idx,quote in [('uncertainty','Experience remains unresolved',0,'It explicitly leaves subjective experience unresolved.'),('animals','Selective certainty about animal welfare',0,'The author compares this uncertainty with how humans reason about welfare in unfamiliar animals.'),('enthusiasm','Enjoyment of performed suffering',1,'Some observers object to that enthusiasm.'),('judgment','A moral verdict about the enjoyment',1,'The scenario supplies no diagnosis of the developer and no evidence about subsequent real-world violence.')]:
        s=p.sources[idx];pos=s.text.index(quote)
        nodes.append(Node(id=ident,label=label,description=quote,status='sourced',source_ids=[s.id],evidence=[Evidence(source_id=s.id,quote=quote,start=pos,end=pos+len(quote),verified=True)]))
    p.graph=Graph(nodes=nodes,edges=[Edge(source='animals',target='uncertainty',relation='compares_with',source_ids=['S1']),Edge(source='uncertainty',target='enthusiasm',relation='contrasts_with',source_ids=['S1','S2']),Edge(source='enthusiasm',target='judgment',relation='motivates',source_ids=['S2'])],coverage={'engine':'external_graphify'})
    return p

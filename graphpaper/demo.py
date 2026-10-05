"""Original, explicitly illustrative sample material; not real-world research."""
from .models import Project, Source, Brief, Node, Edge, Evidence, Graph, Angle, Section, now
from .graph import annotate
from .ingest import digest


def make_demo(mode="nonfiction"):
    if mode == "fiction":
        return fiction_demo()
    p = Project(title="The city that forgot the dark", mode="nonfiction", demo=True)
    p.brief = Brief(audience="Curious readers of long-form cultural essays", direction="Explore the tension between visibility, safety and the right to darkness. A thoughtful essay, not a simplistic case against streetlights.", voice="Observant, precise and quietly lyrical. Concrete images; fair counterarguments.", target_words=1600)
    texts = [
        ("Design notebook · light and attention", "These are original illustrative notes for a GraphPaper demo, not a published study.\n\nArtificial light changes not only what a street reveals, but what residents notice. Visibility can serve safety, while constant illumination can make darkness feel like a defect. A good lighting brief asks what must be visible, to whom, and when. The question is not simply whether to light a city, but whether every place requires the same kind of light. Light directed at the pavement and light spilling through a bedroom window are different design decisions. Darkness can be a shared resource rather than an absence waiting to be filled."),
        ("Editorial notes · the strongest objection", "These are original illustrative editorial notes, not testimony or collected data.\n\nA campaign for darker streets must address people who feel vulnerable walking at night. An aesthetic preference for stars does not override that concern. Safety and the experience of safety are related but distinct. Removing light without consulting residents is not participatory design. A useful alternative is selective illumination: use the right light in the right place at the right time. Debate often becomes trapped between total brightness and total darkness, overlooking choices about timing, direction and purpose."),
        ("Field sketch · the window and the square", "This invented scene is a writing exercise, not a report of an observed event.\n\nAt midnight the square was empty, but its lamps still shone into an upstairs bedroom. On the pavement, a walker paused to read a street sign. Two people occupied the same lighting design differently: one needed to see, the other needed not to see. The city could serve both by directing light rather than multiplying it. A window is a boundary between public infrastructure and private rest. Treating brightness as an unquestioned good obscures that boundary."),
    ]
    for i, (title, text) in enumerate(texts, 1):
        p.sources.append(Source(id=f"S{i}", title=title, text=text, digest=digest(text), warnings=["Illustrative demo text, not empirical evidence or a real-world case study."]))
    items = [
        ("light", "Artificial light", "concept", 0, "Artificial light changes not only what a street reveals, but what residents notice."),
        ("attention", "Directed attention", "concept", 0, "Artificial light changes not only what a street reveals, but what residents notice."),
        ("visibility", "Visibility", "concept", 0, "Visibility can serve safety, while constant illumination can make darkness feel like a defect."),
        ("safety", "Safety", "concept", 1, "Safety and the experience of safety are related but distinct."),
        ("perception", "Perceived safety", "claim", 1, "Safety and the experience of safety are related but distinct."),
        ("vulnerability", "The night walker", "person", 1, "A campaign for darker streets must address people who feel vulnerable walking at night."),
        ("darkness", "The right to darkness", "concept", 0, "Darkness can be a shared resource rather than an absence waiting to be filled."),
        ("commons", "A shared resource", "concept", 0, "Darkness can be a shared resource rather than an absence waiting to be filled."),
        ("window", "The bedroom window", "place", 2, "A window is a boundary between public infrastructure and private rest."),
        ("rest", "Private rest", "concept", 2, "A window is a boundary between public infrastructure and private rest."),
        ("square", "The empty square", "place", 2, "At midnight the square was empty, but its lamps still shone into an upstairs bedroom."),
        ("spill", "Light spill", "claim", 0, "Light directed at the pavement and light spilling through a bedroom window are different design decisions."),
        ("design", "Selective illumination", "concept", 1, "A useful alternative is selective illumination: use the right light in the right place at the right time."),
        ("time", "Time of night", "concept", 1, "Debate often becomes trapped between total brightness and total darkness, overlooking choices about timing, direction and purpose."),
        ("direction", "Direction, not more", "claim", 2, "The city could serve both by directing light rather than multiplying it."),
        ("residents", "Resident agency", "concept", 1, "Removing light without consulting residents is not participatory design."),
        ("binary", "A false binary", "claim", 1, "Debate often becomes trapped between total brightness and total darkness, overlooking choices about timing, direction and purpose."),
        ("stars", "An aesthetic argument", "claim", 1, "An aesthetic preference for stars does not override that concern."),
    ]
    for ident, label, kind, index, quote in items:
        s = p.sources[index]
        start = s.text.index(quote)
        p.graph.nodes.append(Node(id=ident, label=label, kind=kind, description=quote, evidence=[Evidence(source_id=s.id, quote=quote, start=start, end=start+len(quote), verified=True)], status="sourced"))
    relations = [("light","attention","shapes"),("light","visibility","enables"),("visibility","safety","can_support"),("safety","perception","distinct_from"),("vulnerability","safety","motivates"),("stars","vulnerability","must_address"),("darkness","commons","can_be"),("light","spill","can_produce"),("spill","window","crosses"),("window","rest","protects"),("square","window","illuminates"),("design","direction","uses"),("design","time","adapts_to"),("design","safety","seeks_to_support"),("design","darkness","can_preserve"),("residents","design","should_inform"),("binary","design","obscures"),("binary","visibility","overemphasizes"),("attention","binary","can_question"),("commons","residents","concerns"),("direction","rest","can_protect"),("vulnerability","square","moves_through"),("time","square","changes_use_of")]
    for i, (a,b,r) in enumerate(relations):
        p.graph.edges.append(Edge(id=f"ed{i}", source=a, target=b, relation=r, description="Illustrative relationship inferred from the demo notes.", status="inferred"))
    p.graph.engine = "Illustrative sample graph · not an AI run"
    p.graph.built = now()
    p.graph.coverage = {"sources":3,"chunks":3,"processed_chunks":3,"characters":sum(len(s.text) for s in p.sources)}
    p.graph.warnings = ["This workspace uses invented demo material. Its sample angles are unscored and should not be published as reported research."]
    annotate(p.graph)
    p.angles = [
        Angle(id="angle1",title="Not more light. Better darkness.",thesis="The most useful lighting debate is not brightness versus darkness, but who gets to decide what is illuminated, where and when.",hook="An empty square can be perfectly lit and a bedroom perfectly ruined by the same lamp.",why="Moves from a binary argument to design, agency and competing needs.",motif="cross-community bridge",node_ids=["window","rest","design","darkness","safety","residents"],source_ids=["S1","S2","S3"],counterargument="Darkness may make already vulnerable people feel less secure.",questions=["What real evidence distinguishes perceived safety from measured safety?", "Which local examples show selective illumination working?"],decision="Sample · needs real sources"),
        Angle(id="angle2",title="The invisible politics of being visible",thesis="A lighting plan distributes attention and privacy as well as illumination; those competing purposes deserve an explicit public conversation.",why="Connects the intimate scale of a window to the public scale of infrastructure.",motif="directed chain",node_ids=["light","attention","window","rest","residents"],source_ids=["S1","S2","S3"],counterargument="Practical lighting decisions must still meet concrete accessibility and safety needs.",questions=["Who participates in actual lighting decisions?"],decision="Sample · needs real sources"),
        Angle(id="angle3",title="When a brighter city sees less",thesis="Treating brightness as the goal can hide the underlying design question: what actually needs to be seen?",why="A precise category error, rather than a reflexively contrarian headline.",motif="contradiction",node_ids=["binary","visibility","design","direction"],source_ids=["S1","S2"],counterargument="Some places may genuinely require stronger illumination.",questions=["Find a documented lighting redesign with before-and-after outcomes."],decision="Sample · needs real sources"),
    ]
    p.selected_angle = "angle1"
    p.outline = [Section(title="One lamp, two lives",purpose="Open with a clearly signposted hypothetical scene that establishes competing needs.",beats=["The empty square and the bedroom window", "Why one person's helpful light is another person's intrusion"],source_ids=["S3"],target_words=350),Section(title="The question brightness cannot answer",purpose="Distinguish the amount of light from the purposes it serves.",beats=["Visibility is a means, not a complete design brief", "Take vulnerable walkers' concerns seriously"],source_ids=["S1","S2"],target_words=700),Section(title="Designing for both",purpose="Offer a constructive frame without claiming unverified outcomes.",beats=["Timing, direction and participation", "Darkness as something to design for, not impose"],source_ids=["S1","S2","S3"],target_words=550)]
    p.draft = "# Not more light. Better darkness.\n\n*Illustrative opening, written for the demo. The scene is hypothetical, not reported.*\n\nImagine a square at midnight. Its lamps pick out every seam in the pavement. A walker pauses beneath one to read a street sign. Above the square, behind a thin curtain, someone is trying to sleep.\n\nThe lamp has not failed. It is doing exactly what it was designed to do. The question is whether the design asked enough of it. [S3]\n\n## One lamp, two lives\n\nA conversation about public light can become an argument between two abstractions: brightness and darkness. But the walker and the sleeper are not abstractions. Each needs something the city can reasonably be asked to provide. Neither becomes less real because the other is easier to see. [S2] [S3]\n\nThe interesting question is not whether a city should be lit. It is whether lighting can be directed, timed and discussed carefully enough to serve different lives rather than treating every patch of darkness as an unfinished job. [S1] [S2]\n\n*Continue from the outline, or replace these sample notes with real sources before drafting a publishable article.*"
    return p


def fiction_demo():
    p = Project(title="The last keeper of borrowed mornings", mode="fiction", demo=True)
    p.brief = Brief(format="Short story", audience="Readers of literary speculative fiction", direction="A memory archivist must choose between restoring her father's final morning and preserving a stranger's only memory of home.",canon="Memories cannot be copied, only transferred. Every restoration permanently consumes another memory. Mira has never used the archive for herself. The city does not know the cost.",target_words=2400,voice="Intimate, sensory, restrained; emotional stakes without melodrama.",avoid="Expository monologues, a convenient loophole in the memory rules, a neatly explained moral.")
    text = "Mira is the city's memory archivist. Memories cannot be copied, only transferred. Every restoration permanently consumes another memory. Mira has never used the archive for herself. Her father died before she returned home. She wants his final morning. A stranger named Oren has deposited his only memory of home: his mother peeling an orange beside an open window. Restoring her father's morning would consume Oren's memory. Oren believes the archive is a safe place to keep it. The city does not know the cost of restoration. Mira keeps an empty orange crate under her workbench. The story must not invent a way to duplicate memories."
    p.sources = [Source(id="S1",title="Story bible · the memory archive",text=text,role="canon",digest=digest(text))]
    labels = [("mira","Mira","character"),("archive","The memory archive","place"),("father","Her father's final morning","event"),("oren","Oren","character"),("home","A memory of home","concept"),("transfer","Transfer, never copy","rule"),("cost","A permanent cost","rule"),("orange","The orange at the window","theme"),("trust","Entrusted, not given","theme")]
    p.graph.nodes = [Node(id=i,label=l,kind=k,description="Sample canon; inspect Story bible for the full context.",status="canon") for i,l,k in labels]
    links = [("mira","archive","works_at"),("mira","father","desires"),("oren","home","entrusts"),("home","archive","stored_in"),("archive","transfer","obeys"),("transfer","cost","requires"),("father","home","would_consume"),("home","orange","contains"),("trust","mira","confronts"),("orange","mira","haunts")]
    p.graph.edges = [Edge(source=a,target=b,relation=r,status="canon") for a,b,r in links]
    p.graph.engine = "Illustrative story graph · original sample canon"
    annotate(p.graph)
    p.angles = [Angle(id="fiction1",title="The last keeper of borrowed mornings",thesis=p.brief.direction,hook="Mira knew the smell of every home in the city except the one she had left.",why="A private desire collides with an irreversible rule and another person's trust.",motif="character / consequence arc",node_ids=["mira","father","home","oren","cost","trust"],source_ids=["S1"],counterargument="Mira's grief makes a selfish choice emotionally intelligible without making it harmless.",questions=["What does Mira finally do, and what does it cost her?"],decision="Sample premise")]
    p.selected_angle = "fiction1"
    return p

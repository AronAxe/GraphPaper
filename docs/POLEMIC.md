# Polemic, argument and authorial intent

Use **Polemic** for an essay that argues a position: moral criticism, satire, cultural argument, an opinion piece or a sharply reasoned indictment. It is the fourth writing mode, alongside Nonfiction, Fiction and Science.

The mode does not choose an opinion for you. It develops yours. Factual precision remains necessary; automatic neutrality does not.

## Continue an existing project

You do **not** have to create a new project, re-upload your writing samples or rebuild the graph.

1. Open the project and click **Nonfiction · Change** (or the current mode name) near the top.
2. Select **Polemic** and apply the change.
3. Open **Creative brief**. Set your **Core thesis / position to preserve** and **Rhetorical force**. The thesis is optional: when blank, the writer follows your existing Direction field.
4. In **Angles**, click **Refresh angles with my voice**. This reuses the current graph and enabled voice samples. It does not run another graph extraction.

Sources, source IDs, graph, voice profile, draft, outline, previous angles and draft versions stay in the same project when you change its mode. Old generated angles are not silently rewritten by moving a slider. The interface marks angles or outlines made under an earlier brief/voice as out of date and offers an explicit refresh. Existing manually chosen work remains yours to retain or edit.

## Three different controls

**Writing purpose** determines the task. Polemic develops and defends the stated position. Ordinary Nonfiction now also supports **Develop and defend my position**, **Investigate an open question**, or **Follow the brief**. A question-led article need not conclude in the center either: its conclusion should follow its reasoning and evidence.

**Rhetorical force** controls delivery: understated, pointed or uncompromising. It does not increase factual certainty, mechanically add swear words, or replace your voice with a generic aggressive style.

**Evidence detail** controls how extensively the piece develops its factual basis and directly relevant limits. It is not a politeness, neutrality or permission-to-invent slider. Lower detail keeps the presentation lean; higher detail supports a fuller treatment without demanding a yes-but paragraph after every judgment.

A precise brief names the proposition, not only the tone. For example:

> Argue that the policy rewards appearances instead of results. Make the case through its incentives, its language and the experience of the people subjected to it. Preserve the satire and end with the judgment. Check factual claims, but do not turn the argument into an open question about whether criticism is permissible.

## What changed in 0.4

Previous versions supplied the author voice to drafting/revision but omitted it from angle generation, outline generation and the initial editorial review. At the same time, shared prompts repeatedly emphasized counterarguments and moderation-adjacent phrasing. Those two choices could select a neutralized thesis before the writer ever encountered the author's voice.

The editorial pipeline now receives a common **authorial contract** and the voice context at angle generation, JEV candidate evaluation, final angle scoring, outlining, drafting, review, revision and prose polishing. Voice samples remain stylistic evidence, not factual sources.

The angle stage generates different routes into the requested argument rather than different degrees of retreat from it. A counterargument is optional metadata and must be relevant; an empty field is better than a manufactured objection. Candidate scoring considers **stance fidelity** and **voice fidelity** alongside factual support and editorial potential. Without JEV, the same authorial contract still goes to the language model.

The critic distinguishes factual assertions, inferences, moral judgments, analogies, satire and deliberate hyperbole. A moral description of conduct is not automatically a clinical diagnosis. Conversely, an invented diagnosis or factual allegation is not excused by choosing Polemic. The editor should identify the actual problem and suggest a local repair, not replace the entire position with something milder.

## Avoiding repeated disclaimer openings

Short polemics and explicitly argument-led nonfiction with an approved outline of **up to 3,000 words** are drafted as one coherent piece. Section-by-section generation could repeatedly reopen the same uncertainty because every section saw the same cautionary instructions afresh.

Longer pieces retain section-wise drafting, with the same authorial contract and prior prose. Fiction keeps its scene/continuity workflow; Science keeps its scientific research workflow. The whole-piece writer still receives the approved outline and selected source passages and is followed by the usual evidence review.

## Voice and editing

Enabled current writing samples reach the angle stage even when a learned profile needs refreshing. A stale learned profile is not treated as current, and turning voice influence off is still respected. Voice learning now explicitly attends to rhetorical moves, willingness to conclude, analogy, comic timing, indignation and argument structure—not just sentence length and punctuation.

The review panel can report **authorial fidelity** separately from source support. It can flag an irrelevant caveat or a softened conclusion as editorial drift. Automatic revision acceptance is asked to preserve thesis, force and voice; a more moderate or polite result is not automatically a better result.

Humanize and Deslop follow the same intent. Their fidelity critic also sees the brief and voice. A changed stance counts as a meaning warning, and a candidate prepared under an earlier brief or voice cannot silently overwrite the current draft.

## Scope

This is an editorial-workflow change, not a switch that rewrites a provider's behavior or guarantees a particular style from every model. Inspect the proposed angles and choose your own when appropriate. The release includes wiring, preservation, UI and native regression tests plus separately labelled live Codex examples using original synthetic material. The fixtures are not a user's private articles and are not empirical findings about AI consciousness.

[Nonfiction workflow](NONFICTION.md) · [Author voice](VOICE-AND-PROSE.md) · [Graph and JEV](GRAPH-AND-JEV.md) · [Validation](QUALITY.md)

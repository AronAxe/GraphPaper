# GraphPaper 0.5.0 — reusable voice graphs and bounded JEV

- Fix oversized JEV requests with exact UTF-8 payload preflight, automatic question/candidate batching and compact voice-graph context. Raw voice-training articles are not sent to JEV. The existing 60 KB application budget is not simply raised.
- Save and name a voice once, then apply its compact graph in any project without another model call or re-uploading the articles. Legacy learned profiles can be saved without retraining.
- Separate voice training pieces from project evidence, with upload, pasted text and article-URL inputs in the voice library.
- Edit the mini graph's habits and weights, export/import it, and view a namespaced style/evidence overlay without modifying the research graph.
- Keep author control: power language is not filtered, and current project instructions override saved style habits. Applying or updating a voice does not choose the author's opinion.
- Preserve existing profiles, source documents, graphs, settings and manuscripts. Failed/oversized optional decisions cannot destroy completed writing or fabricate a passing score.

Download the Windows ZIP, extract it fully, and run `GraphPaper.exe` with `_internal` alongside it. The package is unsigned and retains the public Graphify runtime, Codex OAuth, reasoning controls, Polemic and Science/APA features.

For an existing voice, open **Your writing voice → Save as reusable voice**. In another project, open **My voices → Use in this project**. The [voice-graph guide](https://github.com/AronAxe/GraphPaper/blob/main/docs/VOICE-GRAPHS.md) explains the graph editor, training library, overlay, precedence and request sizing.

Development, regression testing and Windows packaging for this update run on GitHub-hosted runners—not the user's computer. The release workflow and attached reports record the actual completed checks. Synthetic provider responses test routing and size handling; they are not a claim of live JEV quality evaluation.

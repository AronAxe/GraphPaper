# Graph exploration, Graphify and JEV

The graph is an inspectable map of ideas and possible relationships. It helps discover a direction for writing; it does not replace reading the sources or establish causality by itself.

## Build or import

**Native extraction** works without installing Graphify. It reads enabled non-voice sources in bounded chunks and attaches exact source quotations where possible. Unchanged extraction inputs are cached. A failed or budget-limited extraction does not install a half-complete graph as though it covered the entire library.

**Import graph** accepts Graphify/NetworkX-style node-link JSON with `nodes` and either `edges` or `links`. Imported relationships remain unverified. External confidence values are not promoted to evidence.

**Graphify (external process)** uses the public Graphify 0.9.80 runtime included with the Windows release. It builds the graph separately, while GraphPaper supplies your selected extraction model and reasoning setting, including Codex OAuth, and accounts for the requests. No second Native pass runs. Leave the custom executable path blank for the bundled runtime. [Setup and public dependency strategy](UPDATE-0.3.1.md)

## Read the status, not only the picture

| Status | Interpret it as |
|---|---|
| **Sourced** | A relationship or concept with a matching source anchor; not necessarily an established fact |
| **Inferred** | An interpretation without verified direct support |
| **Canon** | A relationship associated with supplied fictional canon |
| **Proposed** | A possibility to develop or examine |
| **Imported** | External graph content that has not been verified against this project’s sources |

External Graphify nodes also retain source-file links. These pointers support retrieval for angle evaluation without pretending the file proves a relationship. Quoted text is checked for occurrence in the imported source. It can still be misleading, disputed or insufficient to support the claim. Read the surrounding passage.

## Navigate and guide discovery

Select nodes or relationships to inspect descriptions and evidence, or edit their wording. In 3D, drag the background to orbit, Shift-drag to pan, and scroll to zoom; 2D gives a flat pannable view. Search the whole graph by titles, notes or relationship names. **Focus here**, type filters and connection filters reduce clutter. [Full graph controls, editing and undo](GRAPH-STUDIO.md).

**Pin** concepts to emphasize them. **Exclude** distractions from candidate discovery. Edit the direction and the exploration/evidence-discipline settings beside the graph. These controls influence exploration; they do not permit unsupported reasoning.

**Find a path** highlights an undirected conceptual connection between two nodes. The highlighted sequence is not a causal proof. A graph can connect two concepts through a vague intermediate node while contributing little to a defensible article.

The default overview displays 60 nodes; **Show** offers 40, 60, 100 or 180. At most 360 links are drawn. These are view limits: the complete stored graph remains available to search and downstream work. Imports are bounded to 5,000 nodes and 20,000 edges. The footer reports displayed versus stored data.

## How angles are discovered

The pipeline searches bounded graph motifs: relationships, contradictions/conflicts, divergence, convergence, cross-community bridges and directed chains. Fiction also uses character/consequence structures. It preserves diversity across motif families instead of picking only the most connected node.

Candidate structures become competing theses or premises. Each angle can retain its graph nodes, source IDs, counterargument and unresolved questions. You select the direction; the app does not automatically publish the highest-scored candidate.

## What JEV contributes

JEV supplies typed model judgments at several points:

- Candidate value, fit, grounding and risk of a spurious connection.
- Editorial potential, evidence gaps and questions tailored to an angle.
- Recommendations to research, revise or move to author review.
- Acceptance checks for a bounded automatic revision.

This is more than a score attached to a finished article. It helps decide which structures deserve expensive writing or editorial attention. However, the values are model judgments, not calibrated probabilities that a scientific claim is true.

With JEV off, structural exploration still works and results are not given fabricated scores. With the optional automatic refinement enabled, an unconfirmed revision can be retained as a candidate version rather than replacing the original. A recommendation to research is a workflow signal; in ordinary nonfiction it does not mean a web search has secretly run.

## Request sizing and voice context

JEV receives compact style-graph context and relevant decision material, not raw voice-training articles. The complete serialized UTF-8 envelope is checked before sending; candidates and questions are automatically batched while preserving their IDs. The 60 KB limit is an application transport budget, not a general JEV capability limit. An indivisible oversized optional decision stays explicitly unscored; it does not abort completed writing or approve a revision by default. [Details](VOICE-GRAPHS.md#why-jev-no-longer-receives-the-whole-heap).

## When to rebuild

After adding, changing, excluding or reclassifying sources, rebuild before relying on graph coverage. Scientific screening can change the enabled evidence set as well. Inspect important connections again when their underlying material changes.

A stronger graph is useful only if it leads to a better argument or story. The [quality protocol](QUALITY.md) separates that editorial question from the fact that the software tests passed.

## Argument-led angle discovery

Polemic generates alternative routes into your thesis, not alternative opinions on whether you may hold it. JEV receives compact author-voice context and the editorial contract and scores stance/voice fidelity explicitly. Counterarguments are optional and must be directly consequential. Brief or voice changes mark old angles as stale; refresh them without re-running Graphify. [Authorial-intent controls](POLEMIC.md).

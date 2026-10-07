# Graph exploration, Graphify and JEV

The graph is an inspectable map of ideas and possible relationships. It helps discover a direction for writing; it does not replace reading the sources or establish causality by itself.

## Build or import

**Native extraction** works without installing Graphify. It reads enabled non-voice sources in bounded chunks and attaches exact source quotations where possible. Unchanged extraction inputs are cached. A failed or budget-limited extraction does not install a half-complete graph as though it covered the entire library.

**Import graph** accepts Graphify/NetworkX-style node-link JSON with `nodes` and either `edges` or `links`. Imported relationships remain unverified. External confidence values are not promoted to evidence.

**Graphify CLI** is optional for an existing trusted installation. It runs separately, with its own model requests, and native extraction adds source checking. It is not bundled with the Windows release. [Technical integration details →](INTEGRATIONS.md#graphify)

## Read the status, not only the picture

| Status | Interpret it as |
|---|---|
| **Sourced** | A relationship or concept with a matching source anchor; not necessarily an established fact |
| **Inferred** | An interpretation without verified direct support |
| **Canon** | A relationship associated with supplied fictional canon |
| **Proposed** | A possibility to develop or examine |
| **Imported** | External graph content that has not been verified against this project’s sources |

Quoted text is checked for occurrence in the imported source. It can still be misleading, disputed or insufficient to support the claim. Read the surrounding passage.

## Navigate and guide discovery

Select nodes or relationships to inspect descriptions and evidence. Drag nodes, pan, zoom or fit the view. Search by label to find relevant concepts in a large graph.

**Pin** concepts to emphasize them. **Exclude** distractions from candidate discovery. Edit the direction and the exploration/evidence-discipline settings beside the graph. These controls influence exploration; they do not permit unsupported reasoning.

**Find a path** highlights an undirected conceptual connection between two nodes. The highlighted sequence is not a causal proof. A graph can connect two concepts through a vague intermediate node while contributing little to a defensible article.

For responsiveness, the view displays at most 180 nodes at a time; the complete graph remains in the project. Imports are bounded to 5,000 nodes and 20,000 edges. The interface shows when it is displaying only part of a large graph.

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

## When to rebuild

After adding, changing, excluding or reclassifying sources, rebuild before relying on graph coverage. Scientific screening can change the enabled evidence set as well. Inspect important connections again when their underlying material changes.

A stronger graph is useful only if it leads to a better argument or story. The [quality protocol](QUALITY.md) separates that editorial question from the fact that the software tests passed.

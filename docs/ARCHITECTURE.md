# Architecture

GraphPaper is an independent implementation. It does not vendor another writer or pretend a knowledge graph is proof. The native backend is deliberately usable without a large graph database or a separate frontend toolchain.

## Process layout

`GraphPaper.pyw` provides first-run GUI setup. `graphpaper.desktop` starts FastAPI/Uvicorn on a held, randomly assigned **127.0.0.1** socket and opens a pywebview window. On Windows the selected renderer is Edge WebView2. The interface is local HTML, CSS and JavaScript; no CDN or remote fonts are required.

SQLite/WAL stores project JSON, extraction cache and draft revisions. Pydantic rejects unknown model fields and non-finite typed numeric values. Optimistic version checks preserve concurrent edits. A small, explicit JS bridge exposes export dialogs and a save-before-close handshake, not arbitrary filesystem access or shell execution. The close handshake uses `run_js`, not CSP-incompatible `evaluate_js`.

## Domain data

Sources have stable IDs, content digests, enabled flags and roles: evidence, canon, inspiration, voice. A source passage is stored with exact character positions. Source-role separation prevents a voice example from becoming factual support.

Nodes are claims, concepts, people, events, characters, places, themes or rules. Edges have typed relationships and source quote anchors. Their status is sourced, inferred,canon, proposed or imported. Exact quote verification is deterministic; whether the quote supports a claim remains a separate editorial judgment.

Angles contain a thesis/hook, a discovered motif, node/edge/source IDs, evidence questions, counterargument and labelled JEV evaluations. Outlines carry section/scene purposes, beats, sources and word allocations. Drafts, reviews, continuity ledgers and earlier versions are distinct objects.

## Pipeline

1. **Ingest.** Extract text with bounded file size/decompression, preserve paragraph/page ordering where supported, and warn about missing visual or revision content. URLs are fetched explicitly with public-address checks and redirect revalidation.
2. **Extract.** Process every planned source chunk or fail without installing a partial graph. Cache unchanged extraction inputs. Extract exact evidence separately from possible conceptual links. Canonical labels merge native nodes across sources.
3. **Discover.** Mine bounded relationship, contradiction/conflict, divergence, convergence, cross-community bridge and directed-chain motifs. Pin/exclude choices and explicit direction influence the shortlist. Diversity is preserved across motif families.
4. **Evaluate.** Batch candidates through typed JEV questions. Use separate judgments for value, fit, support and spuriousness. Then ask the writing model for genuinely different candidate theses rather than blindly writing the structurally highest-ranked path. JEV scores and evidence-gap signals remain inspectable.
5. **Choose.** Human approval is mandatory for an angle. An author can edit it or supply their own. Do not manufacture support for an author-preferred conclusion.
6. **Outline.** Build an editable structure with a normalized word budget. Nonfiction requires an argument; fiction requires consequential scenes, not headings masquerading as a story.
7. **Draft.** Use section-aware source retrieval, graph-linked passages, brief, voice references and prior prose. For fiction, carry a compact continuity ledger across scenes. Save checkpoints while a long job runs.
8. **Review.** A separately configurable editor checks substance and craft. Nonfiction also audits reference IDs and samples up to 12 substantive claims with exact quote verification. JEV can recommend research, revision or author review.
9. **Refine.** At most one automatic improvement pass per draft job, when enabled. Preserve both candidates; an explicit JEV preference and citation integrity gate control automatic replacement. Further revisions are user-triggered.

JEV's `research` recommendation is a visible workflow signal, **not a claim that autonomous web research ran**. The author can import additional sources and repeat the relevant stage.

## Modules

| Module | Responsibility |
|---|---|
| `models.py` | Typed project and settings contracts |
| `storage.py` / `secrets.py` | SQLite, revisions, cache; DPAPI or OS keyring/session keys |
| `ingest.py` | Files, public URL retrieval, chunking and content digests |
| `graph.py` / `graphify_adapter.py` | Extraction normalization, graphs, motifs, optional real Graphify subprocess |
| `providers.py` | OpenRouter, OpenAI-compatible, Anthropic and JEV requests; retries and usage |
| `support.py` | Source-reference and sampled-claim support checks |
| `pipeline.py` | Jobs, stage contracts, source selection, writer/editor/JEV orchestration |
| `export.py` | Markdown, DOCX, safe HTML, graph/project JSON |
| `server.py` / `desktop.py` | Local API security and native desktop shell |
| `ui/` | Graph, source library, angle cards, outline, editor, settings and version UI |

## Deliberate constraints

Graph view renders at most 180 nodes at once for responsiveness; the full graph stays in the project. Imports are capped at 5,000 nodes/20,000 edges; native motif candidate expansion is bounded. Native extraction permits up to 350 planned chunks; the job request budget can stop a large corpus before completion, preserving its previous state and cached chunks.

Source retrieval is relevance/anchor-based and bounded, not a promise to send the entire corpus into every model call. Coverage is available in the pipeline context. The context guard is character-based, not an exact tokenizer for every arbitrary model.

Graphify imports preserve external IDs. Augmenting native extraction can leave similar labels as separate nodes; there is no unsafe automatic entity-equivalence proof. Graphify CLI work has separate costs and an explicitly bounded timeout.

The application does not learn a globally calibrated model of the author's preferences. Saved choices/directions are explicit controls. Persistent learned preference calibration and blind writing-quality benchmarks remain future work, not hidden implemented features.

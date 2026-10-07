# Architecture

GraphPaper is a local-first desktop application with an inspectable source/evidence model. It is an independent implementation; it does not vendor a complete writing agent and relabel it.

## Runtime structure

```text
Windows desktop window (pywebview / Edge WebView2)
                |
          local HTML/CSS/JS
                |
  session-protected loopback API (FastAPI / Uvicorn)
                |
   project store + bounded job runner + provider clients
       |                |                    |
   SQLite / folders   writing pipeline   Codex / APIs / JEV
                           |
                    Science adapters
               PubMed / S2 / arXiv / Crossref / Europe PMC
```

The desktop process holds an ephemeral loopback socket before handing it to Uvicorn. The UI is bundled; there is no frontend CDN dependency. The native bridge exposes only readiness, export and close-handshake methods, keeping native Windows objects private. A close request returns immediately to the UI thread while a worker asks the editor to finish saving.

## Domain model

**Project:** stable ID, mode, brief, sources, graph, angles, selected direction, outline, draft, reviews, history-related state, usage and optional research workspace.

**Source:** stable source ID, text, content digest, role, enabled state, URL/author metadata and ingestion warnings. Science can attach structured bibliographic metadata.

**Graph:** typed nodes and relationships, status, evidence quotations, exact-match offsets, communities and extraction coverage. Attribution and truth are separate concepts.

**Angle:** thesis/premise, hook, discovered motif, nodes/edges/sources, objections, research questions and optional JEV judgments.

**Research workspace:** protocol, provider records, search logs, screening decisions, appraisal and source hashes, abstract/keywords and manuscript-specific author confirmations.

Pydantic validates structured state. SQLite/WAL stores project snapshots, revisions and cache; optimistic version checks prevent a stale result from quietly replacing newer edits. Project folders supplement the database rather than replacing it.

## Writing pipeline

1. Ingest source text with explicit roles and warnings.
2. Extract/cache graph chunks and verify quoted substrings.
3. Mine bounded graph motifs, preserving structural diversity.
4. Optionally use JEV to judge candidates and decide where further reasoning is useful.
5. Let the author select or replace the proposed angle.
6. Build an editable outline, then draft sequential sections/scenes with relevant passages.
7. Review substance and craft, with source support for nonfiction/science and a continuity ledger for fiction.
8. Save checkpoints and keep revision proposals recoverable.

The optional automatic revision is bounded, not an open-ended agent loop. JEV judgments inform control and acceptance but are not empirical truth probabilities.

## Science extension

`scholarly.py` calls external metadata services with bounded retrieval, rate spacing, explicit failures and provenance. Screening converts included records into project evidence sources. Full-text retrieval and uploaded-paper attachment retain content scope and source identity.

`science.py` coordinates query planning, retrieval, appraisal, scientific outline, drafting and checks. A planned query is not a completed search. The actual log constrains method reporting. Empirical mode requires author-supplied completed results. Search limits remain visible, especially for systematic/scoping claims.

`apa.py` resolves internal source IDs against metadata; `science_export.py` constructs the manuscript and research package. Submission confirmations are tied to the current manuscript/research state, not a permanent project-wide approval flag.

## Module map

| Module | Responsibility |
|---|---|
| [models.py](../graphpaper/models.py), [science_models.py](../graphpaper/science_models.py) | Project/settings and research contracts |
| [storage.py](../graphpaper/storage.py), [folders.py](../graphpaper/folders.py), [secrets.py](../graphpaper/secrets.py) | Database, file workspaces and credentials |
| [ingest.py](../graphpaper/ingest.py), [author_web.py](../graphpaper/author_web.py) | Source import and selected author-site discovery |
| [graph.py](../graphpaper/graph.py), [graphify_adapter.py](../graphpaper/graphify_adapter.py) | Graph extraction, normalization, motifs and optional Graphify |
| [providers.py](../graphpaper/providers.py), [reasoning.py](../graphpaper/reasoning.py), [codex.py](../graphpaper/codex.py) | Model requests, effort capabilities and Codex authentication/runtime |
| [pipeline.py](../graphpaper/pipeline.py), [support.py](../graphpaper/support.py) | Jobs, context selection, writing/review and source checks |
| [voice.py](../graphpaper/voice.py), [polish.py](../graphpaper/polish.py) | Style profiles and protected prose proposals |
| [scholarly.py](../graphpaper/scholarly.py), [science.py](../graphpaper/science.py) | Live literature adapters and scientific work |
| [apa.py](../graphpaper/apa.py), [science_export.py](../graphpaper/science_export.py), [export.py](../graphpaper/export.py) | Citations, manuscripts and exchange formats |
| [server.py](../graphpaper/server.py), [studio_routes.py](../graphpaper/studio_routes.py), [science_routes.py](../graphpaper/science_routes.py) | Local API and mode-specific endpoints |
| [desktop.py](../graphpaper/desktop.py), [ui/](../ui/) | Native shell and interactive workspaces |

## Boundaries that matter

Graph view limits are distinct from stored-graph size. Character budgets are not exact tokenizer counts for every model. Source packs contain selected passages rather than a promise that every request sees the entire library. A voice profile is source-informed prompting, not fine-tuning.

Graphify is an optional graph engine with a bundled public runtime in Windows releases. Its external worker calls a job-scoped loopback gateway; GraphPaper routes the selected extraction provider/model/effort and records the usage. There is no duplicate Native pass. Scholarly records, preprints and abstract-only sources are not automatically validated science. Citation matching samples support; it cannot prove every inference.

The application is not currently documented as a multi-user server, an MCP service or an installed agent plugin. Future integrations should preserve explicit project permission and avoid exposing credentials. [Development](DEVELOPMENT.md) and [Security](SECURITY.md) describe the corresponding checks.

## External Graphify runtime boundary

`graphify_worker.py` hosts the unmodified pinned public CLI in a separate process. `graphify_gateway.py` implements its authenticated, text-only loopback completion endpoint. `graphify_runtime.py` probes availability and prepares an isolated environment; `graphify_process.py` manages owned process lifetimes. The adapter validates the complete graph before the existing optimistic project save. File provenance remains a retrieval pointer, not a truth status. [Protocol and distribution](UPDATE-0.3.1.md).

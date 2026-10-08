# Changelog

## 0.5.0

- Bound and automatically batch JEV requests by actual serialized UTF-8 size; remove voice-training prose from decision payloads.
- Add named, reusable voice graphs with independent training, graph editing, import/export and explicit application across projects.
- Compose namespaced style/evidence overlays without altering the research graph; current author instructions override saved style preferences.
- Keep unrepresentable optional decisions honestly unscored instead of aborting completed writing.
- Implement and validate the update using GitHub-hosted runners only.


## 0.4.0

- Add Polemic and a reversible writing-mode switch for existing projects.
- Separate thesis, writing purpose, rhetorical force and evidence detail; remove unconditional neutrality/counterargument pressure.
- Supply author voice and intention to angle selection, JEV scoring, outlining, review, revision and prose polishing.
- Draft short argumentative pieces as coherent wholes rather than restarting the same disclaimers for each section.
- Track stale angle/outline/review context; refresh angles without rebuilding the graph; flag stance drift as a meaning change.
- Preserve source checks, native Windows fixes, Graphify/Codex, Science/APA, project folders and existing manuscripts.


## 0.3.1

- Repair external Graphify extraction with the configured provider, including official Codex OAuth and extraction-role reasoning.
- Bundle pinned public Graphify 0.9.80, SDKs, metadata, tokenizer cache and licences in Windows builds; publish explicit source requirements.
- Route job-scoped inference through an authenticated loopback adapter, with shared accounting, no API fallback and no duplicate Native extraction.
- Preserve source-file provenance into graph inspection and angle retrieval; reject malformed/partial graph results.
- Add runtime diagnostics, deadline/cancellation coverage, compatibility tests, actual external-worker tests and compiled-native release gates.


## 0.3.0

- Provider-native, model-aware reasoning effort for writer/editor/extraction roles, with Codex catalog support and explicit thinking budgets.
- Third Science workspace with real scholarly database searches, documented screening, open full text, evidence appraisal and scientific drafting.
- APA 7 professional manuscripts, metadata-based references, research-package export and manuscript-specific author confirmation.
- Retained the 0.2.1 private native bridge and nonblocking save-on-close fix; added native Science regression coverage.
- Rendered export inspection fixed empty-page overflow and inherited heading-theme fonts.


## 0.2.1 ? 2026-10-06

- Fix recursive native-window exposure in the JavaScript bridge.
- Fix native close/save deadlock without discarding pending edits.
- Add real Windows mouse, bridge, dialog and save-on-close regression tests for the compiled release.

## 0.2.0 — 2026-10-05

- Learn and edit an author voice from uploaded writing or selected article URLs.
- Separate project folders, stable-file automatic Inbox imports, role subfolders and original uploads.
- Local prose inspection, humanizer/deslopping proposals, protected factual spans and explicit accept/reject with version history.
- Official Codex browser OAuth and subscription-based writing, with an isolated account directory and bundled Windows runtime.
- Dedicated new workflow, API, subprocess and browser tests; versioned Windows release packaging with SHA-256 provenance.


## 0.1.0 — 2026-10-05

Initial GraphPaper writing studio:

- Native Windows-oriented desktop shell, graphical source-edition setup, dark/light interface and responsive browser layout.
- Document/text/URL import, explicit evidence/canon/inspiration/voice roles, cached quote-anchored extraction and Graphify JSON/optional CLI integration.
- Interactive graph, path inspection, pin/exclude controls and typed motif-based angle discovery.
- OpenRouter-preferred JEV, direct TypeSafe route, explicit choices, evidence-gap signals and bounded revision gate.
- Independent nonfiction and fiction generation; editable outlines; scene-level continuity ledger.
- Local autosave, optimistic concurrency, draft checkpoints, versions, reviews and Word/Markdown/HTML/JSON export.
- Secure key storage, cloud opt-in, local API protections, provider request accounting and cancellation.
- Initial local validation: 86 passing unit/integration tests, 17 passing browser workflow checks and a loopback asset self-test. Live providers and interactive native Windows UI require separate validation.
- Windows CI/package workflows and an optional separate graphical branch publisher.

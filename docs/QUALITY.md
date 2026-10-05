# Quality, tests and known limits

## Version 0.2 validation update

The 0.2 update was tested on a native Windows 11 machine with an isolated Python 3.13 environment: **120 automated tests passed**, with one symlink-permission test skipped; **all 26 real-HTTP browser workflow checks passed** with zero JavaScript page errors. The official bundled **Codex CLI 0.160.1** passed its signed-out app-server handshake and required-command checks. These are local Windows results, not GitHub-hosted CI results; the hosted runner remained queued and that run was cancelled. Reports are in [validation/v0.2](validation/v0.2/) (or the corresponding directory from this documentation page).

A real user OAuth completion, paid model calls, output-quality comparisons and hands-on native-window dialog interaction are not claimed as tested. Historical 0.1 results below remain a record of that earlier build.

## Initial local validation

Validation date: **5 October 2026**. Initial build environment: **Linux, Python 3.13**, system Chromium. Subsequent GitHub Actions results are separate and visible in the repository's Actions tab.

| Check | Initial result | Scope |
|---|---|---|
| Automated pytest suite | **86 passed, 1 skipped** | Storage/CAS, ingestion, graphs, provider contracts, JEV routing, Origin checks, source support, pipelines, cancellation, exports, desktop close bridge and publisher manifest validation |
| Graphical workflow tests | **17 passed, zero page errors** | Actual interface, real FastAPI routes/store and deterministic model doubles |
| Loopback service self-test | **Passed** | Health, index and bundled JS/CSS served over local HTTP |
| Native Windows DPAPI | **Skipped locally** | Windows-only test included in CI matrix |
| Native WebView2 and frozen Windows application | **Not run locally** | Check actual Windows CI results separately; a packaged backend self-test does not certify interactive WebView2 behaviour |
| Live writing/JEV providers | **Not run** | Controlled HTTP mock responses; no live keys |
| Live external Graphify CLI | **Not run** | Optional adapter; not installed in the build environment |
| GitHub push from GUI publisher | **Not run** | Manifest/path controls tested; the repository upload uses the authorized connector instead |

The managed browser in the initial environment blocked URL navigation, including loopback. Initial browser checks used Playwright set_content with the actual interface scripts and an in-process bridge to FastAPI's TestClient. No browser policy was disabled. The normal HTTP version of the same workflow script is used by GitHub CI. File-input upload is exercised through Playwright; a native Windows OS file dialog is a separate check.

Reports are in [validation](validation/). CI refreshes these reports when validating the repository import. Screenshots are actual interface renders of original illustrative material, not a mockup of unimplemented screens. AI responses inside the test harness are controlled fixtures, not evidence of writing quality.

## The 17 interface checks

Welcome; illustrative graph; node inspection and pinning; path highlighting; angle edit/selection; outline edit/reordering; manuscript autosave/preview; source references; version restore; export controls/valid Word bytes; provider settings; browser file-input import; full nonfiction pipeline; explicit revision; fiction scenes/ledger; light theme; responsive 390-pixel layout.

## Evidence safeguards

Exact quote matching, role separation and source references help prevent fabrication. They do not establish source truth, detect every distorted paraphrase or prove logical entailment. The critic samples up to 12 important claims; it is not an exhaustive legal, scientific or factual audit. Imported graphs are hypotheses until anchored. Images, scanned PDF content, DOCX comments and tracked-revision metadata are not silently interpreted as complete source text.

Fiction canon is author-supplied. The generated continuity ledger is useful context, not an infallible record. Whole-draft revisions and manual edits can make it stale; check it against the latest prose.

## Cost and recovery

Request budgets count GraphPaper's own calls and bounded retries, not external Graphify subprocess usage. Real provider-reported cost is recorded when supplied; unknown cost stays unknown. Jobs can be cancelled, but an in-flight request may still incur a charge. Long drafting jobs save intermediate versions. Exceeding context/output constraints fails explicitly instead of overwriting with a truncated manuscript.

Extraction may require many calls on a large manuscript. Start with a small real project, inspect the extracted graph and provider receipts, then set budgets deliberately. Automatic revision is bounded to one pass; the app is not an open-ended self-improvement loop.

## How to test the actual writing advantage

No claim is made that this system already produces better prose than every direct prompt. Evaluate it against a serious baseline with the same models, sources, word targets and comparable inference budget.

For nonfiction, blind-rate factual support, reasoning, novelty, organization, voice and reader usefulness. Count unsupported claims and misleading citations separately from subjective quality. For fiction, blind-rate motivation, continuity, scene causality, prose, emotional progression and originality. Record the author's edit time, not just the model's self-score.

Compare direct prompt, outline-and-review baseline, GraphPaper without JEV, and GraphPaper with JEV. Separate one-source articles from larger corpora. A graph that yields attractive but spurious connections should score worse, not better. Do not train and evaluate angle selection on the same author-rated examples.

The practical quality goal is a better final article or story with less author correction, not the largest graph, most agents or highest self-awarded score.

## Known release limitations

The source launcher and visual native shell need a real Windows interactive validation pass. No signed installer is included. Provider endpoint/model availability can change. Citation support is sampled. There is no automatic paywall bypass, OCR, live-web fact verification, trained author-preference model, cloud-sync collaboration or full WYSIWYG editor. HTML/Word typography should still be checked for a publisher's specific template.

Large graphs are visually capped while the full project remains stored. Graphify IDs and native canonical IDs may leave duplicate conceptual labels after augmentation. Direction and pins influence candidate exploration but do not guarantee every requested connection is defensible.

The compiled Windows executable passed its startup, local backend and bundled-interface self-test. The versioned Windows ZIP includes the official Codex runtime and its verified provenance. This check does not complete a real account OAuth login or make a live model request.

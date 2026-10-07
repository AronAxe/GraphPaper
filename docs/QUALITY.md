# Validation and quality

Passing software tests and producing a better article are different questions. This page keeps recorded release checks, live service checks and editorial evaluation separate.

## Recorded validation: GraphPaper 0.3.0

The [release summary](validation/v0.3.0/summary.json) records native Windows validation for the published 0.3.0 build. These are **recorded local-build results**, not a claim that every current GitHub Actions run passed.

| Check | Recorded result | Evidence |
|---|---|---|
| Automated Windows tests | 172 passed, 1 symlink-permission skip, 0 failures | [JUnit report](validation/v0.3.0/windows.xml) |
| Base browser workflow | 17 checks passed | [Report](validation/v0.3.0/browser-base.json) |
| Voice/folder/prose browser workflow | 9 checks passed | [Report](validation/v0.3.0/browser-studio.json) |
| Science/reasoning browser workflow | 13 checks passed | [Report](validation/v0.3.0/browser-science.json) |
| Native Windows source interface | 10 checks passed | [Report](validation/v0.3.0/native-source.json) |
| Actual compiled Windows interface | 10 checks passed | [Report](validation/v0.3.0/native-package.json) |
| Compiled backend/assets | Passed | [Report](validation/v0.3.0/package.json) |
| APA export rendering | Four synthetic manuscript pages visually inspected | [Scope](validation/v0.3.0/apa-render.json) |

The 39 browser checks reported no JavaScript page errors. The compiled native test exercises a Windows mouse interaction, bridge initialization, Science protocol editing, Connections, native Save As and persistence of a pending edit before normal process exit. It is not merely a request to a health endpoint.

## Live versus controlled tests

Browser/model fixtures are synthetic and labelled. They verify workflow behavior, not prose quality or scientific findings. The release checks did not complete a real user OAuth ceremony or make paid writing/JEV requests.

The [separate live metadata check](validation/v0.3.0/scholarly-live.json) succeeded for PubMed, arXiv, Crossref and Europe PMC. Anonymous Semantic Scholar returned HTTP 429; the failure was recorded rather than turned into zero results. This is a dated connectivity check, not a guarantee of current availability.

The bundled official Codex runtime received a signed-out protocol check. External Graphify execution was not exercised by a live run in the recorded release validation. Mock contract tests cannot establish continued availability of an external endpoint.

APA rendering used the same exporter source with synthetic material in LibreOffice on Linux, not Microsoft Word automation. Visual checks found and corrected blank-page and inherited-font issues. The final manuscript still needs inspection under the target journal’s requirements.

## Current CI status

The README’s quality badge is dynamic and links to the actual [quality workflow](https://github.com/AronAxe/GraphPaper/actions/workflows/quality.yml). It should not be replaced with a static “passing” label. A queued, skipped or failed hosted run is distinct from the recorded release results above.

The [Windows release workflow](../.github/workflows/windows.yml) requires the compiled native regression before artifact publication. Later CI rebuilds are not allowed to silently replace an existing verified release package. Checksums identify exact assets, not a general claim that all builds are identical.

## Evaluate the writing advantage

Compare GraphPaper with a strong direct-writing baseline using the same sources, models, target length and a comparable inference budget. Blind the evaluator to the generation route where practical.

For nonfiction, assess source support, reasoning, useful novelty, counterarguments, structure and author editing time. Count unsupported claims and misleading citations separately from style preferences.

For fiction, assess motivation, agency, canon consistency, scene causality, emotional progression, prose and the ending. Do not reward more generated explanation when it makes the story worse.

For Science, check search completeness claims, actual source access, screening decisions, reported study details, interpretation and references. A model-generated appraisal is not a validated bias assessment or meta-analysis.

Compare direct prompt, outline/review baseline, graph workflow without JEV and graph workflow with JEV. Keep one-source and large-corpus tasks separate. Avoid training a preference model and evaluating it on the same rated examples.

## Known limits

Source quotation matching does not prove truth or entailment. Claim review samples important statements rather than exhaustively certifying the manuscript. Graphs can contain plausible but spurious links. Fiction ledgers can become stale after revisions. Science searches are bounded; metadata and abstracts do not count as full-text appraisal.

There is no measured claim that GraphPaper outperforms every direct prompt, no trained global model of an author’s taste, no automatic journal approval and no guarantee that a protected prose edit preserves every nuance.

## Historical builds

Earlier results and bug reports remain in the [validation directory](validation/) and versioned release notes. The 0.2.0 native freeze exposed a gap in browser-only/startup testing; [0.2.1](RELEASE-0.2.1.md) added genuine native-window regression coverage. Historical limitations should not be mistaken for the status of a later tested build.

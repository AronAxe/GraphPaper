# GraphPaper 0.3.0 - Science mode and reasoning depth

## New

- **Three modes:** Nonfiction, Fiction and Science, with a separate research desk for scientific work.
- **Per-role reasoning:** independently select writer, editor and extraction/research effort. Codex options come from the runtime's model catalog, including extended levels only when advertised. OpenRouter, OpenAI-compatible and Anthropic routes use their native fields. Explicit thinking budgets and configurable request timeouts are supported where appropriate.
- **Live scholarly search:** PubMed, Semantic Scholar, arXiv, Crossref and Europe PMC, with query logs, timestamps, caps, duplicate merging and explicit partial failures. Optional NCBI/Semantic Scholar keys are stored securely.
- **Evidence workflow:** include/exclude decisions, exclusion reasons, open full text or uploaded-paper attachment, study appraisal, exact source quotations, design/limitations and an evidence matrix.
- **Scientific manuscripts:** editable question/protocol, IMRaD-style outlines, evidence-led drafting, abstract, keywords, author declarations and source-support review. Empirical mode requires the author's actual completed results; it does not invent experiments or analyses.
- **APA 7 Word export:** professional title/author-note page, abstract, consistent typography, running head and page numbers, author-year citations and hanging references generated from metadata. A research package adds BibTeX, RIS, the evidence CSV, protocol and search log.
- **Submission checks:** unresolved blockers and author confirmations are visible. Changes invalidate prior approval. The checklist is not a claim of journal acceptance or ethics approval.

The author-voice, project-folder, humanizer/deslop and Codex OAuth features remain available. The Windows bridge freeze and save-on-close fixes are retained.

## Install

Download **GraphPaper-v0.3.0-Windows-x64.zip**, extract the whole folder into a new location, and run **GraphPaper.exe**. Keep `_internal` with the executable. No Python installation or terminal workflow is required. Existing projects and credentials use the same local data directory. The binary is unsigned.

Use **Connections -> Load available models -> Reasoning depth** to choose effort levels. Create a **Science** project and open its **Research protocol** to begin scholarly work.

## Scope

Database search is real network retrieval, not simulated research. Searches are bounded and never presented as exhaustive when capped. Abstracts/preprints are labelled. Systematic/scoping review completeness checks are stricter. The author must verify original sources, specialized references and the target journal's reporting requirements. Live metadata checks are separate from controlled model tests; no real user OAuth sign-in or paid writing-model call is claimed as part of release validation.

Detailed instructions: [UPDATE-0.3.md](https://github.com/AronAxe/GraphPaper/blob/main/docs/UPDATE-0.3.md). Validation reports are under `docs/validation/v0.3.0`. SHA256SUMS.txt identifies the exact downloadable archive.

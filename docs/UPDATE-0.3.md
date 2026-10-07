# GraphPaper 0.3 - reasoning controls and scientific research

GraphPaper now has three distinct workspaces: **Nonfiction, Fiction and Science**. Existing projects, author voices, project folders, prose-editing tools and Codex sign-in are retained. The native Windows bridge and save-before-close fixes from 0.2.1 are retained as well.

## Model-specific reasoning

Open **Connections & settings**, choose the provider and models, then **Load available models**. The **Reasoning depth** section has independent controls for the writer, editor and extraction/research model.

**Provider default** sends no override. Codex model discovery reads the runtime's `supportedReasoningEfforts`, `defaultReasoningEffort` and default-model flag. Options such as `xhigh`, `max` or `ultra` appear when that model actually advertises them; unsupported settings are rejected before a model call rather than silently changed. The exact selected effort is passed to Codex and recorded with its usage receipt.

OpenRouter uses its `reasoning.effort` field and requires routing support for the supplied parameters. OpenAI-compatible APIs use `reasoning_effort`. Direct Anthropic uses advertised effort capabilities and `output_config.effort`; adaptive thinking is enabled when supported. Models using explicit thinking-token budgets can expose a Budget option. A budget must leave room inside the total output-token limit.

Some API model catalogs expose only the presence of reasoning support, not a model-specific list. Those controls explicitly label the provider vocabulary as unverified for that model. The provider can reject an unsupported combination; GraphPaper does not quietly substitute a different level. Refresh capabilities when changing model or provider.

The request timeout is configurable. Higher effort can consume more time and tokens; it is not a requested article length. Codex continues to use its subscription/account allowance, with no hidden API-key fallback. JEV remains separately connected and does not inherit a language model's reasoning setting.

## The Science research desk

Choose **Science** when creating a project. The research desk keeps the question, search protocol, papers, screening decisions, evidence matrix and manuscript together.

A typical workflow:

1. **Research protocol:** define the question, manuscript type, databases, date range, eligibility criteria and optional population/intervention/comparator/outcome fields. Enter queries yourself or use **Plan search queries** to propose them. Planning does not pretend a search has happened.
2. **Search databases:** run actual requests to PubMed, Semantic Scholar, arXiv, Crossref and/or Europe PMC. Queries, timestamps, counts, caps and failures are recorded. DOI, PubMed ID, arXiv ID and cautious title/year matching merge duplicate records while retaining provenance.
3. **Screen:** select papers and explicitly include or exclude them. Exclusion requires a reason. Included papers become evidence sources in the project. Retraction flags are surfaced and block ordinary inclusion.
4. **Read and appraise:** retrieve available open full text or attach a paper you have uploaded and identified. Abstract-only records remain labelled. Appraisal records the reported design, sample, findings, limitations, opposing evidence and exact supporting quotations. Missing details stay missing; they are not filled from a plausible-sounding template.
5. **Outline and write:** create an editable scientific outline, then draft sections using the actual evidence and search history. Graph exploration and angle discovery are available, but a proposed framing is a hypothesis to test, not permission to force the evidence. The manuscript includes an editable abstract and keywords.
6. **Review and export:** inspect source support, complete the author declarations and submission checks, then export a Word manuscript or the full research package.

### Scholarly connections

Search uses public scholarly APIs, not an LLM pretending to have searched. It does not require a writing-model API key. Optional **NCBI** and **Semantic Scholar** keys are available in Connections and use the existing secure credential storage. Anonymous Semantic Scholar access may be rate-limited; a failed request is recorded as a failure, not as zero results. No paywall bypass or unauthorized access is implemented.

Crossref discovery is scoped to journal articles. arXiv records remain clearly labelled as preprints. A database listing does not by itself establish peer review, validity or absence of retraction. Author names supplied as unstructured strings can need correction, especially compound surnames and group authors; **Reference details** makes that editable.

Retrieval is deliberately bounded: up to 100 results per query per database and 600 unique records per project. Caps are visible in the search log. A capped result set is not described as exhaustive. Systematic/scoping submission checks flag truncated searches, unscreened records, failed databases and missing eligibility criteria. This edition is not a replacement for an exhaustive systematic-review retrieval/screening platform.

### Manuscript types

The default is an evidence-led narrative review: genuine secondary research rather than invented original experimentation. Scoping/systematic review and protocol structures are also available, with stronger completeness checks. A protocol describes planned procedures in future tense. **Empirical article** mode requires the author's own completed methods/results report; it does not invent a dataset, statistical test, p-value, registration or ethics approval.

Appraisal of a very long source can use explicitly labelled beginning/middle/end excerpts. Full-text extraction does not imply that every figure or complex table has been interpreted. Inspect the originals and the recorded coverage before relying on detailed claims.

## APA export and the review package

The Word exporter implements an **APA 7 professional-manuscript template**: US Letter, one-inch margins, consistent 12-point Times New Roman, double spacing, first-line paragraph indentation, running head and page numbers, professional title/author-note page, abstract and keywords, academic headings, and hanging-indented references. References are generated from retrieved or author-corrected metadata, not from language-model guesses.

Internal `[S#]` source links resolve to APA author-year citations, including grouped same-author works and same-year letter suffixes. Journal/preprint references retain journal/volume italics and DOI links. Specialized books, proceedings or corrected entries can use an explicit author-supplied APA reference override; they should not be mistaken for ordinary journal references. Metadata title casing and source-specific edge cases still need author review.

The **working research package** contains:

- `manuscript.docx` and `manuscript.md`;
- `references.bib` and `references.ris`;
- `evidence.csv`, `search-log.json` and `protocol.json`;
- `submission-checks.json` and a short scope note.

The separate **Submission package** requires resolved automated blockers and explicit author confirmations for source verification, journal/reporting requirements, authorship/disclosures and method accuracy. Changing the manuscript or research state invalidates those confirmations. A working package remains exportable while work is incomplete. Packages do not include provider keys or the full source-paper library.

Formatting and a checklist cannot confer journal acceptance, peer review or ethics approval. The author remains responsible for the actual research, reporting guideline, analysis, declarations and the target journal's requirements. Model fidelity judgments and exact quote matching are useful checks, not scientific proof.

## Validation

Automated tests cover model-specific effort routing, protected defaults, scholar parsers, deduplication, database failures, screening, source identity, citation formatting, Word structure and submission confirmation invalidation. Real local-HTTP browser tests exercise the complete Science workflow and the reasoning controls. The native Windows regression exercises the actual desktop window, including a Science protocol, and the release workflow gates publication on the packaged native test.

Live metadata connectivity is checked separately from mocked writing tests. A synthetic APA export was rendered and visually inspected using the same exporter source; blank-page and heading-theme problems found by that check were fixed. No scientific finding or prose-quality score is inferred from these software tests. Exact test results and scope are recorded under `docs/validation/v0.3.0`.

## Primary integration references

- OpenAI Codex app-server and model capabilities: https://developers.openai.com/codex/app-server
- Codex configuration: https://developers.openai.com/codex/config-reference
- OpenRouter reasoning: https://openrouter.ai/docs/guides/best-practices/reasoning-tokens
- Anthropic effort: https://platform.claude.com/docs/en/build-with-claude/effort
- Anthropic model capabilities: https://platform.claude.com/docs/en/api/models/list
- NCBI developer APIs: https://www.ncbi.nlm.nih.gov/home/develop/api/
- Semantic Scholar Academic Graph: https://api.semanticscholar.org/api-docs/graph
- arXiv API manual: https://info.arxiv.org/help/api/user-manual.html
- Crossref metadata API: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
- Europe PMC API: https://europepmc.org/RestfulWebService
- APA paper format and reference guidance: https://apastyle.apa.org/style-grammar-guidelines/paper-format and https://apastyle.apa.org/style-grammar-guidelines/references/examples/journal-article-references

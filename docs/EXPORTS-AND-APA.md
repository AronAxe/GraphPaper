# Exports, references and APA manuscripts

Use **Export** from the project header or writing desk. Save a current draft before exporting so the result matches the text you intend to share.

## Ordinary writing projects

| Format | Contents |
|---|---|
| **Word (`.docx`)** | Editable manuscript with basic formatting and eligible source references |
| **Markdown (`.md`)** | Portable plain text retaining headings and source identifiers |
| **HTML (`.html`)** | Safe rendered text with print styling; open in a browser to print or save as PDF |
| **Project backup (`.json`)** | Current project state including source text; not credentials or all historical revisions |
| **Graph (`.json`)** | The stored knowledge graph for external inspection or reuse |

The editor supports a practical Markdown subset, not full desktop-publishing layout. HTML printing is different from a native PDF exporter. Publisher-specific typography and complex tables should be checked in the target editor.

## Science’s APA 7 Word template

Science exports use a professional-manuscript template rather than the ordinary article style:

- US Letter pages, one-inch margins and 12-point Times New Roman.
- Double-spaced prose, paragraph first-line indentation and consistent academic headings.
- Running head and page-number fields.
- Title/author-note page, abstract and keywords, manuscript body, then references.
- Author-year citations and hanging-indented references from structured metadata.

Set author names, affiliations, running head and declarations in **Research protocol**. Abstract and keywords are editable there after generation. **APA preview** shows resolved citations and text structure; the Word file adds page layout and header fields.

This is a general APA 7 professional template, not every journal’s submission format. The journal may require different spacing, separate files, a blinded manuscript or additional reporting checklists.

## How citations are produced

The drafting interface keeps `[S1]`, `[S2]` and similar identifiers as links to evidence. Science export resolves them into parenthetical author-year citations and generates the reference list from eligible cited sources.

The formatter handles ordinary author counts, grouped works and same-year disambiguation. It preserves bibliographic fields rather than asking the model to invent plausible references. An unresolved citation is a problem to fix, not something the exporter silently fills.

Use **Reference details** to correct names, dates, journal details, page ranges and DOI information. Verify compound surnames, group authors, title capitalization, article numbers and other source-specific cases. Specialized entries can use an **APA reference override**, with `*italics*` where needed. The override is your checked reference, not automatic proof of correctness.

Preprints retain their preprint designation. A DOI or journal title alone does not establish peer review. If quoting directly, check APA locator requirements yourself; the writing workflow favors supported paraphrase rather than fabricating page numbers.

## Bibliography and evidence exports

Science also offers **BibTeX**, **RIS**, the **evidence matrix CSV** and the **search log JSON**. The bibliography is based on cited eligible sources; the matrix retains research records and their screening/appraisal information.

CSV cells receive formula-injection protection where appropriate. CSV is an exchange format, not a computed statistical analysis workbook. Review fields imported into your reference manager; each manager may apply its own formatting rules.

## Working research package

The ZIP contains:

```text
manuscript.docx
manuscript.md
references.bib
references.ris
evidence.csv
search-log.json
protocol.json
submission-checks.json
README.txt
```

It is available while the project is still being completed. It does not include the full source-paper collection, model keys or Codex account state. The protocol and log describe what the project recorded, including limits and failures.

## Submission package

The separate submission export requires resolved automated blockers and current author confirmations. Those confirmations cover source checking, the target journal/reporting requirements, authorship/disclosures and the accuracy of the Method description.

A changed draft or research state invalidates previous confirmations. An old approval cannot certify newly edited claims. Use the working package while resolving issues.

Software checks do not confer peer review, ethics approval or journal acceptance. Confirm the final Word layout and required supplementary files before submitting through the journal’s own system.

## Backup versus manuscript export

A manuscript export is not a project backup. A project JSON backup is not the full revision database. For a complete history copy, close GraphPaper and back up its local data directory. [Project storage and recovery →](PROJECTS-AND-SOURCES.md#backups-and-recovery)

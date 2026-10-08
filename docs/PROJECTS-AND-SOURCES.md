# Projects, sources and folders

A project brings together its brief, sources, graph, angles, outline, draft and review. Science projects also retain search records, screening decisions and their research protocol. Projects have stable internal IDs; renaming one does not change its identity.

## Source roles

| Role | Use it for | Do not treat it as |
|---|---|---|
| **Evidence** | Reporting, research and other material that may support factual claims | Automatically verified truth |
| **Canon** | Established fictional events and world rules | Real-world evidence |
| **Inspiration** | Background ideas or possible directions | Approved fictional canon or factual support |
| **Voice** | Your own prose samples | A source of facts to cite |

Open a source to read the extracted text and change its role. Excluding a source from use does not erase its saved text. Changes to the material can invalidate graph coverage, voice profiles or scientific appraisals; the relevant stage should be refreshed.

## Reusable voices are separate

Prefer the **My voices** library for style training. Its articles are not mixed into the evidence cards or copied into each project that uses the voice. Older project-role Voice sources remain readable and can seed a reusable profile without deletion. **Save as reusable voice** copies their training material into the library, while applying the saved graph copies only its compact snapshot. [Voice library](VOICE-GRAPHS.md).

## Add material through the interface

**Upload:** PDF, DOCX, TXT, Markdown, CSV or HTML. The per-file upload limit is 20 MB; extracted source text is limited to two million characters. CSV is imported as text, not silently converted into a statistical analysis.

**Paste:** give the source a title and paste the original text. Optional author and URL information help with provenance.

**Add URL:** fetch a public article or PDF. The importer does not bring browser cookies, log into sites or bypass paywalls. A blocked page can be replaced by a permitted uploaded copy. Check the imported result for a landing page or missing sections.

Image-only PDFs need transcription/OCR before import. PDF figures and complex table layouts require manual inspection. Word paragraphs and tables are imported, but comments, tracked-revision history and images are not a claim of complete visual interpretation.

## The project folder

Use **Sources → Project folder** to open the workspace in Windows Explorer. Its ABOUT file identifies the project. The folder contains:

```text
<Project workspace>/
  Inbox/
    Evidence/
    Voice/
    Canon/
    Inspiration/
  Originals/
  Exports/
```

Drop files into the appropriate Inbox subfolder when their role is known. The ordinary Inbox also accepts files. Files uploaded through the app are preserved in Originals. Exports is a convenient place for files you save; it is not an automatic mirror of the current manuscript.

GraphPaper checks for Inbox changes about every five seconds while the project is **open, visible and idle**. It waits for a stable file before importing. **Import files now** performs an explicit check. Files added while the application is closed are discovered on a later visit, not by a background service.

Changing an already tracked Inbox file updates its associated source instead of repeatedly adding duplicates. Removing the file leaves the imported source intact. Importing a document does not automatically trigger paid extraction, appraisal or writing calls.

The folder is project-associated, but it is **not the authoritative project database**. Graphs, drafts, settings and revision history are kept in SQLite. Deleting a project from the application does not delete its folder.

## Where work is stored

The normal Windows data directory is `%LOCALAPPDATA%\GraphPaper`. The application shows the configured directory in Connections. Developers can set `GRAPHPAPER_DATA_DIR` for an isolated test environment.

| Item | Purpose |
|---|---|
| `studio.sqlite3` | Projects, source text, drafts, revisions, graph-edit undo history, saved voices and training pieces, settings and cache |
| Project workspaces | Inbox imports, preserved uploads and author-managed exports |
| `credentials.dpapi` | API credentials encrypted for the Windows user context |
| `codex-account/` | Separate Codex-managed account state |
| `desktop.log`, `setup.log` | Local diagnostics |

Do not upload the full data directory to a public issue. It can contain unpublished writing, source texts and credentials. See [Privacy](SECURITY.md).

## Backups and recovery

**Export → Project backup** creates a portable JSON copy of the current project. It includes source text and the current graph, outline, manuscript and associated project fields, but not provider keys or the complete historical revision database. Importing a backup creates a separate project copy rather than overwriting the existing one.

A project backup contains its applied compact voice snapshot, not the global voice library or its training pieces. **Export voice** exports a reusable compact graph separately. Camera and manually arranged graph positions are local view settings and are not currently included in the project JSON.

For a **full-history backup**, including the full voice library, close GraphPaper and copy the complete data directory. Protect that copy as confidential. Windows-encrypted credentials may not decrypt under another user or computer; plan to sign in or re-enter keys there.

Versions provide earlier drafts and generated checkpoints. Restoring a version preserves the draft it replaces. After restoration, rerun reviews that no longer describe the current text, and recheck fiction ledgers or scientific confirmations where relevant.

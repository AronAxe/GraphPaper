# API recipes (GraphPaper 0.7.1)

`gp.py` is a small standard-library client. Global `--url` and `--timeout` precede the subcommand. Every command performs the normal local session-cookie handshake and sends `X-GraphPaper: 1`. It does not disable the application's origin checks. No redirects or environment proxy are followed.

Use JSON files or stdin (`--json-file -`), not command-line secrets or interpolated source text. `--output file.json` saves large results to an agent scratch file; an existing file requires `--overwrite`. `export` also refuses overwrites by default. Saved API/project results can contain private source text: keep them out of Git and inspect before sharing.

```sh
python /path/to/skill/scripts/gp.py api POST /api/projects --json-file create.json --output project.json
```

`create.json`:
```json
{"title":"A specific working title","mode":"polemic"}
```

The result supplies the actual `id` and `version`. Use returned IDs throughout; `PID`, `VID`, `RID` and `JID` below are notation, not literal IDs. Fetch a project with `GET /api/projects/PID`.

## Editing without clobbering work

To update a brief, read the current project, merge into its existing `brief`, and PATCH only `version` plus changed top-level fields. Replacing a nested object with a tiny fragment can reset its other fields. Full draft contents are sent under `draft`; outlines and angles use their existing model shapes. Example using the bundled client from Python:

```python
from gp import Client  # add the skill's scripts directory to sys.path
c = Client('http://127.0.0.1:8765')
p = c.request('GET', '/api/projects/' + project_id)
brief = {**p['brief'], 'thesis': author_thesis, 'direction': author_reasoning,
         'stance_policy': 'preserve', 'rhetorical_force': 90}
p = c.request('PATCH', '/api/projects/' + project_id,
              {'version': p['version'], 'brief': brief})
```

A 409 is a conflict, not permission to fetch a new number and overwrite newer text blindly. Reconcile the changes. After a job or import, fetch the updated project again.

## Material and graph

| Operation | Request |
|---|---|
| Direct document upload | `gp.py upload --project PID --role evidence /path/to/source.pdf` |
| Canon or inspiration | Same upload, with `--role canon` or `--role inspiration` |
| Add text | `POST /api/projects/PID/sources/text` with `title`, `text`, `role`, optional `url`, `author`, `published` |
| Fetch a supplied public URL | `POST /api/projects/PID/sources/url` with `url`, `role` |
| Workspace paths | `GET /api/projects/PID/workspace` |
| Explicit Inbox import | `POST /api/projects/PID/workspace/scan` with `{"force":true}` |
| Import graph | `POST /api/projects/PID/graph/import` with `nodes` and `edges` or `links` |
| Inspect graph | Project response's `graph`, or `GET /api/projects/PID/export/graph` |
| Follow connection | `GET /api/projects/PID/graph/path?a=NODE_ID&b=NODE_ID` (URL-encode both IDs) |

Use **one** ingestion route per document. For Inbox, use the server-returned paths, scan explicitly, inspect the result and fetch the project. A directory full of files does not prove they were imported. A duplicate response is not permission to invent a new source ID. Graph import resets proposed angles and selection; export a backup first for an existing project. Imported links are not verified evidence.

## Model jobs

```sh
python /path/to/skill/scripts/gp.py job PID graph --wait-seconds 1800
python /path/to/skill/scripts/gp.py job PID angles --output angle-job.json
python /path/to/skill/scripts/gp.py wait JID --wait-seconds 1800
python /path/to/skill/scripts/gp.py cancel JID
```

The `job` command posts once, writes `submitted_job` to stderr immediately, then polls until the backend reports a terminal state. HTTP failure never retries a write automatically. `wait` resumes polling. Exit codes: **0 completed command; 2 request/configuration error; 3 failed/cancelled job; 4 polling deadline; 130 interruption**. A deadline does not cancel the job or start a replacement. A raw `api POST .../jobs` only submits: follow it with `wait`.

Actions: `graph`, `angles`, `outline`, `draft`, `review`, `revise`, `voice`, `humanize`, `deslop`, `both`, `system-one-audit`, `science-plan`, `science-search`, `science-screen`, `science-fulltext`, `science-appraise`, `science-outline`, `science-draft`, `science-review`. Use `--instruction-file` for revision direction. The 8,000-character instruction limit is checked before submission, not silently clipped.

## Decisions and exports

`GET /api/projects/PID/system-one` returns actual stored state, receipts, feedback and settings. `POST .../system-one/feedback` requires current `version`, `angle_id`, `label` (0/1), optional `correction`. Only record the user's real preference, not the agent's opinion disguised as a human label. `POST .../system-one/train` may refuse insufficient data; that is not a bug to bypass.

```sh
python /path/to/skill/scripts/gp.py export /api/projects/PID/export/md draft.md
python /path/to/skill/scripts/gp.py export /api/projects/PID/export/docx draft.docx
python /path/to/skill/scripts/gp.py export /api/projects/PID/export/json project-backup.json
python /path/to/skill/scripts/gp.py export /api/projects/PID/export/system-one decisions.json
```

These save directly; no native file dialog. Other existing formats include `html`, `graph`, and Science `bib`, `ris`, `evidence`, `search-log`, `research-package`, `submission`. Submission export is gated; normal draft export is not journal approval.

`POST /api/import` accepts an exported project and creates a **separate imported copy**, revalidating source anchors. It does not restore provider credentials. List/read/restore revisions through `GET /api/projects/PID/revisions` and `POST /api/projects/PID/revisions/RID/restore` (restores manuscript text, not an entire historical graph). Back up before destructive operations; the skill is not permission to delete existing work.

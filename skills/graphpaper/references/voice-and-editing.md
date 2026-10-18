# Reusable voices and reversible prose editing

## Voice library, not the article pile

Read `GET /api/voices` first. Reuse the named saved voice; do not retrain it for every article. Read one with `GET /api/voices/VID`. The library returns `profile`, `graph`, sample metadata, `version` and relearning state.

For a new voice:

1. `POST /api/voices` with `{"name":"Requested voice"}`. Keep the returned ID.
2. `gp.py upload --voice VID /path/to/author-sample.docx`. Text and supplied URL alternatives are `POST /api/voices/VID/samples/text` (`title`, `text`) and `/samples/url` (`url`). Do not crawl an entire author website without scope. `/api/voice/discover` can identify candidate articles for selection.
3. Fetch the voice's current version. `POST /api/voices/VID/learn` with `{"version":VERSION}` returns a job. Poll it using `gp.py wait JID`; learning is a model call, not just a file save.
4. Fetch the **project's** current version. `POST /api/projects/PID/voice/apply` with `{"version":PROJECT_VERSION,"voice_id":"VID"}` applies a saved snapshot, with no retraining.

An explicit author style description can initialize `POST /api/voices` using `name` and `instructions`, or `graph`. That is an authored profile, not a claim it was learned from samples. Current project instructions override its habits; stronger language is allowed. Reuse never converts style statements into factual evidence.

Export a voice with `gp.py export /api/voices/VID/export voice.json`. Import on another machine/workspace using `POST /api/voices/import` and that JSON. Training articles are deliberately not included in the reusable graph export. A changed library voice does not silently rewrite every existing project's applied snapshot; apply the updated voice explicitly.

## Prose proposals

`POST /api/projects/PID/craft/audit` runs local phrase/structure heuristics. These are cues, not AI-authorship detection or blanket bans on wording. A deliberate rhetorical contrast may be good writing.

For a model edit, run `humanize`, `deslop` or `both` with an instruction file as needed. After completion, fetch the project and inspect `polish.draft`, `polish.diff`, `polish.review` and the original. **The proposal is not the current manuscript yet.** Preserve quotations, numbers, citations, causal meaning, character motivation and the author's chosen conclusion. Removing a valid hedge is a factual change; removing an unrelated obligatory caveat can restore the intended argument.

Accept through `POST /api/projects/PID/craft/accept` with the current project `version`, after the comparison and within delegated editing authority. Do not set `acknowledge_warnings=true` on the user's behalf to force through a flagged semantic change. Refetch on conflict. `POST .../craft/discard` with current `version` removes the proposal; original text remains. Existing versions can be read and restored through the normal revision endpoints.

Do not feed agent preferences into `/system-one/feedback` as if the user approved them. Store real author corrections, scoped to that voice/mode, and respect newer instructions. If preference training has insufficient independent data, retain the baseline rather than manufacturing labels.

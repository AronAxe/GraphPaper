# GraphPaper 0.2 — your voice, your project folder, cleaner prose

## Your writing voice

In **Sources → Your writing voice**, upload your own writing, paste a sample, or choose **Find my writing online**. The website tool reads the article/author page you enter and lists up to 30 same-site candidate links. Choose up to 12 of your own pieces to import. It does not assume every link was written by you or crawl an entire site invisibly.

**Learn my writing style** analyzes balanced beginning/middle/end excerpts and measurable cadence. The resulting profile is editable and has an influence slider and an on/off switch. It guides drafting, revision and humanizing. This is reusable, source-informed prompting, not weight fine-tuning or a guarantee of perfect imitation. Voice samples never become factual citations. When samples change, an old learned profile is ignored until refreshed; current samples can still guide style. Explicitly edited instructions are treated as author direction.

## A folder for every project

**Sources → Project folder** opens the project's workspace in Windows Explorer. Its stable ID keeps it associated with the same project even after renaming. The folder's ABOUT file records its human-readable title.

Put files in **Inbox**, or its **Evidence**, **Voice**, **Canon** or **Inspiration** subfolders. GraphPaper checks automatically every five seconds while that project is open, visible and idle. It waits for a stable file before importing; **Import files now** runs an explicit check. Files added while the app is closed are picked up on a later visit. Source changes do not silently trigger paid model requests.

Changed inbox files update their associated sources without multiplying duplicates. Removing files leaves the imported source intact. Source roles, file limits, symlink checks and conflict protection remain in effect. Uploads through the app are also kept in **Originals**. **Exports** is an available folder for your own output. Deleting the database project does not delete the folder. SQLite still holds the authoritative graph, outline, draft and history; use Export → Project backup for a portable project.

## Humanizer and deslopping

The writing desk offers **Humanize**, **Deslop**, **Both**, and a no-cost **Inspect prose** action. Humanizing focuses on the author's cadence and expression; deslopping focuses on filler, repetition, staged emphasis, formulaic contrasts and unsupported vague attribution.

These are editing tools, not AI-authorship detectors or promises to evade detection. Intentional dashes, repetition, formal language, humor and scientific qualifications are not blindly banned. The author's samples take precedence over generic style advice.

Quoted text, numbers, citations, links, code and blockquotes are protected during the edit. Missing or newly invented protected material fails validation. A separate editorial check looks for meaning drift. The proposal is stored separately, with side-by-side comparison and a line diff. **Accept** is explicit; changed drafts cannot be overwritten by stale proposals, and the previous draft remains in Versions. A model's fidelity judgment is not proof; check material claims yourself.

### Research and inspiration

GitHub searches for widely starred writing humanizers identified **blader/humanizer**, whose repository showed **54,162 stars on 5 October 2026**. Its structural-pattern-first approach, author-sample priority, and rewrite-then-check workflow informed this independent implementation. **stephenturner/skill-deslop** provided a second writing-specific reference for filler, repeated structures, inflated stakes and context-sensitive register. **peteromallet/desloppify** was excluded as the main prose reference because it targets code quality rather than article editing. No code or full prompt text from those projects is vendored here.

Primary references:
- https://github.com/blader/humanizer
- https://github.com/blader/humanizer/blob/main/SKILL.md
- https://github.com/stephenturner/skill-deslop
- https://github.com/stephenturner/skill-deslop/blob/main/SKILL.md

## Codex / ChatGPT sign-in instead of a writing API key

In **Connections**, select **Codex — sign in with ChatGPT**, then press **Sign in with ChatGPT**. Complete the official browser flow and check the connection. A blank model uses Codex's configured default; the model list can also be loaded. The Windows release bundles an official, digest-verified Codex runtime. A source installation can point to an existing native runtime.

GraphPaper uses Codex's documented app-server login and non-interactive execution. It does not scrape ChatGPT, ask you to paste session tokens, read another application's auth.json, or silently fall back to API billing. Codex handles its own credentials in GraphPaper's separate `codex-account` directory. Sign-out affects this directory, not your other Codex setups. Runtime provenance and its Apache licence are included in the bundle. Provider API keys are not inherited by the child process.

Writing through Codex consumes the applicable ChatGPT/Codex account allowance and remains subject to that account's limits and OpenAI's policies. Cloud processing still needs your consent. Codex controls its own output limits; GraphPaper's API output-token setting does not override them. Token usage is recorded when the runtime reports it, without inventing a monetary cost. **JEV is separate**: it needs its own optional OpenRouter/TypeSafe connection. Without one, writing still works and graph screening is explicitly unscored. External Graphify CLI mode also needs separate API credentials; Native graph extraction works with Codex sign-in.

Primary official documentation:
- https://developers.openai.com/codex/auth
- https://developers.openai.com/codex/app-server
- https://developers.openai.com/codex/noninteractive
- https://github.com/openai/codex

## Validation boundaries

The release process runs the existing suite plus new voice, inbox, provenance, protected-edit and Codex subprocess tests. Browser workflows exercise uploads, voice learning/editing, folder ownership and automatic import, humanizing/deslopping comparisons, acceptance/rejection and the Codex settings option. Controlled model and authentication doubles do not establish real prose quality or complete a real user OAuth ceremony.

A separate Windows check runs the actual bundled Codex executable, verifies the supported CLI flags, and performs a signed-out app-server handshake. No live model request or user sign-in is performed in CI. The compiled GraphPaper application also runs its backend/assets self-test. Interactive Windows dialog behavior and completion of your own browser sign-in remain user-environment checks. The executable is unsigned.

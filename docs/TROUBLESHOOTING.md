# Troubleshooting

Start with the exact application version and the action that failed. Preserve your draft and source material before trying changes; most connection or extraction problems do not require resetting the database.

## Desktop startup and freezing

**Window opens but freezes on interaction:** use the latest release. Version 0.2.1 corrected recursive exposure of native Windows objects and a save-on-close deadlock; later releases retain those fixes. Extract into a new folder rather than mixing old and new `_internal` files. If the problem persists, record the version, Windows version and whether it happens in a new empty project.

**Missing dependencies or WebView errors:** check that the full release was extracted and that Edge WebView2 is installed. Do not move the executable without its companion directory. Source-edition users should check Python/Tcl-Tk and `setup.log`. [Windows guide →](WINDOWS.md)

**Close appears to wait:** the app asks the editor to finish pending saves. A failed save should be resolved rather than discarding work to make the window disappear. Cancel active model work deliberately; an in-flight request can still consume provider allowance.

## Models and reasoning

| Message or symptom | Action |
|---|---|
| Model not found / HTTP 404 | Confirm provider and base URL, reload its model list, and choose an available ID. |
| HTTP 401/403 | Check the credential and account’s access to the selected service/model. |
| HTTP 402 | Check provider credit or billing. |
| HTTP 429 | Wait for the service’s limit to clear or use an appropriately authorized key/account. |
| Reasoning effort not advertised | Reload capabilities or choose Provider default; do not assume every model supports ultra/max/xhigh. |
| Output truncated | Increase a supported output cap or reduce the task; incomplete output is not installed as a finished draft. |
| Context too large | Use an appropriate model/budget, reduce selected material or split the project. The budget is in characters, not a universal token count. |
| Cloud permission disabled | Enable it only when the material may be shared with the configured provider. |

For Codex sign-in problems, use its GraphPaper-specific sign-in controls and check that the bundled runtime is intact. A blank writer model can use the Codex default. JEV is separate: being signed into Codex does not authenticate TypeSafe or OpenRouter.

A network timeout can represent a request the provider already processed. The app avoids assuming that an unobserved request was free. Repeated retries can incur additional charges.

## Graph studio and reusable voices

**Graph is too dense:** select a relevant node, use **Focus here** or one/two hops, reduce **Show**, or filter connection types. **Spread nodes apart** and zoom help; **2D** provides a flat view. Hidden nodes remain stored and searchable.

**Graph seems to disappear:** clear the search and use **Reset filters**, then **Fit graph** or **Reset camera**. A view setting is not data deletion.

**Edit did not save:** node/connection inspector changes require **Save node**, **Save connection** or Ctrl+S. Editing is blocked during active AI jobs. A stale-version conflict protects newer data; refresh before retrying instead of overwriting it.

**Undo is unavailable after extraction:** graph-only undo refuses to replace a graph that was rebuilt or imported after the edit. It is separate from manuscript Versions.

**Saved voice missing from another article:** open **My voices**, select it and choose **Use in this project**. A project-only profile first needs **Save as reusable voice**. No retraining is needed for an already learned profile.

**Library changes did not alter an existing project:** each project keeps an applied snapshot. Reapply the saved voice deliberately, then refresh affected angles/outline as needed.

## External Graphify and JEV requests

**Adapter expects Graphify 0.9.80:** clear **Custom Graphify executable**, save connections and run **Check Graphify runtime** to use the included runtime. Keep Graphify selected as the engine. An explicit custom path overrides the bundled copy.

**JEV exceeds the old 60,000-character limit:** use v0.6 with the request-sizing fix introduced in v0.5. The app preflights UTF-8 size, batches automatically and excludes raw voice-training articles. An oversized optional decision should now be labelled unscored, not fail the whole job. If the old exact error persists, confirm the executable version rather than weakening the brief or retraining the voice. Report provider/API failures separately.

## Sources and folders

**The project Inbox did not import a file:** open that project, keep it visible and idle, and wait for the file to stop changing. Then try **Import files now**. Check format and size limits. The folder is not watched by a service while the app is closed.

**PDF has little or no text:** image-only PDFs need OCR/transcription before import. Check extraction warnings, columns, tables and page content. The app does not silently interpret every image as complete text.

**URL import returns a landing page:** paste or upload a permitted copy. No cookies or paywall bypass are used. Some sites block automated reads.

**Graph says sources changed:** rebuild it. Cached unchanged passages can be reused, but stale coverage is not equivalent to a fresh reading.

## Science

**One database failed:** inspect Search log. A failure is not an empty search result. Anonymous Semantic Scholar returned 429 during the recorded 0.3 connectivity check; an optional service key can help where the provider authorizes it.

**No full text:** the abstract remains available, with its scope labelled. Upload a licensed complete paper and attach it to the exact record, or disclose the access limitation. Do not claim full-text appraisal from metadata alone.

**Submission export is blocked:** inspect the checklist. Common causes include missing author declarations, unresolved citations, retraction flags, missing evidence or stale author confirmations. A working research package remains exportable.

**Systematic/scoping review has incomplete coverage:** result caps and failed searches are disclosed. Complete or appropriately narrow the actual search and screening; do not relabel a bounded convenience set as exhaustive.

**Wrong author-year reference:** correct structured metadata or a specialized APA override through Reference details. Check compound names and same-year works. [APA guide →](EXPORTS-AND-APA.md)

## Writing and recovery

**Prose proposal no longer applies:** the draft changed after the proposal was generated. Discard it or run a fresh pass; stale proposals cannot overwrite newer text.

**A revision lost a useful passage:** inspect Versions and restore the earlier draft or compare it manually. Restore also preserves the current text as a version. Recheck reviews, fictional ledgers and scientific confirmations afterward.

**Costs show as unknown:** the provider did not report a cost. Unknown is not zero. Codex subscription usage and external Graphify requests are not accurately represented by inventing a dollar price.

## Report a reproducible problem

Open a [GitHub issue](https://github.com/AronAxe/GraphPaper/issues) with the version, source-versus-executable edition, exact action, error text and a small non-confidential example when possible. Say whether the failure occurs in an empty project and which provider/model is involved—without including keys.

Review diagnostics before sharing them. Never attach `credentials.dpapi`, Codex account files, a private manuscript or an unredacted data-directory archive. Security-sensitive disclosures should go privately to the maintainer, not into a public issue. [Privacy and security →](SECURITY.md)

## Angles are too cautious or ignore my voice

Use v0.6.0 or newer. The authorial-intent changes introduced in v0.4 remove forced counterbalancing and supplies voice context to the early editorial stages. In an existing project, choose **current mode · Change -> Polemic**, then edit **Core thesis** and **Rhetorical force**. In Angles, choose **Refresh angles with my voice**; old saved angles do not rewrite themselves when a slider changes. The existing graph is reused. Evidence detail is a separate control and never sets how moderate your position must be. Ordinary Nonfiction can also **Develop and defend my position**.

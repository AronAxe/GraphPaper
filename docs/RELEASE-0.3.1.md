# GraphPaper 0.3.1 - external Graphify with Codex

## Fixed

- The external Graphify action now works with **Codex / ChatGPT OAuth** and the configured GraphPaper provider, extraction model and reasoning setting.
- Graphify runs as the real public upstream command in a separate process. There is **no duplicate Native extraction pass**, no requirement for an additional Codex API key and no automatic switch to API billing.
- The Windows application includes **Graphify 0.9.80**, its public dependencies, metadata, tokenizer cache and licences. Source dependencies are pinned in `requirements-graphify.txt`; no private fork or unpublished backend is needed.
- A temporary, authenticated loopback adapter routes Graphify's bounded text requests through GraphPaper. Provider/OAuth credentials are not passed to Graphify. The extraction shares the job's request accounting and honours configured reasoning.
- Missing backends, malformed/empty graph output, dangling edges, cancellation and timeouts leave the previous graph and source documents intact.
- External source-file provenance is preserved in the graph inspector and downstream angle retrieval without treating it as proof of a claim.
- Added graphical runtime diagnostics, total extraction timeout and chunk-budget controls, plus release gates that actually exercise the bundled worker rather than merely checking the window's HTTP assets.

The existing author-voice, project-folder, humanizer/deslop, Science/APA and native Windows freeze fixes remain in place.

## Download and use

Extract **GraphPaper-v0.3.1-Windows-x64.zip** into a new folder and run **GraphPaper.exe**. Keep `_internal` beside it. The binary is unsigned; no separate Python or Graphify installation is required for this Windows package.

In **Connections & settings**, keep or select your provider, choose the extraction model and reasoning depth, and select **Graphify (external process)** under **Advanced limits & Graphify**. Leave **Custom Graphify executable** blank for the included runtime. An old explicit custom path is not silently overridden; clear it when switching to the bundled runtime. **Check Graphify runtime** makes no model call.

## Testing and scope

Validation separates implementation tests, real upstream Graphify execution, a real Codex-backed extraction, and compiled Windows/native checks. Model fixtures are explicitly synthetic. The real Codex test uses synthetic documents in an isolated project, not an existing manuscript. Versioned reports record the exact platforms, outcomes and archive checksum.

Cancellation cannot refund a provider request that was already submitted. File attribution and quote matching do not prove scientific validity. macOS compatibility is not presented as a tested desktop build. Existing local installations are not modified by publishing this release.

[Integration and distribution guide](https://github.com/AronAxe/GraphPaper/blob/main/docs/UPDATE-0.3.1.md) · [Public Graphify distribution](https://pypi.org/project/graphifyy/0.9.80/)

## Verified build

217 automated Windows tests passed (1 platform-permission skip). All 44 browser workflow checks passed, all 10 native-source checks passed, and all 15 checks against the actual compiled executable passed. The compiled-native checks include a real public Graphify worker with synthetic model transport, source provenance, native Save As and save-on-close.

Real Codex-backed extraction was verified separately with synthetic documents and the packaged Graphify worker, using the explicitly selected `gpt-6-luna` model at `low` reasoning. It used 1 model request(s), with no duplicate Native pass or API-key fallback. Exact outcomes, dependency versions and platform results are recorded in `docs/validation/v0.3.1`. This is not a claim of paid API testing for every provider or a macOS desktop build.

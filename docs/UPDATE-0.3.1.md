# GraphPaper 0.3.1: external Graphify with Codex

This update repairs the external Graphify action. It uses the actual, unmodified public **Graphify 0.9.80** command, not a Native extraction pass relabelled as Graphify and not an unpublished fork.

## Using the Windows release

Open **Connections & settings** and select your writing provider. Codex users can keep **Sign in with ChatGPT**. Choose the extraction model and its reasoning level, then select **Graphify (external process)** in **Advanced limits & Graphify**.

Leave **Custom Graphify executable** blank to use the runtime included in the Windows package. Use **Check Graphify runtime** to verify it without making a model call. An explicit custom path is respected; an invalid path or unsupported version is not silently replaced. Clear an old custom path when switching to the included runtime.

Open a project and choose **Build graph**. Only enabled non-voice source text is exported into the job's temporary input directory. Graphify runs in a separate process and returns its graph to GraphPaper. File references point back to the original project sources. The source library and settings are not replaced.

The result feeds the ordinary graph, angle and writing workflow. File provenance supplies bounded original passages for angle evaluation; it is not automatically promoted to verified evidence. No second Native extraction is run after Graphify.

## Codex, other providers and reasoning

Graphify's public OpenAI-compatible backend connects to a temporary local GraphPaper endpoint. GraphPaper supplies the inference through its selected extraction provider:

- **Codex / ChatGPT OAuth:** the official Codex runtime performs the text-only completion using the existing signed-in account. No additional writing API key or API-billing fallback is introduced.
- **OpenRouter, OpenAI-compatible and Anthropic:** the existing GraphPaper provider adapters retain their selected model, reasoning controls, consent and request limits.

The extraction model is used when set; otherwise the writer model is used. **The extraction reasoning setting is used**, not the writer's or editor's setting. Provider default still sends no reasoning override. Unsupported model/effort combinations fail rather than silently substituting a lower setting.

The child receives a random, job-specific local credential and a fixed local model alias. It does not receive the actual provider API key or Codex OAuth credentials. The local endpoint accepts only the bounded text-extraction request shape, listens only on loopback, rejects browser-origin requests and does not expose tools, an arbitrary model router or an arbitrary upstream URL.

This is a controlled integration, not an operating-system security sandbox. Only run a custom executable you trust. Native process ownership and a temporary configuration home reduce accidental interaction with unrelated work; they are not a claim that hostile programs cannot access the computer under the current user account.

## Budgets, cancellation and failures

Graphify's inference passes through GraphPaper's existing request accounting. There is one inference request at a time, no separate unmetered API path, no second Native pass, and no hidden API-key fallback. Graphify SDK and chunk-retry settings are disabled so the two systems do not multiply retries. GraphPaper's own documented bounded provider handling remains in effect.

The UI exposes the **total extraction timeout** and Graphify's approximate input-chunk budget. The selected provider's request timeout and output limit still apply where supported by that provider. An output-token limit is not an exact input tokenizer or a guaranteed monetary cap.

Cancellation stops the owned Graphify process tree and signals the in-flight inference. Official Codex execution checks this cancellation while waiting. A submitted cloud API request may already have consumed tokens or may finish after cancellation; cancelling is not a billing reversal. Late results cannot overwrite the old project graph.

Malformed JSON, non-finite values, empty graphs, duplicate node IDs, dangling edges, missing output and oversized output are rejected before the result is committed. A failed extraction leaves the prior source documents, graph and manuscript intact. Usage and failure history can still record the attempt.

## Public dependency and distribution strategy

The source dependency is declared in [requirements-graphify.txt](../requirements-graphify.txt). It uses the public PyPI distribution `graphifyy[openai]==0.9.80`; the verified SDK/tokenizer versions are pinned alongside it. No private repository, local-only backend patch or unreleased upstream feature is required.

For a source environment:

```bash
python -m pip install -r requirements-graphify.txt
python scripts/prepare_graphify.py
```

The graphical Windows source launcher installs its desktop requirements, including the public Graphify dependencies. Its dependency fingerprint includes the Graphify requirements file. Native-only Python environments may omit this optional runtime, but cannot claim external Graphify is available until its probe succeeds.

The **Windows ZIP includes the Graphify Python modules, runtime dependencies, distribution metadata, tokenizer cache, upstream licences/notices and official Codex executable**. GraphPaper launches a dedicated worker mode of its own executable to host the unmodified Graphify CLI; it does not require a separate system Python or Graphify installation.

The worker launch supplies `PYTHONHASHSEED=0` before Python starts, satisfying the upstream startup contract without its normal `python -m graphify` re-execution. A frozen GraphPaper executable is not treated as a general Python command.

Release preparation verifies installed dependency versions, prepares the tokenizer cache and requires the upstream licence. The package contains `vendor/graphify-runtime.json` inside its bundled assets, recording versions, public provenance and cache/licence checksums. Packaging tests must exercise the frozen Graphify worker, not merely check that the main window's HTTP assets load.

A custom Graphify executable must match the supported release and have its OpenAI-compatible SDK dependencies installed. Its version probe cannot establish the health of an arbitrary custom environment; the included runtime has the stronger package-level verification.

## Validation scope

The tests distinguish these operations:

1. Pure validation and backward-compatible data defaults.
2. The real public Graphify process with synthetic provider responses, including failure, cancellation, timeout, source exclusion and model/effort routing.
3. A real Codex-backed extraction through GraphPaper's external action, with synthetic documents and an isolated project.
4. The compiled Windows worker and actual native Windows interface.

The recorded live Codex test uses an explicitly selected model/effort rather than silently changing the user's settings. It sends only the synthetic test material. No installed application update or experiment on an existing manuscript is part of this delivery.

See the versioned validation reports for actual platform and packaging results. Windows native execution is distinct from Linux source tests and from compatibility inferred for macOS. Do not interpret source compatibility as a tested macOS desktop package.

## Primary references

- [Public graphifyy distribution](https://pypi.org/project/graphifyy/0.9.80/)
- [Graphify upstream source](https://github.com/Graphify-Labs/graphify)
- [Graphify documentation](https://docs.graphify.com)
- [Codex non-interactive execution](https://developers.openai.com/codex/noninteractive)
- [Codex app-server and model discovery](https://developers.openai.com/codex/app-server)
- [Codex reasoning configuration](https://developers.openai.com/codex/config-reference)

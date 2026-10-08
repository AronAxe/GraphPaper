# Models, authentication and reasoning

Open **Connections & settings** to choose the writing connection. The writer, editor and extraction/research model can be configured separately. Blank editor or extractor model fields use the writing model; reasoning settings are independent, with **Provider default** meaning no explicit override for that role.

## Supported writing routes

| Provider | Authentication | Notes |
|---|---|---|
| **Codex / ChatGPT** | Official browser sign-in | Uses the applicable account allowance; the Windows release bundles the official runtime. |
| **OpenRouter** | API key | Model IDs and available capabilities come from the provider catalog. |
| **OpenAI-compatible** | Provider key or local-server configuration | Set the API base URL and an accepted model ID explicitly. |
| **Anthropic** | Direct API key | Uses the direct Messages API and supported model capabilities. |
| **Local endpoint** | Whatever the local server requires | Use the compatible-provider route and a localhost base URL. |

GraphPaper never silently changes a Codex subscription request into API billing. Provider availability, account limits and service terms are external to the app.

## Codex sign-in

Select **Codex — sign in with ChatGPT**, press **Sign in with ChatGPT**, and complete the official browser flow. Load available models afterward. A blank writer model can use Codex’s configured default; loading its catalog makes explicit reasoning choices possible.

Codex manages credentials under GraphPaper’s separate `codex-account` directory. GraphPaper does not ask for pasted browser session tokens or reuse another application’s account file. Signing out applies to this account directory, not every Codex installation on the machine.

The runtime is bundled in the compiled Windows release. A source installation can select an existing native executable. Keep the release’s vendor files and provenance together.

## API and local-model setup

Select the provider before entering its base URL. Save the correct key and use **Load available models**, or enter a model ID supported by that endpoint. OpenRouter can use its dedicated key field; direct TypeSafe is only for JEV decisions, not an ordinary writer.

The compatible API base should point to the service’s API root, commonly ending in `/v1`, rather than to a model’s website. The application supports unencrypted HTTP only for a local model server. A remote provider should use HTTPS.

Connection tests make a real, small model request. Saving settings or loading model metadata is not the same as proving a full manuscript call will fit its context and output limits.

## Reasoning depth

Load model capabilities, then set each role’s reasoning level. There is no universal ladder that every provider implements.

| Route | How the selected effort is sent |
|---|---|
| Codex | Model-advertised efforts, passed to the runtime as `model_reasoning_effort` |
| OpenRouter | `reasoning.effort`, with routing required to support the supplied parameters |
| OpenAI-compatible | `reasoning_effort` |
| Anthropic | `output_config.effort`, plus adaptive thinking when supported |

Codex options such as `xhigh`, `max` or `ultra` appear only when the selected model advertises them. Unsupported choices are rejected rather than mapped to an invented equivalent.

Some API catalogs advertise reasoning generally but not a complete model-specific effort list. In that case, the interface labels the provider vocabulary as unverified for the model. The provider may reject an unsupported combination; refresh capabilities or use **Provider default**.

A **Budget** option is available where explicit thinking-token budgets are supported. The budget must be at least 1,024 tokens and smaller than the total output-token cap. Codex controls its own output behavior; the API output-token setting does not override its runtime.

Higher effort can increase latency and token consumption. It does not set the manuscript word count. Recorded usage receipts include the requested effort for relevant calls.

## Optional JEV

JEV has its own **Auto, OpenRouter, TypeSafe or Off** selector. Auto prefers an available OpenRouter credential, then direct TypeSafe. It does not silently switch routes after a failed paid request.

The application preflights serialized request size and automatically batches decisions. Voice training articles are excluded from those requests; optional decisions that cannot fit stay unscored. [Request-sizing behavior](VOICE-GRAPHS.md#why-jev-no-longer-receives-the-whole-heap).

Without JEV, writing remains available and graph candidates are explicitly unscored. Codex OAuth does not include a JEV connection. [JEV’s role in the workflow →](GRAPH-AND-JEV.md)

## Scholarly database keys

The optional NCBI and Semantic Scholar fields are separate from writing-provider credentials. Database search does not require an LLM API key. Anonymous Semantic Scholar access can be throttled; the search log records this as a failed request, not zero evidence. [Science connections →](SCIENCE.md#search-the-databases)

## Costs, consent and limits

Cloud generation requires explicit permission to send project material. URL imports and scholarly searches are separate network actions. The API model’s retention and processing terms still apply after permission is granted.

Advanced settings include maximum requests per job, output-token cap, context budget in **characters**, candidate count and request timeout. A request limit is not a monetary cap. Provider-reported cost is displayed when supplied; missing cost stays unknown. Cancellation cannot undo a request already submitted.

Never put keys into prompts, screenshots, issue reports or project documents. [Credential storage and privacy →](SECURITY.md)

## External Graphify

Choose **Graphify (external process)** under Advanced limits & Graphify. Leave the custom path blank for the included Windows runtime. **Check Graphify runtime** does not call a model. The external action now uses this same provider connection, including Codex OAuth, with the extraction-role model and reasoning setting. [Detailed setup and distribution](UPDATE-0.3.1.md).

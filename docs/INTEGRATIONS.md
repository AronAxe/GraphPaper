# Integration reference

This page describes the interfaces implemented in GraphPaper 0.3.0. User-facing setup is in [Models and reasoning](CONNECTIONS.md). External endpoints, model IDs and capability vocabularies can change independently; consult the linked primary documentation and test a connection before a large job.

## Writing providers

| Route | Implemented request style |
|---|---|
| OpenRouter | Chat Completions at the configured API base; model discovery and optional reasoning fields |
| OpenAI-compatible | Chat Completions; direct OpenAI hosts use `max_completion_tokens`, other compatible endpoints use `max_tokens` |
| Anthropic | Direct `/v1/messages`, separate system prompt, model capabilities and supported effort/thinking fields |
| Codex | Official app-server authentication/model discovery plus non-interactive runtime execution |

Structured tasks request JSON and validate the relevant contract. Truncated or invalid output does not become a complete manuscript. Retry and request budgets are bounded. A timeout is not treated as proof that a request was unbilled.

Reasoning is selected by role. Provider default omits the override. Codex uses advertised `supportedReasoningEfforts`; extended levels are not guessed. Other routes preserve their native field names and report unsupported combinations instead of silently downgrading them.

Primary references: [Codex authentication](https://developers.openai.com/codex/auth), [app-server](https://developers.openai.com/codex/app-server), [configuration](https://developers.openai.com/codex/config-reference), [OpenRouter reasoning](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens), [Anthropic effort](https://platform.claude.com/docs/en/build-with-claude/effort).

## JEV / TypeSafe

| Route | Endpoint | Default alias |
|---|---|---|
| OpenRouter | `https://openrouter.ai/api/alpha/decisions` | `~typesafe/jev-latest` |
| Direct TypeSafe | `https://api.typesafe.ai/v1/systemone` | `jev-latest` |

Requests include `model`, `state` and typed `questions`, with bearer authorization. The application uses bounded numeric estimates (`noul`) and `choice` responses with explicit criteria. Parsing validates answer types, numeric range and declared choices.

Auto prefers available OpenRouter credentials, then direct TypeSafe; it does not silently fail over after a rejected paid request. No connection means no fabricated JEV score. The application’s combined editorial score is not a calibration result.

Primary references: [OpenRouter JEV guide](https://openrouter.ai/docs/guides/community/jev-tutorial), [TypeSafe quickstart](https://docs.typesafe.ai/introduction/quickstart), [TypeSafe SDK constants](https://docs.typesafe.ai/sdk/python/api/constants).

## Scholarly adapters

| Service | Interface |
|---|---|
| PubMed | E-utilities search and record retrieval, including structured XML metadata |
| Semantic Scholar | Academic Graph paper search with metadata, abstracts and available links |
| arXiv | Atom query API |
| Crossref | REST works discovery, journal-article filter |
| Europe PMC | REST search and available full-text XML |

Queries, limits, timestamps and partial failures are stored. Optional NCBI/Semantic Scholar credentials do not double as writing-model keys. Full-text fetching uses accessible URLs and explicit uploaded-source attachment, not authenticated browser scraping.

Primary references: [NCBI](https://www.ncbi.nlm.nih.gov/home/develop/api/), [Semantic Scholar](https://api.semanticscholar.org/api-docs/graph), [arXiv](https://info.arxiv.org/help/api/user-manual.html), [Crossref](https://www.crossref.org/documentation/retrieve-metadata/rest-api/), [Europe PMC](https://europepmc.org/RestfulWebService).

## Graphify

Native extraction does not require Graphify. Imported Graphify/NetworkX JSON supports `nodes` and either `edges` or `links`; relationships are not accepted as factual evidence merely because the JSON supplies a confidence value.

The optional CLI adapter invokes a user-selected executable without a shell, prepares enabled non-voice source text in a temporary folder and selects the configured provider backend. Its command contract includes:

```text
graphify extract <temporary-source-folder> --backend openai --mode deep --no-viz --no-cluster --token-budget 4000 --max-concurrency 2
```

For direct Anthropic it selects the corresponding Claude backend. The adapter looks for `graphify-out/graph.json` or `graph.json` and adds native evidence extraction. Version compatibility must be checked against the installed Graphify executable. Graphify is not bundled, and the external process has not been validated by a live run in the recorded GraphPaper release tests.

Graphify’s calls and retries are outside GraphPaper’s internal request/cost meter. Codex subscription sign-in is not a drop-in API credential for this external adapter; use native extraction with Codex or provide the external process with its supported API connection.

Project references: [Graphify repository](https://github.com/Graphify-Labs/graphify), [Graphify documentation](https://docs.graphify.com).

## Local API and desktop bridge

The local API is a session-protected implementation interface, not a public multi-tenant service. Routes cover projects, sources, graph operations, jobs, settings, prose proposals, scientific research and exports. Inspect [server.py](../graphpaper/server.py), [studio_routes.py](../graphpaper/studio_routes.py) and [science_routes.py](../graphpaper/science_routes.py) for current schemas.

The native bridge is intentionally narrow; its four methods are `notify_ready`, `save_export`, `request_close` and `cancel_close`. Do not attach public native/store objects to it. [pywebview API](https://pywebview.flowrl.com/api/) provides the underlying desktop contract.

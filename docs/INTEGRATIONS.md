# Integration reference

This page describes the interfaces implemented in GraphPaper 0.6.0. User-facing setup is in [Models and reasoning](CONNECTIONS.md). External endpoints, model IDs and capability vocabularies can change independently; consult the linked primary documentation and test a connection before a large job.

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

The `model`/`state`/`questions` envelope is sized in UTF-8 bytes before sending. Candidate/question batching and compact style-graph context prevent the former oversized-state failure. Original question keys are retained when answers are combined; unscored optional decisions are distinct from API or typed-answer errors. [Voice graphs and request sizing](VOICE-GRAPHS.md).

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

Native extraction remains independently available. External extraction runs the unmodified public `graphifyy[openai]==0.9.80` CLI. The Windows package includes its dependencies, metadata, tokenizer cache and upstream licences; source environments use [requirements-graphify.txt](../requirements-graphify.txt).

The worker receives only an isolated non-voice text corpus and a per-job loopback credential. It calls Graphify's OpenAI-compatible backend, but the authenticated local gateway routes inference through **GraphPaper's selected extraction provider, model and reasoning setting**. This includes official Codex OAuth, OpenRouter, API-compatible and Anthropic connections. No real provider/OAuth credential is passed to Graphify, and no API-key fallback is introduced.

Graphify requests share GraphPaper's budget and receipts. Extraction is serial; upstream retry layers are disabled to avoid multiplying requests. The total deadline and cancellation cover owned workers. A previously submitted cloud request can still consume allowance after cancellation. Invalid, missing, oversized, empty or dangling graph output does not replace the previous graph. No second Native extraction is run.

The output remains an external interpretation. Source-file IDs are retained as retrieval pointers, not truth labels; exact quotation anchors are checked separately. The native graph UI and angle discovery use the completed result.

A custom executable is an explicit trust choice and must match the supported upstream version. Its version check is not a full audit of that custom environment. [Complete protocol, runtime and distribution guide](UPDATE-0.3.1.md)

Primary references: [public Graphify distribution](https://pypi.org/project/graphifyy/0.9.80/), [upstream source](https://github.com/Graphify-Labs/graphify), [Codex non-interactive execution](https://developers.openai.com/codex/noninteractive).

## Local API and desktop bridge

The local API is a session-protected implementation interface, not a public multi-tenant service. Routes cover projects, sources, graph operations, jobs, settings, prose proposals, scientific research and exports. Inspect [server.py](../graphpaper/server.py), [studio_routes.py](../graphpaper/studio_routes.py) and [science_routes.py](../graphpaper/science_routes.py) for the base schemas; [graph editing routes](../graphpaper/graph_editing.py) and [voice library routes](../graphpaper/voice_routes.py) cover the current graph/voice extensions.

The native bridge is intentionally narrow; its four methods are `notify_ready`, `save_export`, `request_close` and `cancel_close`. Do not attach public native/store objects to it. [pywebview API](https://pywebview.flowrl.com/api/) provides the underlying desktop contract.

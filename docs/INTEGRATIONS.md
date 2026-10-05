# Provider and Graphify integrations

## Writing models

OpenRouter is the default provider. Configure any available model ID rather than relying on stale built-in model names. The writer, extraction model and editor can be different. Their use is task-specific; a cheap extractor is only useful when it can reliably preserve negation, attribution and exact quotes.

OpenAI-compatible requests use Chat Completions at the configured `/v1` base. Direct OpenAI hosts use `max_completion_tokens`; other compatible endpoints use `max_tokens`. Direct Anthropic uses `/v1/messages` and separate system text. Not every provider implements every optional convention; the connection test and error messages expose incompatibilities.

Structured generation parses JSON and validates the relevant stage contract. Truncated output fails rather than replacing the previous document. Transport retries are bounded and counted. After a network timeout, the app does not assume an unobserved request was free.

## JEV: OpenRouter preferred, direct TypeSafe available

The implementation follows the published typed-decision interfaces:

| Route | Endpoint | Default alias |
|---|---|---|
| OpenRouter | `https://openrouter.ai/api/alpha/decisions` | `~typesafe/jev-latest` |
| TypeSafe | `https://api.typesafe.ai/v1/systemone` | `jev-latest` |

Both use bearer authorization. Requests contain `model`, `state` and `questions`. Used question types are `noul` (bounded numeric estimate) and `choice` with explicit criteria. Response parsing checks the typed answer, validates numeric range and refuses out-of-vocabulary choices. A displayed score is a model estimate, **not empirical calibration**.

Auto chooses an available OpenRouter credential first, including the ordinary writer key when the writing provider is OpenRouter, then a direct TypeSafe key. It does not silently switch after a failed paid request. Select the route explicitly to control it. Choosing Off keeps the workflow available and displays results as unscored rather than fabricating JEV output.

Relevant primary documentation:
- https://openrouter.ai/docs/guides/community/jev-tutorial
- https://openrouter.ai/docs/guides/community/typesafe-sdk
- https://docs.typesafe.ai/introduction/quickstart
- https://docs.typesafe.ai/sdk/python/api/constants

Transport contracts are covered by mock-response tests. No live credentials were available in the build environment, so live calls have not been verified here. Alpha endpoints and model IDs can change independently of GraphPaper.

## Graphify

The default **Native** mode does not require Graphify. It performs graph extraction itself, with exact source quotation anchors. This is intentional: a writer should not have to set up another agent framework before opening the studio.

**Import:** use Graph view to import Graphify/NetworkX node-link JSON. Both `edges` and `links` arrays are accepted. Imported edges are labelled unverified; external confidence fields do not become factual evidence.

**Run an installed Graphify:** choose Graphify in advanced Connections and provide the installed executable. The bridge runs an argument array without a shell:

```text
graphify extract <temporary-source-folder> --backend openai --mode deep --no-viz --no-cluster --token-budget 4000 --max-concurrency 2
```

For direct Anthropic it selects `--backend claude`. It passes the documented provider environment variables and retrieves `graphify-out/graph.json` or `graph.json`. The temporary corpus contains enabled non-voice text sources, not your entire computer. Native extraction then performs separate quote-linked source checking.

The relevant published package is `graphifyy`; Graphify is an independently installed, optional dependency. Choose a trusted executable. Its API usage, nested retries and any independently configured behaviour are **outside GraphPaper's request/cost accounting**. It has a 20-minute subprocess timeout; cancellation terminates the process, but cannot undo already submitted provider calls. This bridge has not been run against a live Graphify installation here.

Primary sources:
- https://github.com/Graphify-Labs/graphify
- https://docs.graphify.com

No third-party repository code is vendored in GraphPaper. The external project's licence and provider terms still apply when you install or use it.

## Desktop reference

The native shell follows pywebview's documented API. Its save-before-close callback uses `window.run_js`, avoiding `evaluate_js`'s eval dependency so GraphPaper can retain a strict Content Security Policy.

- https://pywebview.flowrl.com/api/
- https://pywebview.flowrl.com/examples/save_file_dialog.html

## Local API for future agent plugins

Each desktop session binds to an ephemeral loopback port; it is not a network-facing service. The UI uses `/api/projects`, project-specific source and graph routes, `/api/jobs`, settings and export endpoints. A session cookie and `X-GraphPaper: 1` header protect the API, with Origin/Host checks. Use the Pydantic models and route definitions as the contract. There is no claimed MCP server or installed agent plugin in this release; adding one should preserve explicit project permissions and never expose provider keys.

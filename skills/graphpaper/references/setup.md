# Headless setup

## 1. Backend environment, separate from the skill

Use an authorized GraphPaper source checkout, version 0.7.1 or newer. From that checkout:

```sh
python -m venv .venv
```

Use `.venv/bin/python` on Linux/macOS or `.venv\Scripts\python.exe` on Windows for the following commands. Activation is optional. Install the normal source requirements, **not** `requirements-desktop.txt`:

```sh
python -m pip install -r requirements.txt
```

These setup commands use the environment's selected Python. The skill must subsequently use that same environment. When copied outside the checkout, supply `--repo` or set `GRAPHPAPER_REPO`. Serving also works with an installed source package containing its UI assets. A Windows release's `_internal` folder is not a Python development environment.

Native graph extraction is available through the normal backend. To choose external Graphify in a source environment, install `requirements-graphify.txt` into an appropriate environment, set `graphify_executable` to its Graphify CLI as needed, and check `/api/graphify/status`. The Windows ZIP's bundled runtime is not automatically present in a source checkout. Do not pretend Graphify was used when native extraction was selected.

## 2. Run without a window

From the checkout, start this command using the agent host's managed background-process facility:

```sh
python skills/graphpaper/scripts/gp.py serve --repo . --data-dir /absolute/path/to/graphpaper-agent-data --port 8765
```

Use an actual user-authorized path (including a Windows path when appropriate). This command stays running. It starts FastAPI/Uvicorn with the existing store and job runner; it does not call the desktop entry point, open a browser or initialize Python.NET/WebView2. Only one process/worker is allowed. Run `doctor` from a second command:

```sh
python skills/graphpaper/scripts/gp.py doctor
```

The initial `status: starting` line is not readiness. Retry **doctor only** briefly until `ready: true`. The returned data directory must match the intended agent workspace. A port conflict calls for a different explicit port and `--url http://127.0.0.1:PORT` on subsequent client commands, not attaching to an unidentified service.

An agent-workspace marker and OS lock prevent two skill hosts opening the same workspace. A pre-existing non-agent database is refused by default. `--adopt-workspace` is reserved for explicit reuse permission, after backup and after closing the desktop. The desktop does not participate in this lock: do not run it concurrently against this directory.

Before stopping the service, finish or cancel its active jobs. Stop the exact managed process with a normal interrupt. In-memory jobs do not survive a service restart; saved projects, revisions, voices, decision receipts and accounting do. Provider calls can still be billed after cancellation. Do not kill arbitrary Python processes or delete workspace lock files to bypass a running host.

## 3. Provider setup without leaking credentials

`doctor` makes no model call. A fresh workspace has cloud processing disabled. Obtain the user's authorization for the provider, material and spending limits before enabling it. Merely installing a skill is not that authorization.

Create a local **non-secret** settings JSON using the selected provider's real model IDs. Fields include `provider`, `model`, `editor_model`, `extraction_model`, per-role `reasoning_effort` settings, `graph_engine`, `jev_provider`, `max_calls` and `refine`. `max_calls` is a per-job limit, not a whole-project price guarantee. Track the cumulative usage across jobs as well. Keep optional automatic model routing off unless alternatives were expressly approved.

```sh
python skills/graphpaper/scripts/gp.py configure --json-file settings.json --key-env openrouter=MY_WRITING_PROVIDER_KEY --key-env typesafe=MY_JEV_KEY --allow-cloud
```

Use only already provisioned environment variables; never put their values in shell arguments, the brief or the repository. Keys passed this way remain in the server session (`remember_keys=false`). Re-provision them after restarting. `configure` fetches and merges settings rather than resetting unrelated options. Raw `PUT /api/settings` replaces settings and should use the complete fetched object.

JEV can be `typesafe`, `openrouter`, `auto` or `off`; choose the authorized route explicitly. Keys for writing and JEV are separate. No key means no invented decision results. Retrieval and some metadata/model-catalog actions contact external services even though the backend itself is local.

For Codex, use `/api/codex/status` and, with authorization, `POST /api/codex/login`. Relay the returned sign-in URL to the user and poll status. Account sign-in cannot be fabricated or bypassed, and a new agent data directory has its own Codex account state. Do not copy account files from other agents. Model options are discoverable through `/api/models`; follow the actual catalog, not a hard-coded “ultra” setting.

## 4. No credentials / agent writes its own prose

The agent can create a project, import supplied material and graph JSON, read source-linked records, set its own angles/outline/draft, run deterministic craft auditing and export without a writing-provider key. It must label that route accurately: agent-authored prose and imported graph, not a completed GraphPaper model job. JEV-assisted auditing still requires its configured provider. The fully automatic GraphPaper writing jobs use its approved model connection rather than borrowing the calling agent's session implicitly.

# Connect an AI agent to GraphPaper

The GraphPaper MCP adapter lets a local agent open projects, read sources and graph records, edit drafts, apply saved author voices, run GraphPaper jobs, and export manuscripts. It uses the same workspace and project versions as the running GraphPaper app.

## 1. Start GraphPaper

To share your desktop workspace, close GraphPaper and launch the updated build from PowerShell with a fixed local port.

~~~powershell
.\GraphPaper.exe --agent-port 8765
~~~

From a source checkout with desktop dependencies installed, use `python -m graphpaper.desktop --agent-port 8765`. In **Connections & settings**, find the displayed project storage path. Use that path as `--data-dir` in the MCP configuration.

For a separate workspace, start the [headless backend](../skills/graphpaper/references/setup.md#2-run-without-a-window) with `gp.py serve --data-dir` and the same port. Point the adapter at that data directory. The desktop and headless host should use separate data directories when running at the same time.

## 2. Register the MCP server

From the GraphPaper source folder, install the MCP client dependency into the Python environment you want the agent to use. Python 3.11 or later is required. For the Windows build, the adapter scripts are in the `agent` subfolder.

~~~powershell
python -m pip install -r .\skills\graphpaper\scripts\requirements-mcp.txt
~~~

For a Windows build, use `.\agent\requirements-mcp.txt`. In your agent’s local MCP settings, register a stdio server with the absolute Python executable and script paths. Replace the example paths with yours.

~~~json
{
  "mcpServers": {
    "graphpaper": {
      "command": "C:/Tools/graphpaper-agent/Scripts/python.exe",
      "args": [
        "C:/Tools/GraphPaper/skills/graphpaper/scripts/graphpaper_mcp.py",
        "--url", "http://127.0.0.1:8765",
        "--data-dir", "C:/Users/You/AppData/Local/GraphPaper",
        "--export-dir", "C:/Users/You/Documents/GraphPaper Exports"
      ]
    }
  }
}
~~~

Use `agent/graphpaper_mcp.py` for the script path in the Windows build. For clients that use TOML, put the same `command` and `args` values under `[mcp_servers.graphpaper]`. Restart or reload your MCP client, then ask it to list your GraphPaper projects.

## 3. Use it in a writing task

> Open my polemic in GraphPaper. Read the brief and the sources cited in the draft. Flag any mismatches before changing the prose. Save a Word copy when the citations are ready.

- Start with `list_projects`. Use `read_project` to inspect the draft, outline, angles, sources, graph, or editorial review. Use `read_source` for the underlying passage.
- Use the latest version returned by `read_project` for edits. If GraphPaper reports a conflict, reconcile the draft with the newer version before saving again.
- Use `start_job` only for authorized model actions, then poll `job_status` with the returned ID. GraphPaper uses its configured provider and account for those actions.
- Use `export_manuscript` to save PDF, Word, or other supported exports to the configured folder. A filename stem like `my-article` creates `my-article.pdf` for a PDF export. Pick a new name if the file already exists.

The adapter connects to `127.0.0.1` and checks the expected workspace. When you start the desktop with `--agent-port`, GraphPaper writes a fresh connection token inside its data directory. The adapter reads it automatically. Use a private workspace folder and register GraphPaper with clients you trust with its writing and sources.

Add `--read-only` to expose inspection tools only. Omit `--export-dir` to leave file exports unavailable. These settings control what the MCP server offers the client. Use the [agent skill](../skills/README.md) for file uploads and backend setup.

"""Use the official MCP client over stdio against a real loopback backend."""

import asyncio
from pathlib import Path
import socket
import sys
from threading import Thread
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import pytest
import uvicorn

from .conftest import ScriptedClients
from graphpaper.models import Settings
from graphpaper.desktop import server_config, write_agent_token
from graphpaper.server import create_app


SCRIPT = Path(__file__).resolve().parents[1] / "skills/graphpaper/scripts/graphpaper_mcp.py"


@pytest.fixture
def loopback(app, request):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        root = app.state.store.root
        if getattr(request, "param", False):
            host = create_app(root, agent_token=write_agent_token(root, port))
        else:
            host = app
        host.state.runner.clients_factory = ScriptedClients
        host.state.store.set_settings(Settings(model="test/model", allow_cloud=True, refine=False).model_dump())
        server = uvicorn.Server(server_config(host, log_level="error"))
        thread = Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.02)
            assert server.started
            yield f"http://127.0.0.1:{port}"
        finally:
            server.should_exit = True
            thread.join(10)
            assert not thread.is_alive()
            if host is not app:
                host.state.runner.pool.shutdown(wait=True, cancel_futures=True)


def parameters(url, root, *options):
    return StdioServerParameters(
        command=sys.executable,
        args=[str(SCRIPT), "--url", url, "--data-dir", str(root), *options],
    )


@pytest.mark.parametrize("loopback", [False, True], indirect=True, ids=["headless", "desktop-token"])
def test_agent_edits_graphpaper_and_exports_pdf(app, loopback, tmp_path):
    async def flow():
        destination = tmp_path / "exports"
        config = parameters(loopback, app.state.store.root, "--export-dir", str(destination))
        async with stdio_client(config) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            tools = {tool.name: tool for tool in (await session.list_tools()).tools}
            assert tools["list_projects"].annotations.readOnlyHint
            assert "run_command" not in tools

            async def call(tool, **arguments):
                result = await session.call_tool(tool, arguments)
                assert not result.isError, result.content
                return result.structuredContent

            created = await call("create_project", title="Agent draft", mode="polemic")
            project_id = created["id"]
            assert (await call("list_projects"))["projects"][0]["id"] == project_id
            added = await call("add_source_text", project_id=project_id, title="Evidence",
                               text="One distinctive verified passage.")
            source_id = added["source"]["id"]
            assert (await call("read_source", project_id=project_id, source_id=source_id))["text"] == "One distinctive verified passage."
            stale_job = await session.call_tool("start_job", {
                "project_id": project_id, "version": created["version"], "action": "graph",
            })
            assert stale_job.isError and "409" in str(stale_job.content)
            job = await call("start_job", project_id=project_id, version=added["version"], action="graph")
            for _ in range(120):
                status = await call("job_status", job_id=job["id"])
                if status["state"] not in {"queued", "running"}:
                    break
                await asyncio.sleep(0.05)
            assert status["state"] == "completed", status
            current = await call("read_project", project_id=project_id)
            assert current["graph_nodes"] > 0
            draft = f"An argument. [{source_id}]"
            await call("update_project", project_id=project_id, version=current["version"], draft=draft)
            conflict = await session.call_tool("update_project", {
                "project_id": project_id, "version": current["version"], "draft": "Stale edit",
            })
            assert conflict.isError and "409" in str(conflict.content)
            assert (await call("read_project", project_id=project_id, view="draft"))["draft"] == draft

            result = await call("export_manuscript", project_id=project_id, format="pdf", name="essay")
            file = Path(result["path"])
            assert file == destination / "essay.pdf" and file.read_bytes().startswith(b"%PDF")
            for name in ("essay", "../elsewhere"):
                refused = await session.call_tool("export_manuscript", {
                    "project_id": project_id, "format": "pdf", "name": name,
                })
                assert refused.isError

    asyncio.run(flow())


def test_adapter_refuses_wrong_workspace_and_hides_mutations_in_read_only_mode(app, loopback, tmp_path):
    async def flow():
        config = parameters(loopback, tmp_path / "different", "--read-only")
        async with stdio_client(config) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            names = {tool.name for tool in (await session.list_tools()).tools}
            assert {"list_projects", "read_project", "read_source"} <= names
            assert not {"create_project", "update_project", "start_job", "export_manuscript"} & names
            result = await session.call_tool("list_projects")
            assert result.isError and "workspace" in str(result.content)
        assert app.state.store.list() == []

    asyncio.run(flow())

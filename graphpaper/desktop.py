"""Native desktop entry point. Windows uses Edge WebView2; no public server."""
from __future__ import annotations

import argparse
import logging
import re
import socket
import sys
import threading
import time
from pathlib import Path

from .export import export
from .server import create_app
from .storage import data_directory


def server_config(app, **options):
    """Windowed Python has no stdout/stderr. Never configure console formatters."""
    import uvicorn
    return uvicorn.Config(app, log_config=None, **options)


class DesktopBridge:
    """Small explicit bridge: export only through an OS save dialog."""
    def __init__(self, store, runner=None):
        self.store = store
        self.runner = runner
        self.window = None
        self.ui_ready = False
        self.close_authorized = False

    def notify_ready(self):
        self.ui_ready = True
        return True

    def request_close(self):
        """Called by our UI only after its pending saves have completed."""
        active = self.runner and any(j.state in {"queued", "running"} for j in self.runner.jobs.values())
        if active and not self.window.create_confirmation_dialog(
            "AI job running", "Close and cancel this job? An in-flight provider request may still finish and be billed. Saved checkpoints remain available."
        ):
            return {"closed": False}
        self.close_authorized = True
        self.window.destroy()
        return {"closed": True}

    def save_export(self, project_id: str, kind: str):
        try:
            import webview
            if kind not in {"md", "docx", "html", "json", "graph"}:
                return {"error": "Unknown export type"}
            p = self.store.get(project_id)
            data, _, ext = export(p, kind)
            stem = re.sub(r'[^\w\s.-]', '', p.title).strip()[:80] or "GraphPaper"
            result = self.window.create_file_dialog(
                webview.FileDialog.SAVE, save_filename=stem + ext,
                file_types=(f"{kind.upper()} files (*{ext})", "All files (*.*)"),
            )
            if not result:
                return {"saved": False}
            filename = result if isinstance(result, str) else result[0]
            path = Path(filename)
            if not path.suffix:
                path = path.with_suffix(ext)
            path.write_bytes(data)
            return {"saved": True}
        except Exception:
            logging.exception("Export failed")
            return {"error": "Could not save the export. Check the destination and whether the file is open in another application."}


def run(browser: bool = False):
    import uvicorn
    root = data_directory()
    root.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=str(root / "desktop.log"), level=logging.WARNING)
    app = create_app(root)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Keep the ephemeral listener open until handed to uvicorn (no port-selection race).
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    config = server_config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(.05)
    if not server.started:
        raise RuntimeError("GraphPaper's local application service could not start.")
    url = f"http://127.0.0.1:{port}/"

    def cleanup():
        for job in list(app.state.runner.jobs.values()):
            job.cancel.set()
        app.state.runner.pool.shutdown(wait=False, cancel_futures=True)
        server.should_exit = True
        thread.join(timeout=4)
        sock.close()

    if browser:
        # Optional developer fallback; Windows users normally launch the native window.
        import webbrowser
        webbrowser.open(url)
        try:
            while thread.is_alive():
                time.sleep(.5)
        except KeyboardInterrupt:
            pass
        finally:
            cleanup()
        return
    try:
        import webview
        # Keep CSP strict. run_js below does not use eval; evaluate_js would.
        webview.settings["ALLOW_FILE_URLS"] = False
        webview.settings["ALLOW_DOWNLOADS"] = False
        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
        bridge = DesktopBridge(app.state.store, app.state.runner)
        window = webview.create_window(
            "GraphPaper — a studio for connected thought", url=url,
            js_api=bridge, width=1440, height=940, min_size=(940, 650),
            background_color="#101714", text_select=True,
        )
        bridge.window = window

        def closing():
            if bridge.close_authorized or not bridge.ui_ready:
                return True
            try:
                # The JS -> Python callback completes an async save handshake.
                # Do not use evaluate_js: its eval wrapper conflicts with CSP.
                window.run_js("window.graphpaperRequestClose()")
                return False
            except Exception:
                return window.create_confirmation_dialog(
                    "Close GraphPaper?", "The editor could not confirm its save state. Close anyway? Unsaved text may be lost."
                )

        window.events.closing += closing
        webview.start(gui="edgechromium" if sys.platform == "win32" else None, debug=False, private_mode=True)
    finally:
        cleanup()


def self_test(output):
    """Check the frozen backend and bundled UI without claiming to test WebView2."""
    import json
    import tempfile
    import urllib.request
    import uvicorn
    with tempfile.TemporaryDirectory(prefix="graphpaper-package-test-") as temp:
        app = create_app(Path(temp))
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        server = uvicorn.Server(server_config(app, log_level="error"))
        t = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
        t.start()
        try:
            for _ in range(200):
                if server.started:
                    break
                time.sleep(.05)
            checks = {}
            for path in ["/health", "/", "/static/app.js", "/static/styles.css"]:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=10) as r:
                    body = r.read()
                    checks[path] = {"status": r.status, "bytes": len(body)}
            Path(output).write_text(json.dumps({"ok": all(v["status"] == 200 and v["bytes"] > 0 for v in checks.values()), "checks": checks}), encoding="utf-8")
        finally:
            server.should_exit = True
            t.join(timeout=4)
            sock.close()
            app.state.runner.pool.shutdown(wait=True)


def main():
    parser = argparse.ArgumentParser(description="GraphPaper desktop studio")
    parser.add_argument("--browser", action="store_true", help="Developer fallback: open the local studio in a browser")
    parser.add_argument("--self-test", metavar="OUTPUT_JSON", help="Packaging check: backend/assets only; no AI calls")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.self_test)
        return
    try:
        run(args.browser)
    except Exception as e:
        logging.exception("GraphPaper could not start")
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk(); root.withdraw()
            messagebox.showerror("GraphPaper could not open", f"{e}\n\nOn Windows, install Microsoft Edge WebView2 Runtime.\nDetails are in GraphPaper's local desktop.log.")
            root.destroy()
        except Exception:
            print(f"GraphPaper could not start: {e}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

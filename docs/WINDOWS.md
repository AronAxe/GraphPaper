# Windows guide

## The source edition: a graphical first run

Extract the full folder. Double-click **Open GraphPaper.vbs**, then **Install and open**. The launcher uses windowed Python, so no console is part of the everyday workflow.

Prerequisites are Windows 10/11, Python 3.11+ with Tcl/Tk, and Edge WebView2 Runtime. Python 3.12/3.13 is recommended for the source edition; compatibility with every newer Python/dependency combination has not been tested. Obtain Python from https://www.python.org/downloads/windows/ and WebView2 from https://developer.microsoft.com/microsoft-edge/webview2/ .

The script discovers normal per-user Python installations and the Python launcher. A custom installation can open `GraphPaper.pyw` with `pythonw.exe` using Windows **Open with**. If your computer blocks VBScript by policy, use that `.pyw` route; do not disable security policy.

Setup downloads dependencies into `%LOCALAPPDATA%/GraphPaper/runtime/pyXY`. It does not change the global Python environment. The requirements fingerprint is saved so unchanged dependencies are not reinstalled every launch. Internet is needed for first setup. Provider access is a separate configuration step.

## Inside the app

**Connections & settings** is where API keys and models belong. Choose OpenRouter, paste the key, load its model list and choose the writer. An optional editorial model can be different from the writer. The extraction model should be good at structured JSON and precise quotation.

For JEV, Auto uses the OpenRouter key when available, then direct TypeSafe. Enter the TypeSafe key for that fallback, or choose the direct route explicitly. Use the connection tests before a substantial run; these tests can make billable requests.

Cloud calls stay disabled until you enable them. An OpenAI-compatible localhost model can be used without cloud permission; choose its base URL and model explicitly.

## Files and recovery

The application directory can live anywhere writable; your work is separate:

- `%LOCALAPPDATA%/GraphPaper/studio.sqlite3`: projects, source text, settings, extraction cache, revision history.
- `credentials.dpapi`: encrypted keys tied to the Windows account/machine.
- `setup.log` and `desktop.log`: local diagnostics, not included in project exports.

Use **Export → Project backup** to move a current project. It includes its source text, graph, angle, outline and current draft, but not credentials or the entire revision database. For a full history backup, close GraphPaper and copy its local data folder. Do not move a Windows-encrypted credentials file expecting it to decrypt under a different account.

`Ctrl+S` saves the editor. Normal typing autosaves. Closing the native window asks the interface to finish saving first. Revisions are kept; a concurrent edit conflict does not silently overwrite the new text. Cancelling a model job retains completed draft checkpoints in version history.

## Portable executable build

After the source is on GitHub's default branch, use **Actions → Windows desktop package → Run workflow**. When that job succeeds, download its `GraphPaper-Windows-x64` artifact. Extract the entire app folder and run `GraphPaper.exe`; its companion `_internal` directory must stay with it.

The workflow bundles Python with PyInstaller, includes the interface, runs tests and probes the frozen backend/assets. It does **not** certify the visual WebView2 experience. Before public release, test launch, file dialogs, save/close and credentials on a real Windows computer. An unsigned build may trigger SmartScreen; do not treat an unverified binary as inherently trusted.

The original delivered archive is source, not a compiled artifact. Consult the actual Actions run for the build's status.

## Troubleshooting

**Nothing opens:** verify Python/Tcl-Tk and use `.pyw` if VBScript is blocked. Check `setup.log`.

**A WebView error:** install/repair Edge WebView2 Runtime and try again; inspect `desktop.log`.

**Model not found:** refresh the model list or enter an ID supported by your selected provider. Model availability is not frozen in GraphPaper.

**Context/output limit:** use a suitable long-context model, reduce the target length or adjust the explicit limits. Truncated output is treated as an error rather than silently installed as a complete article.

**Cloud processing disabled:** enable it only after deciding the source material can be shared with the selected providers.

**Source import has little text:** scanned/image-only PDFs need external transcription/OCR. This edition does not silently guess at unreadable images.

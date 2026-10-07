# Windows installation and upgrades

## Portable Windows release

Get the Windows x64 ZIP from [Releases](https://github.com/AronAxe/GraphPaper/releases/latest). Extract everything, then run `GraphPaper.exe` with its `_internal` directory beside it. Do not launch from inside the ZIP viewer or move the executable by itself.

The package includes Python and the official Codex runtime. The native interface uses Microsoft Edge WebView2. Windows 10/11 x64 is the intended desktop target; recorded native validation was performed on Windows 11. The build is unsigned.

Use the publisher’s official sources for prerequisites:

- [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/)
- [GitHub release assets and SHA256SUMS](https://github.com/AronAxe/GraphPaper/releases/latest)

A SmartScreen warning about an unsigned binary is not a validation result. Check the repository, release asset and checksum rather than disabling security software. The checksum verifies the downloaded bytes match the release record; it is not a code-signing certificate.

## Upgrade without resetting your work

1. Close the running GraphPaper instance. If an old faulty version is hung, end only its process in Task Manager.
2. Extract the new ZIP into a **new folder**. Do not mix `_internal` files from different versions.
3. Open the new `GraphPaper.exe`.

The executable folder is separate from the normal data directory, `%LOCALAPPDATA%\GraphPaper`. Existing projects, revisions, settings and credentials are not overwritten by extracting a new application. Back up important work before upgrading.

The native bridge and save-on-close corrections introduced in 0.2.1 remain in 0.3.0. Use the latest release rather than the affected 0.2.0 executable.

## Source edition

The source ZIP is intended for people who want the code or need to run it directly. It requires **Python 3.11+ with Tcl/Tk**; Python 3.12 or 3.13 is the conservative choice for the desktop dependency set.

Extract the complete repository and double-click **Open GraphPaper.vbs**. The first-run setup window offers **Install and open**. It downloads dependencies into a private environment under `%LOCALAPPDATA%\GraphPaper\runtime`, rather than modifying the global Python installation.

If Windows policy blocks VBScript, open `GraphPaper.pyw` with a trusted `pythonw.exe` installation instead. Do not disable your organization’s security policy. Python is available from the [official Windows downloads page](https://www.python.org/downloads/windows/).

Normal compiled-release users do not need the `.vbs` launcher, the optional publisher or Git.

## Where to look when startup fails

| Symptom | First check |
|---|---|
| Executable cannot find bundled files | Re-extract the whole release; keep `_internal` beside it. |
| WebView initialization error | Install or repair the official WebView2 Runtime. |
| Source launcher does nothing | Check Python/Tcl-Tk, file association and `setup.log`; use `.pyw` if VBScript is blocked. |
| Window freezes or will not close | Confirm the version, use the corrected release and inspect `desktop.log`. |
| Updated application appears to have old behavior | Confirm you launched the new folder, not an old shortcut. |

The normal log directory is `%LOCALAPPDATA%\GraphPaper`. Logs may contain diagnostics; inspect them before sharing. Do not upload the full data directory or credential files to an issue.

For model, import and manuscript problems, continue with [Troubleshooting](TROUBLESHOOTING.md). For developer builds and native checks, see [Releases and packaging](PUBLISHING.md).

## External Graphify in 0.3.1

The 0.3.1 Windows package includes the public Graphify runtime and its dependencies. No separate Graphify installation is required. Clear an old custom executable path to select the included runtime; custom paths are never silently overridden. [Detailed setup and distribution](UPDATE-0.3.1.md).

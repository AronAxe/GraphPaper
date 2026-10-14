# GraphPaper 0.7.1 — Windows downloaded-runtime startup fix

Addresses the reproduced **Failed to resolve Python.Runtime.Loader.Initialize** startup failure caused by Windows Internet-zone marks on bundled DLLs. The previous native tests exercised build files, not this downloaded-file condition.

- Checks exact bundled DLL paths and embedded per-build hashes before loading the Python/.NET bridge.
- Shows **GraphPaper runtime permission** only when affected files carry an Internet/Restricted-zone mark. Choose Yes only if you trust your downloaded release; No leaves the marks in place and cancels startup.
- Removes only the listed runtime DLL marks, never project files, unrelated DLLs, or system-wide security policy. Incorrect or mixed DLLs are not unblocked.
- Gives error-specific startup advice rather than recommending WebView2 for every error.
- Tests a fresh extraction of the actual release ZIP with simulated DLL Internet-zone marks, both native consent choices, and the full native graph, Science, Polemic, voice and System One workflows. This does not simulate SmartScreen or all antivirus/policy configurations.

## Install

Extract the complete ZIP into a **new folder** and open **GraphPaper.exe** with `_internal` beside it. Approve the scoped runtime dialog when shown and when you trust the release. Keep the existing project data directory. No graph rebuild or voice retraining is needed.

The System One decision studio from v0.7.0 is retained. This patch changes startup/distribution handling, not your writing policy, models, prompts or project data. All release tests use isolated GitHub-hosted machines and synthetic project/model fixtures, not a user's computer or private manuscripts.

[Windows startup details](https://github.com/AronAxe/GraphPaper/blob/main/docs/WINDOWS.md#downloaded-runtime-permission)

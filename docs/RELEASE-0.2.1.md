# GraphPaper 0.2.1 ? Windows interface freeze fix

This is a corrective release for the Windows interface in 0.2.0. It retains
all author-voice, project-folder, prose-editing and Codex sign-in features.

## Fixed

- Restricted the Python/JavaScript bridge to four explicit methods. Its store,
  job runner and native window are now private and cannot be recursively
  reflected into the browser API. Native testing of the old bridge produced
  recursion-limit and wrong-thread COM/WebView2 errors while API initialization
  failed to finish.
- Fixed a second native deadlock on closing: the WinForms closing handler now
  returns immediately and performs the save handshake on a worker, rather than
  waiting for JavaScript while holding the UI event loop.
- Failed saves and declined close prompts reset the handshake so closing can be
  retried. The original manuscript is not discarded to make the window close.

## Windows download

Extract **GraphPaper-v0.2.1-Windows-x64.zip** into a new folder and open
**GraphPaper.exe**. Keep its `_internal` companion folder. No Python installation
is needed. Close the old executable first. Existing projects and credentials
remain in the same local data directory; this patch does not reset them.

## Native regression coverage

The new `scripts/native_smoke.py` launches the actual Windows/WebView2 shell in
an isolated temporary project directory. It sends a genuine Windows mouse click,
checks the restricted bridge and its returned promise, creates a project, types
in the editor, opens Connections, opens and cancels a native Save As dialog, and
sends the Windows close message before autosave's delay expires. It then verifies
that the pending manuscript was written and the process exited normally.

It runs against source and the compiled executable. This is not the browser-only
or HTTP-startup check used in previous releases. The release workflow now requires
the compiled native regression before uploading its Windows artifact.

126 automated Windows tests passed; one symlink-permission test was skipped.
Native test reports are recorded with this release after the packaged run.
No live model request or OAuth login is part of these tests. The binary remains
unsigned. SHA256SUMS.txt records the exact downloadable ZIP checksum.

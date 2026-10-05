## GraphPaper 0.2.0

A Windows writing studio for fiction and nonfiction, now with:

- **Your writing voice:** upload samples, paste writing, or discover and selectively import articles from your author/blog URL; learn an editable style profile with adjustable influence.
- **Project folders:** a local Inbox per project, automatic idle-time import, role-specific subfolders and original upload files.
- **Humanizer and deslopping:** separate or combined editing passes, explainable local inspection, protected factual spans, side-by-side proposals, diffs and explicit acceptance.
- **Codex / ChatGPT sign-in:** use your account allowance instead of a writing API key; official runtime included, with browser OAuth handled by Codex. Other API providers remain available. JEV is a separate optional connection.

### Windows

Download **GraphPaper-v0.2.0-Windows-x64.zip**, extract the complete folder and open **GraphPaper.exe**. No separate Python installation or terminal workflow is needed. Keep the `_internal` companion folder. Edge WebView2 must be available. The build is unsigned.

The SHA256SUMS file records the package checksum. The bundled Codex runtime has its own version, download URL and SHA-256 provenance in `_internal/vendor/codex-release.json`.

### Quality and limits

The build process runs automated tests, browser workflows and actual Windows package checks. Model responses in tests use controlled fixtures. The official runtime is checked while signed out; a real user's OAuth ceremony and live prose generation cannot be completed by CI. Inspect claims, citations and proposed edits before publishing.

Existing projects load with defaults for the new features. User data stays in the existing local GraphPaper data directory; extracting the new executable does not replace your project database.

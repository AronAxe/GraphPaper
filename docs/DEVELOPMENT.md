# Development and contributing

GraphPaper uses a Python backend and a bundled HTML/CSS/JavaScript interface. Ordinary Windows users should use the [compiled release](https://github.com/AronAxe/GraphPaper/releases/latest); this guide is for contributors.

## Set up a source environment

Use Python 3.11 or newer; the existing test/build workflows target Python 3.12/3.13. Work in an isolated environment.

```bash
python -m venv .venv
```

Activate it using the command appropriate to your shell, then install the test dependencies:

```bash
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
```

For a native desktop run, also install `requirements-desktop.txt`. For development only, `python -m graphpaper.desktop --browser` opens the local service in a browser. Native Windows regressions require the Windows desktop dependencies and WebView2.

Set `GRAPHPAPER_DATA_DIR` to an isolated temporary directory before experimenting with storage or migrations. Never run destructive test work against an author’s real database.

## Find the relevant layer

Read [Architecture](ARCHITECTURE.md) before changing cross-cutting behavior. Shared Pydantic models define the persisted state; route modules validate user actions; the job runner handles long operations and usage accounting. Provider clients should not be given unrestricted file or shell access.

The interface is shipped from `ui/`. It must work without remote scripts or CDN fonts. Preserve escaping, source-role separation and the restrictive Content Security Policy.

## Run the tests

```bash
python -m pytest -q
python scripts/ui_smoke.py
python scripts/ui_studio_smoke.py
python scripts/ui_science_smoke.py
```

On Windows, test the actual shell as well:

```text
python scripts/native_smoke.py --science --out test-results/native-source
python scripts/native_smoke.py --science --executable dist/GraphPaper/GraphPaper.exe --out test-results/native-package
```

The second command requires a compiled package. It is a desktop-interaction test, not a substitute for a live model/OAuth test. See [Validation](QUALITY.md) for what each suite establishes.

`python scripts/check_scholarly.py` is an **opt-in live network** check against public research services. It does not use an LLM to invent search results. Keep its failures and rate-limit observations in the report rather than hard-coding success.

## Changes that need particular care

**Native bridge:** only explicit RPC methods may be public. Exposing a native Window or store object caused recursive COM reflection in an earlier release. Close handlers must not wait for JavaScript while blocking the Windows UI thread.

**Evidence and references:** exact quotes establish attribution, not truth. Do not accept a voice sample as factual evidence or convert imported graph confidence into a verified claim. Scientific references must remain linked to actual metadata.

**Provider requests:** keep reasoning levels provider-native and model-aware. Do not silently fall back from Codex OAuth to API billing, invent unreported cost, or retry an ambiguous timed-out request as though it was free.

**State and editing:** preserve optimistic revisions, draft checkpoints, stale-proposal checks and manuscript-specific scientific confirmations. A passing unit test does not justify overwriting a newer draft.

**Filesystem and exports:** preserve size/path checks, safe URL fetching, source identity and formula-safe CSV output. Treat project backups and logs as potentially confidential.

## Maintaining the documentation

The maintained pages live under `docs/`; [the documentation index](README.md) is the user entry point. `docs/wiki-pages.json` maps those pages to wiki titles. The wiki is generated from the same content, with relative links translated and a consistent sidebar/footer.

Validate the repository documentation and render a local wiki copy:

```bash
python scripts/docs_tool.py check
python scripts/docs_tool.py render-wiki --output test-results/wiki-preview
```

Publishing is explicit and requires an initialized wiki plus authorized Git access:

```bash
python scripts/docs_tool.py publish-wiki
```

The publisher updates only its managed Markdown pages, never force-pushes and refuses to discard independently edited generated pages without reconciliation. Its separate wiki-manifest records the generated content. The wiki’s first page must exist on GitHub before its Git repository is available; [GitHub’s wiki instructions](https://docs.github.com/en/communities/documenting-your-project-with-wikis/adding-or-editing-wiki-pages) describe that one-time initialization.

Preserve user artwork and verify its path/hash when reorganizing README content. Prefer dynamic badges for changing repository status; do not replace CI state with an unconditional green badge. Keep historical release notes separate from the current installation guide.

## Submit a contribution

Open a focused issue or pull request explaining the user-visible behavior, the change and the checks you actually ran. Include a non-confidential reproduction when useful. Do not commit runtime binaries, test environments, credentials, manuscript databases or real private source documents.

For application releases, continue with [Packaging](PUBLISHING.md). For sensitive disclosures, use a private route to the maintainer and read [Security](SECURITY.md).

## External Graphify in 0.3.1

The full developer/test requirements include the public pinned Graphify distribution. Run `python scripts/prepare_graphify.py` for tokenizer/licence assets, `python scripts/check_graphify.py` for an isolated real-worker test with synthetic inference, and `python scripts/ui_graphify_smoke.py` for its graphical workflow. Windows builds also test the frozen worker. Opt-in live Codex testing is documented in the check script and requires an explicitly selected existing official account profile. [Detailed setup and distribution](UPDATE-0.3.1.md).

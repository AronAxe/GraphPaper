# Contributing to GraphPaper

Contributions should make the final article or story better, preserve the author's work, or make the application easier to understand and use.

Start with the [developer guide](docs/DEVELOPMENT.md), [architecture](docs/ARCHITECTURE.md) and [validation scope](docs/QUALITY.md). For a reproducible bug, include the version, edition, exact steps and a small non-confidential example. State which checks were run rather than implying live-model validation from a fixture test.

Keep pull requests focused. Preserve source-role separation, secure credentials, optimistic saves, private native bridge state and honest provider accounting. Never commit private manuscripts, API keys, Codex account files or build environments.

Documentation changes belong in the maintained `docs/` pages; the wiki is generated from the same source. Run `python scripts/docs_tool.py check` before submitting. User artwork and headers should remain intact unless their owner requested a change.

Use [Issues](https://github.com/AronAxe/GraphPaper/issues) for ordinary defects and proposals. Handle security-sensitive disclosures privately as described in [Security](docs/SECURITY.md).

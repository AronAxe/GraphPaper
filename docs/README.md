# GraphPaper documentation

**Connect your sources. Find your angle. Write in your own voice.**

These guides cover **GraphPaper 0.6.0**: the ink-blue studio, real graph-paper sidebar, spatial graph editor, four writing modes and reusable voice graphs. [Download for Windows](https://github.com/AronAxe/GraphPaper/releases/latest) · [See the interface](VISUAL-TOUR.md) · [Version history](../CHANGELOG.md).

## Start here

| You want to… | Read |
|---|---|
| See the real application before installing | [Visual tour](VISUAL-TOUR.md) |
| Finish a first project | [Getting started](GETTING-STARTED.md) |
| Install or upgrade without losing work | [Windows installation](WINDOWS.md) |
| Choose models, Codex sign-in and reasoning depth | [Models and reasoning](CONNECTIONS.md) |
| Get a quick answer about graphs, voices or costs | [Frequently asked questions](FAQ.md) |

## Choose your writing workflow

| Mode | Purpose | Guide |
|---|---|---|
| Nonfiction | Develop a source-linked article or essay; argue a case or investigate a question | [Nonfiction workflow](NONFICTION.md) |
| Polemic | Defend your thesis with conviction, wit and your chosen rhetorical force | [Polemic and authorial intent](POLEMIC.md) |
| Fiction | Build characters, scenes and consequences while preserving canon | [Fiction workflow](FICTION.md) |
| Science | Search scholarly databases, screen evidence and prepare an APA manuscript | [Science workflow](SCIENCE.md) |

**Sources → Graph → Angles → Outline → Write.** Science adds a Research desk. In an existing project, **current mode · Change** switches writing mode without deleting the sources, graph, voice or manuscript. Review the brief and refresh affected generated work afterward.

## Work with your material

| Guide | Covers |
|---|---|
| [Projects and sources](PROJECTS-AND-SOURCES.md) | Uploads, source roles, project Inbox, local storage and backups |
| [Spatial graph studio](GRAPH-STUDIO.md) | 3D/2D, orbit/pan/zoom, density, connection styles, node/edge editing and undo |
| [Graph exploration and JEV](GRAPH-AND-JEV.md) | Extraction, Graphify, evidence status, paths, pins and bounded typed decisions |
| [Reusable voice graphs](VOICE-GRAPHS.md) | Save a voice once, train separately, edit its graph, reuse it and inspect overlays |
| [Author voice and prose tools](VOICE-AND-PROSE.md) | Style direction, Humanize, Deslop, comparison and explicit acceptance |
| [Exports and APA](EXPORTS-AND-APA.md) | Word, Markdown, HTML, project backups and scientific export packages |

## Try it without model calls

Open **The city after dark**, the included illustrative example. Explore the Graph tab: drag the background to orbit, Shift-drag to pan, and scroll to zoom. Click a node or connection to inspect and edit it. Try **Focus here**, then **Reset filters**. Manual graph editing does not call a model.

Next, open Angles, edit a thesis and explore Outline and Write. These are your editorial decisions. Model calls start only when you explicitly run a generation or analysis action.

For an existing learned voice, use **Your writing voice → Save as reusable voice**. In another project, choose it in **My voices → Use in this project**. Saving the existing profile and applying it require no retraining or model request.

## Upgrade notes for existing projects

The visual redesign does **not** require rebuilding graphs or re-uploading sources. Saved voices are independent of the article evidence. Your current instructions override saved style defaults; rhetorical force is separate from evidence detail.

Source changes may require a graph rebuild. Brief, mode or voice changes instead call for refreshing affected angles or outlines using the existing graph. [Recovery and common problems](TROUBLESHOOTING.md).

## Reference and maintenance

[Privacy and security](SECURITY.md) · [Troubleshooting](TROUBLESHOOTING.md) · [Architecture](ARCHITECTURE.md) · [Integration reference](INTEGRATIONS.md) · [Development](DEVELOPMENT.md) · [Validation](QUALITY.md) · [Releases and packaging](PUBLISHING.md).

The repository's `docs/` files are the maintained source for this wiki. Navigation, internal links and images are rendered from the same content. The publishing process checks for independent wiki edits rather than silently replacing them. Historical release notes remain available and are labelled by version.

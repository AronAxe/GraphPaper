# Graph Atlas

GraphPaper 0.6 replaces the cramped graph canvas with an editable spatial view and an ink/indigo workspace. The sidebar uses an actual scanned sheet of squared graph paper, bundled locally. It is not the earlier generated mockup.

## Explore without a wall of labels

Open an existing project and choose **Graph**. There is no extraction, model call or graph rebuild required for the new view. Drag the background to orbit; Shift-drag or middle-drag to pan; scroll to zoom. Drag individual nodes to arrange them for the current session. **2D** returns to a flat view. **Fit graph** or the overview inset recenters the scene. The expand button gives the graph most of the window.

The scene uses real x/y/z positions and perspective projection into accessible SVG, not a raster picture and not a WebGL dependency. It does not continuously simulate or rotate when idle. Camera and spacing preferences are remembered per project; manually dragged node positions are session-local.

Node colors and shapes identify ideas, claims, sources, evidence, people, events and other types. Connections have their own colors, line patterns and arrowheads. The legend distinguishes support, challenge, citation, sequence/cause, analogy/style and other relationships. These are visual groupings of existing relation labels, not newly inferred evidence. Select a line to see its exact label and direction.

Large graphs initially open as expandable **Clusters**, grouped using existing community/type information. The overview counts all represented nodes. Click a cluster to enter it. Select an idea and choose **Focus neighborhood** for its direct connections, or choose a two-hop view. Type and relationship filters narrow the scene. Search runs over the full stored graph, not only the initial visible nodes. When an individual view exceeds 500 nodes or 2,000 connections, the counts make that visible; use clustering, search or focus to inspect the rest.

**Layout & readability** contains spacing and smart/all/hidden label controls. Smart labels avoid overlapping labels while keeping the selected neighborhood readable. Keyboard users can Tab through nodes and lines, press Enter to select, use arrow keys to orbit, +/- to zoom, F to fit and 2/3 to switch views. The inspector also provides a text-based node browser.

## Click and edit

Select a node to edit its title, type and notes. Select a relationship to edit its label and notes, reverse its direction, or delete it. The toolbar adds nodes and connects existing nodes. Press **Save changes** to persist the edit. Unsaved form changes are identified; switching the selected item asks before discarding them.

Manual edits use a version-checked API. They preserve source files, exact quotation anchors, manuscripts, voices, outlines and existing angles. An edited relationship or claim is labeled **proposed**, rather than falsely retaining a sourced verification stamp. This is provenance bookkeeping, not a language filter. The graph editor does not weaken an author's wording or call a model.

**Undo last graph edit** restores the previous graph in one atomic operation, including the affected pins/exclusions. This one-step undo is stored locally and survives reopening the app. It refuses to overwrite an intervening rebuilt/imported graph. Deleting a node also deletes its incident connections; original sources and writing remain intact.

## What stays the same

Codex OAuth, model/reasoning controls, public Graphify extraction, reusable voice graphs, bounded JEV decisions, Polemic and Science remain available. This update changes the interface and adds explicit manual graph editing, not the authorial instructions or evidence pipeline. Tests use disposable projects, not a user's installed database.

[Graph and JEV](GRAPH-AND-JEV.md) · [Reusable voices](VOICE-GRAPHS.md) · [Asset credits](ASSET-CREDITS.md)

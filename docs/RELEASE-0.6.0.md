# GraphPaper 0.6.0 — Ink, paper & the spatial graph studio

## Actual interface changes

- **No more green wash:** charcoal/ink-blue surfaces, clearer contrast and spectral accents throughout the studio.
- **Real graph paper in the sidebar:** a bundled, credited scan by Calsidyrose (CC BY 2.0), not a generated mockup or a green CSS grid. Works offline.
- **Spatial 3D graph:** perspective XYZ layout, orbit, pan, zoom, node dragging, a minimap, expanded view and a one-click 2D view. Dependency-free SVG rendering; no WebGL requirement or model calls.
- **Less visual congestion:** display budgets, full-graph search, node/connection filters, one-/two-hop focus, spacing controls and adaptive labels. Hidden nodes are not deleted.
- **Readable connections:** colored/patterned directed links, a relationship legend and selectable connections; distinct node shapes as well as colors.
- **Edit what you click:** node title/type/notes, connection endpoints/relationship/notes, add/connect/delete dialogs, confirmation, unsaved-edit guards and persistent graph-only undo. Original sources, manuscript and voice stay intact. No tone filter.

## Use it

Download `GraphPaper-v0.6.0-Windows-x64.zip`, extract it completely into a new folder and open **GraphPaper.exe** with `_internal` beside it. This Windows package is unsigned. Keep your existing project data directory; do not copy an empty test database over it.

Open your existing project's **Graph** tab. **No extraction rerun is required.** Drag the canvas to orbit, Shift-drag to pan, wheel to zoom; click a node or a connection to edit it in the inspector. Use **Focus** and **Show** to control density. The author remains in charge of the wording.

[Graph studio controls and limitations](https://github.com/AronAxe/GraphPaper/blob/main/docs/GRAPH-STUDIO.md)

The public Graphify runtime, official Codex connection, reasoning controls, Science, Polemic, reusable voice graphs and bounded JEV requests are retained. This is not a claim that editing or displaying a graph establishes the truth of its claims.

Builds and native Windows release checks run on GitHub-hosted machines, not the user's computer. Synthetic fixtures exercise UI, provider transport and storage; no private accounts or manuscripts are used. Final validation and archive checksum are attached to the published release.

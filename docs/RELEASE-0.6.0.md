# GraphPaper 0.6.0 — Graph Atlas

The actual application UI has been redesigned, not replaced with a mockup.

- Charcoal/indigo workspace, clearer panels and a light sidebar using a real licensed scan of squared graph paper, bundled for offline use.
- Orbitable spatial graph, pan/zoom, depth cues, 2D/3D switch, expanded view and overview inset.
- Colored and shaped node types; separately colored, patterned, directional relationship lines with a legend.
- Dense-graph clusters, one/two-hop neighborhood focus, filters, full-graph search and collision-aware labels.
- Click-to-edit nodes and relationships, add/connect/delete/reverse controls and persistent one-step graph undo. No model calls for editing or viewing.
- Existing sources, manuscripts, reusable voices and authorial settings remain intact. No new tone filters.

Download the Windows ZIP, extract the whole folder and run `GraphPaper.exe` with `_internal` alongside it. Existing projects use the new view without rebuilding their graphs. The package is unsigned.

The spatial view projects x/y/z coordinates into SVG and works without a dedicated GPU or a remote CDN. The bundled paper asset is credited in the application files and documentation.

Guide: https://github.com/AronAxe/GraphPaper/blob/main/docs/GRAPH-ATLAS.md

Development and Windows packaging use GitHub-hosted runners, not the user's computer. Provider-dependent regression tests use synthetic fixtures; this UI release does not claim a new live-model writing-quality evaluation.

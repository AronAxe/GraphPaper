# Frequently asked questions

These answers describe GraphPaper **0.6.0**. For error-specific steps, see [Troubleshooting](TROUBLESHOOTING.md).

## Do I need to rebuild my graph after upgrading?

No. Open the existing project's Graph tab. The new renderer works with stored graphs. Rebuild when source material changes and you need fresh extraction, not merely because the interface changed. [Graph studio](GRAPH-STUDIO.md).

## Why am I seeing only 60 nodes?

That is the default display budget, not the size of the stored graph. **Show** offers 40, 60, 100 or 180 nodes; at most 360 connections are drawn at once. Search examines the whole graph, including nodes outside the current overview. Nothing is deleted by a display filter.

## How do I untangle a dense graph?

Click the important node and choose **Focus here**. Use one or two hops, filter node/connection types, or **Spread nodes apart**. Scroll to zoom, drag the canvas to orbit, Shift-drag to pan, and switch to **2D** for a flat view. **Fit graph** and **Reset filters** provide a route back. [All controls](GRAPH-STUDIO.md#navigate-without-losing-the-thread).

## Can I edit the graph rather than just look at it?

Yes. Click a node or a connection, edit its fields and choose **Save node** or **Save connection**. **Add node**, **Connect nodes** and confirmed deletion are available. **Undo edit** can reverse up to 25 recent manual graph edits, but does not overwrite a graph that has since been rebuilt or replaced. Source documents and the manuscript are separate from these edits.

## Is 3D a real interactive view?

Yes: XYZ positions are projected with perspective and depth sorting, and you can rotate the view. It is rendered using SVG, not WebGL, so it does not require a separate GPU graph engine. It is not a generated mockup. Camera and arranged positions are local view settings and are not currently part of a portable project export.

## How do I reuse my writing voice?

Save the profile under **Your writing voice → Save as reusable voice**. In another project, select it in **My voices → Use in this project**. The compact voice graph is applied without copying the training articles or running a model. To create a new voice, add material under the library's Training pieces and learn it once. [Reusable voices](VOICE-GRAPHS.md).

## Can a voice force polite language or override my current brief?

The saved voice is a default, not an editor with veto power. Your current brief and explicit instructions take precedence. Strong language, sarcasm, satire and indignation are valid choices; rhetorical force does not require lowering evidence requirements. Use Polemic or Nonfiction's **Develop and defend my position**, then refresh old angles. [Authorial intent](POLEMIC.md).

## Does Codex sign-in also authenticate JEV?

No. Codex supplies the writing/extraction route. JEV has a separate OpenRouter or TypeSafe connection and is optional. With it off, writing remains available and missing evaluations are not presented as real scores. [Connections](CONNECTIONS.md#optional-jev).

## Why did an older version say JEV exceeded 60,000 characters?

That was an application request-sizing failure. Since v0.5, requests are checked by their serialized UTF-8 size and split by questions/candidates before sending. JEV receives compact voice context, not the raw training library. An indivisible oversized optional decision remains explicitly unscored rather than aborting completed writing. The 60 KB budget is GraphPaper's transport budget, not a universal JEV limit. [Request sizing](VOICE-GRAPHS.md#why-jev-no-longer-receives-the-whole-heap).

## Do I need to install Graphify separately?

Not for the Windows release. Select **Graphify (external process)** and leave **Custom Graphify executable** empty to use the included 0.9.80 runtime. **Check Graphify runtime** makes no model call. An explicit custom path takes precedence and must be compatible. [Setup](CONNECTIONS.md#external-graphify).

## What uses model allowance or API credit?

Extraction, learning a voice, generating angles/outlines/drafts, model review and prose-editing passes can make calls. Navigation, manual edits, applying a saved voice, exporting and local prose inspection do not. A connection test makes a small real call. URL fetching and database search are separate network operations. Missing provider cost is unknown, not free; cancellation cannot refund a submitted request.

## Where are my projects, voices and backups?

The normal Windows directory is `%LOCALAPPDATA%\GraphPaper`. SQLite holds project state and the global voice library; project folders hold imports and preserved originals. Project JSON exports include the project's applied compact voice snapshot, not the complete global training library or revision history. Close the application and back up its data directory for complete local history; protect credentials in that backup. [Storage and recovery](PROJECTS-AND-SOURCES.md).

## Does Science mode perform experiments or guarantee journal acceptance?

No. It supports scholarly search, screening, source appraisal and manuscript preparation. Do not represent a literature-based manuscript as an experiment the software conducted. APA formatting and an export checklist do not replace author verification, editorial peer review or ethics approval. [Science workflow](SCIENCE.md).

[Getting started](GETTING-STARTED.md) · [Visual tour](VISUAL-TOUR.md) · [Troubleshooting](TROUBLESHOOTING.md)

# GraphPaper 0.4.0 — keep the author's argument

## Fixed: forced moderation of the writing

Angle generation no longer defaults to counterbalancing every position or turning a judgment into an open question. Author voice and a common authorial contract now reach **angle discovery, JEV evaluation, outline generation, drafting, review, revision and Humanize/Deslop**.

The critic checks facts without treating moral judgments, satire or rhetorical force as defects. A softened conclusion or an irrelevant caveat can be flagged as authorial drift. A more moderate or polite revision is not automatically a better revision.

## New: Polemic, the fourth writing mode

Polemic develops and defends the author's position. Different angles are different ways into the argument, not different degrees of retreat from it. Ordinary Nonfiction also supports an explicitly argument-led purpose; this is not only a new label.

**Core thesis**, **Writing purpose**, **Rhetorical force** and **Evidence detail** are separate controls. Lower evidence detail means leaner presentation, not fabricated facts. Higher detail does not request ideological balance. Polemic does not mechanically add profanity or replace the author's own voice with a generic aggressive style.

Short argumentative outlines up to 3,000 words are drafted as one coherent piece, avoiding repeated disclaimer openings caused by restarting the writer for every section. Longer writing, fiction continuity and the Science workflow remain available.

## Continue your current project

Open the existing project, choose **current mode · Change → Polemic**, and edit **Creative brief → Core thesis / Rhetorical force**. In Angles, choose **Refresh angles with my voice**.

**Do not rebuild the graph merely to change the writing stance.** The mode change preserves the source library, graph, voice profile, manuscript and prior generated work. Old angles do not rewrite themselves when a slider changes; they are marked stale until explicitly refreshed or edited.

## Windows package

Download **GraphPaper-v0.4.0-Windows-x64.zip**, extract the complete folder, and run **GraphPaper.exe** with `_internal` beside it. This portable build is unsigned. The included public Graphify runtime, Codex OAuth, reasoning controls, Science/APA, project folders and native freeze/save-on-close fixes remain in the package.

## Verification and scope

Regression tests cover intent and voice handoff at each stage, both opposing author positions, stale-context detection, existing-project preservation, polishing fidelity and source-reference export. Browser/native checks exercise the actual controls. Live Codex editorial examples use original synthetic documents and a synthetic voice sample, not private user articles; evidence for wiring is distinct from a universal prose-quality guarantee.

See [Polemic and authorial intent](https://github.com/AronAxe/GraphPaper/blob/main/docs/POLEMIC.md) and the versioned validation reports for exact test counts, platform results and live-test scope. SHA256SUMS.txt identifies the downloadable archive.

## Verified artifact

252 automated Windows tests passed (1 permission-related skip), all 54 browser checks passed, and all 17 checks passed against the actual compiled executable. Live Codex editorial tests used original synthetic material; JEV input behavior was tested without live JEV spending.

Windows ZIP: **187,529,591 bytes**. SHA-256: `c9fb03c6b293b8505b14ec427c7266aba1e3be8f0391be35ecead18a91399b53`.

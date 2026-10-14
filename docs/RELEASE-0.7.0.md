# GraphPaper 0.7.0 — System One decision studio

This release implements an operational JEV layer across the writing workflow, with a new **System One** sidebar desk.

- Focused Noul predicates, descriptive Score levels and probability-aware Choices. Fidelity is not a tradeable fraction of a generic quality score.
- Stage-level question fan-out, exact-context caching, typed-distribution validation, bounded request sizes and honest unscored fallbacks.
- Guided graph exploration and semantic source selection. Entity identity suggestions require explicit author-approved, undoable merging.
- One-pass angle-intent repair, independent passage checks, contextual changed-prose checks and confidence-gated automatic refinement. No politeness filter or new vocabulary restrictions.
- Task-selected reusable voice habits, explicit saved corrections, local preference training with held-out projects and decision/feedback export.
- Science screening advice, full-text priorities, appraisal-gap checks and fiction continuity decisions.
- Optional routing only among author-approved model alternatives and reasoning settings. Routing defaults to off.

## Use the Windows release

Extract the complete ZIP into a new folder. Run **GraphPaper.exe** with `_internal` beside it. Your project database stays in its existing data directory. No graph rebuild or voice retraining is required to use the update.

Open a project, select **System One**, and configure your JEV connection in **Connections & settings**. **Evaluate current work** evaluates available material without writing or replacing it. The desk exposes questions, distributions, policy outcomes, cached results and failures. Prefer/reject feedback and local training do not make model calls.

The existing graph-paper design, four writing modes, Graphify, Codex sign-in, reusable voice library and reversible edits remain. The application is unsigned. Review the [System One guide](https://github.com/AronAxe/GraphPaper/blob/main/docs/SYSTEM-ONE.md).

## Verification scope

The release workflow runs regression tests and eight real-HTTP browser suites before building Windows; it then tests the actual packaged native window, including the System One desk, feedback, configuration, graph edits, native export and save-on-close. Provider fixtures are explicitly synthetic: passing these checks does not claim a measured live JEV writing-quality or cost advantage. The published asset must match the tested archive checksum.

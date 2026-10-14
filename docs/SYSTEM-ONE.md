# System One decision studio

GraphPaper 0.7 uses TypeSafe's **Choice, Score and Noul** judgments to select material and control work, not merely rate a finished article. The writing model still generates prose. Ordinary code owns budgets, thresholds, persistence and actions. The author owns the thesis and the final words.

## Open it

Open a project and select **System One** in the sidebar. **Evaluate current work** runs a JEV-only audit of available angles, passages and possible entity matches; Science adds screening/appraisal recommendations. It does not write or replace your manuscript. Connect a TypeSafe or OpenRouter JEV account in Connections first. Viewing receipts, editing settings, rating proposals and local preference training make no inference calls.

## What now changes the workflow

| Stage | Focused judgments | What code does with them |
|---|---|---|
| Graph opportunities | Relevance, grounding, descriptive craft/novelty levels | Ranks comparable scored candidates separately from unscored fallbacks; expands a bounded set of promising neighborhoods |
| Angles | Stance, distinct reasoning, voice, added allegations, irrelevant caveats and evidence needs | Requests at most one targeted intent repair; preserves the original proposal for inspection; flags uncertainty without moderating the thesis |
| Sources | Relevance, direct support, contrary evidence and useful examples | Reranks whole nominated passages within the writer's context budget; keeps required-source coverage explicit |
| Voice | Relevance of each saved writing habit to the current task | Selects a compact graph view without changing the stored voice; current instructions override every learned habit |
| Draft review | Independent paragraph checks plus concrete editorial findings | Uses Choice probability, confidence, margin and material/fixable checks before any optional automatic revision |
| Humanize/Deslop | Changed-passage meaning, stance, voice, reasoning loss and concrete improvement | Presents a safe proposal or escalates uncertain/global edits to the contextual editor; automatic refinement keeps the original unless improvement is supported |
| Science | Eligibility against explicit criteria, need for full text and appraisal gaps | Records screening recommendations, prioritizes already included papers and marks gaps. It never silently includes/excludes papers |
| Fiction | Explicit canon, character knowledge, motivation and repeated beats | Checks scenes before the continuity-ledger update and attempts one targeted correction when a concrete conflict is detected |
| Entity identity | Same, related, different or uncertain | Presents possible matches. Only the author can apply a merge; graph Undo preserves recovery |
| Approved model routing | Local/simple task versus difficult synthesis | Uses only explicitly configured alternatives with their selected reasoning effort. Default is off |

## The argument is not an average

A confident failure to preserve an author's stated position cannot be compensated for by fluent prose. Craft and novelty have descriptive Score levels; stance fidelity and semantic drift are independent Noul predicates. A failed fidelity condition produces a repair request rather than a lower generic score. You may still inspect, edit or choose any proposal. Strong language, satire and categorical moral judgments are not automatic failures.

Uncertainty concerns **whether the software should act**, not whether every sentence must sound uncertain. A weakly winning Choice does not authorize a rewrite. Initial thresholds are explicit engineering policies (`system_one.py`), not claimed domain calibration: strong yes/no uses 0.82/0.18; automatic Choice requires confidence at least 0.55 and a probability margin of at least 0.20. The revision branch also requires a material, fixable issue. Deterministic source-ID and protected-span checks remain independent.

## Batching, cache and failure behavior

Each independent stage submits its candidates and questions together. The transport packs requests within its 60,000-byte application budget and 100-question envelope; these are not asserted intrinsic JEV limits. A full candidate's relevant context travels with its questions, with stable IDs. Voice-training articles do not travel in JEV requests. Exact-context caching includes provider, model, questions, policy and state hashes; mutable model aliases expire by UTC day.

Unavailable or unrepresentable optional decisions stay visibly unscored. They do not invent passing scores or replace the draft. Cancellation is not swallowed. Writing-call capacity is reserved. The original provider consent and request caps remain in force.

## Inspect the decision, not just a badge

The desk shows recent stage receipts, question wording, all returned distributions, Score legends, context hash, provider/model, cached/evaluated/unavailable status and elapsed time. It also explains angle policy outcomes and preserves pre-repair proposals. Receipt retention is bounded to a recent window; a receipt can predate a later manual edit. **Export decisions & feedback** produces a local JSON research record with a comparison protocol. It contains local author corrections and judgments, not API keys. Review before sharing.

## Reusable feedback and local learning

Choose **Prefer this** or **Reject / correct** for an angle. An optional correction immediately becomes reusable author guidance when learning is enabled. It is scoped to the applied voice and writing mode; without a shared voice it stays with that project. Current project instructions override older corrections. A second click updates the label rather than manufacturing another training sample. Remove a correction to retract it.

**Train from my feedback** fits a small deterministic, L2-regularized logistic preference ranker to JEV features, entirely locally. It needs both preference classes, at least 40 fully scored labels and four projects sharing the same voice and mode. Complete projects are held out. The model is activated only when holdout Brier score improves over the fixed craft/novelty baseline by 0.01 or more. Training is not automatic fine-tuning of the LLM. Feedback changes invalidate the ranker until retraining. The learned ranking adjustment is bounded and cannot override a fidelity constraint. **Reset learned ranker** restores baseline ranking without deleting corrections.

This is a usable learning loop, not a claim of a validated general model of taste. Duplicate or closely related projects can still make evaluation too optimistic; use genuinely different held-out writing tasks. The JSON export supports independent comparison of direct prompting, graph-without-JEV and System One runs using author preference, unsupported additions, editing time, latency and cost.

## Routing without surprises

Under **Configure**, routing is off unless you enable it and enter an approved fast and/or deep model. Empty alternatives retain the selected writer/editor/extraction model. The current provider and credentials never change. Unsupported reasoning settings remain explicit errors, not a quiet downgrade. JEV is not called recursively to evaluate its own requests.

## Scope of validation

Tests exercise typed transport, probability-aware policy, fan-out, exact cache invalidation, meaningful fallback, author feedback, held-out training, source selection, graph/scene/research handoffs, and the real UI. Synthetic providers test behavior, not live JEV editorial superiority. A live performance claim requires a separate, explicitly budgeted evaluation with real labeled writing tasks.

References: [TypeSafe primitives](https://docs.typesafe.ai/primitives), [confidence](https://docs.typesafe.ai/confidence), [building with System One](https://docs.typesafe.ai/concepts/how-to-build-with-system-one), and [LangChain's harness example](https://www.langchain.com/blog/building-a-harness-with-jev).

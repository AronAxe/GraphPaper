# Writing without operating the UI

## Author contract

Read the task and supplied material first. Keep the separate strands of the user's reasoning in the brief. Set mode to `polemic` for a chosen argument, `nonfiction` for factual essays, or `fiction` for stories. In nonfiction, `stance_policy=preserve` develops a selected position; `explore` investigates an open question. `rigor` governs evidence presentation, not how mild the opinion must be. `rhetorical_force` governs delivery, not permission to fabricate evidence. Strong language, satire, moral judgments and purposeful repetition are legitimate choices.

Ask only for requirements that the prompt, sources and saved voice cannot resolve. A delegated writing task can authorize the **agent** to choose the angle and outline. It need not send the user through those screens. Publication, source deletion, journal attestations and new provider spending need their own authority.

## Full backend route

Use the client and exact request shapes in API recipes:

1. Create a project or read the specified existing project; back up an existing draft. Merge the brief and apply an existing reusable voice when requested.
2. Import the sources once. Inspect source IDs, roles and warnings. Use `canon` for established fictional facts, `inspiration` for prompts/possibilities, `evidence` for citable source material. Research is a separate Science workflow, not a hidden ordinary-nonfiction web search.
3. Run `graph`. Inspect meaningful nodes/relationships and important source anchors. Pin relevant nodes through `brief.pinned_nodes`; exclude only distractions actually outside the task. A path nominates an argument, not proof of its truth.
4. Run `angles`, then fetch the updated project. Check each proposal against **every material strand** of the brief, not merely its total score. Read `system_one` receipts for missing or uncertain judgments and any repaired proposals. Do not prefer a sanitized substitute because it sounds polished.
5. With delegated selection, choose a suitable angle by its returned ID and PATCH `selected_angle` with the current `version`. An agent-authored angle is allowed: use the existing angle schema and actual source/node IDs; never fabricate a JEV score. Without delegated selection, present the unresolved options in conversation.
6. Run `outline`. Fetch it, improve progression/beats and allocations where needed, and preserve `source_ids`. Do not add obligatory opposite-view or disclaimer sections. In fiction, track desire, obstacle, knowledge, stakes, choices and consequences. PATCH the actual approved outline; the running system can then draft without a GUI approval flag.
7. Run `draft`. Fetch the manuscript, review, `system_one` state and job receipts. The pipeline already performs review; avoid paying for the same review again when nothing changed. Science uses its own actions.
8. Repair specific failures. Use `revise` with an instruction file or the editing workflow; preserve the thesis, humor, force, source qualifiers and best lines. Do not enter an unbounded improve/review loop. Fetch saved checkpoints after failures rather than recreating the whole article.
9. Export the manuscript and backup. Report what was actually done and where evidence, judgement or budget limits remain.

## Bring the agent's own draft

The calling agent can write or edit prose itself, PATCH `draft`, and use GraphPaper for graph/source organization, JEV audits, review, provenance and export. This avoids pretending the calling agent's account is automatically a GraphPaper provider. The agent can likewise import a valid node-link graph or set an outline; imported relationships stay explicitly imported. A full `review` job may invoke GraphPaper's configured editor; a deterministic `craft/audit` does not.

Do not perform model spending merely to demonstrate a skill invocation. Reuse an existing current graph and saved voice. A change of angle or rhetorical force does not automatically require re-extracting unchanged sources. After actual source changes, inspect graph coverage/staleness before relying on its prior extraction.

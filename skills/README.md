# GraphPaper agent skill

Install **[graphpaper](graphpaper/SKILL.md)** to let a filesystem/process-capable agent use GraphPaper without clicking through its Windows application. The pack includes a headless host, a JSON API client and on-demand workflow guides for nonfiction, polemic, fiction, scientific research, saved voices, editing and System One.

This is a skill plus an executable bridge to the **same backend**, not a separate writing engine, an MCP server or a claim of guaranteed writing improvement. The desktop executable is unchanged. The source edition supplies the backend; an agent can install and run it on its own authorized machine or sandbox. Installing the skill alone does not install Python dependencies or grant access to accounts.

## Install once

Copy the complete `skills/graphpaper` directory into your agent's skill discovery directory. Common destinations are `.agents/skills/graphpaper` for compatible agent runtimes and `.claude/skills/graphpaper` for Claude Code; use a user-level directory to share the skill across projects. Hosts differ: follow their skill installation procedure. Do not copy only `SKILL.md` and leave out `scripts/` or `references/`.

One portable copy command, executed from this repository, is:

```sh
python -c "from pathlib import Path; import shutil; shutil.copytree('skills/graphpaper', Path.home()/'.agents/skills/graphpaper')"
```

It refuses to overwrite an existing installation. Review a previous copy before replacing it. Alternatively, point the agent directly to `skills/graphpaper/SKILL.md` in this checkout.

## Give the agent a task

> Use the GraphPaper skill to write a 1,600-word polemic from the supplied sources in my saved voice. Preserve my argument and humor. You may choose the strongest angle and outline. Keep the source and decision records, and return the draft as Markdown and Word. Use the approved provider and budget; do not open the GUI.

Or:

> Use GraphPaper to assess this draft, remove repetitive disclaimers and preserve my conclusions. Show the proposed changes; do not replace the original yet.

The agent handles source import, job polling, angle/outline selection when delegated, review and export. Initial provider authorization or a genuinely unresolved author decision still belongs to the user; neither requires manually operating GraphPaper's UI.

## Runtime and privacy

See [setup and provider configuration](graphpaper/references/setup.md). Start a **separate explicit data directory**, not the ordinary desktop workspace. Reusing that directory preserves agent projects between sessions. Moving computers still requires transferring project/voice exports; installing a skill is not synchronization. Keep API keys and account files out of the skill, repository, prompts and exports.

The client is standard-library Python. The server uses GraphPaper's source dependencies; no Windows windowing/.NET dependency is imported. Requests stay on `127.0.0.1`; the backend retains its normal session, source, provider-consent and version checks. This is a trusted single-user tool, not an authorization boundary between mutually untrusted local agents. Do not expose it on a network interface.

## Tests and scope

```sh
python -m unittest discover -s skills/tests -p 'test_*.py' -v
```

Client/skill-contract checks run without models. Backend integration checks require the source requirements and development dependencies; they use real loopback HTTP with the repository's explicitly synthetic model fixtures. The `Agent skills` workflow executes them on Windows and Linux. These are API/workflow checks, not proof of live model quality or separate agent-host certification. [Behavioral scenarios and acceptance criteria](graphpaper/references/evaluation.md) cover the remaining live-agent evaluation.

Format references: [Agent Skills specification](https://agentskills.io/specification), [OpenAI skill authoring](https://developers.openai.com/codex/skills), [Claude skill documentation](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview).

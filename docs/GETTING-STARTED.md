# Getting started

This guide takes you from a downloaded application to an editable first draft. For installation problems, use [Windows setup](WINDOWS.md) or [Troubleshooting](TROUBLESHOOTING.md).

## 1. Open the Windows application

Download `GraphPaper-v<version>-Windows-x64.zip` from [GitHub Releases](https://github.com/AronAxe/GraphPaper/releases/latest). Extract the **complete** folder and run `GraphPaper.exe`. Leave `_internal` alongside the executable; it contains the application’s dependencies and interface.

The compiled edition includes Python and the official Codex runtime. It needs Edge WebView2, but no Python installation or terminal workflow. GitHub’s automatic “Source code” downloads are a different edition. See [Windows](WINDOWS.md) for that route.

## 2. Choose a writing connection

Open **Connections & settings**.

| Route | Configure |
|---|---|
| **Codex — sign in with ChatGPT** | Complete the browser sign-in, then load available models. A blank model can use the Codex default. |
| **OpenRouter** | Save an OpenRouter key, load models and select a writer. |
| **OpenAI-compatible / local** | Set the endpoint and model ID; supply a key when the server requires it. |
| **Anthropic** | Select the direct provider, save its key and choose a model. |

Enable the permission to send project material before using a cloud model. A localhost model can be used without cloud permission. Connection tests make small model requests and can consume allowance or API credit.

Leave reasoning at **Provider default** initially, or load the model catalog and choose supported levels for the writer, editor and extractor. JEV is optional and configured separately. [Detailed model setup →](CONNECTIONS.md)

## 3. Create a project

Give it a working title, a target length and a direction. Choose a mode deliberately:

- **Nonfiction:** source-linked articles and essays.
- **Fiction:** stories, character decisions, scenes and canon.
- **Science:** scholarly searching, evidence appraisal and academic manuscripts.

Mode is chosen at project creation; the interface does not provide a conversion button for an existing project. A title can be changed without changing the project’s identity or folder.

## 4. Add useful material

In **Sources**, upload supported documents, paste text or import a public article URL. Choose the appropriate source role: **Evidence**, **Canon**, **Inspiration** or **Voice**. Review extracted text, especially PDFs and tables.

For fiction, a premise and canon in the **Creative brief** can be enough to begin. Science starts at the **Research** desk; include retrieved papers to turn them into project evidence sources.

The **Project folder** button opens the workspace in Explorer. Files dropped into its Inbox are imported while the project is open and idle; that import alone does not run an AI task. [Sources and folders →](PROJECTS-AND-SOURCES.md)

## 5. Explore, choose and structure

For nonfiction or fiction, build the graph. Select concepts and relationships to inspect their source anchors. Pin ideas you want to emphasize; exclude distractions. Then **Discover angles**.

Choose a suggested direction, edit its thesis or write your own. Develop an outline and review each section’s purpose, source assignments and word allocation before generating a full draft.

For Science, run the [research workflow](SCIENCE.md), then create its scientific outline. Graph exploration can help investigate a framing, but it is not a substitute for screening and checking the literature.

## 6. Write and review

The writing desk supports manual Markdown editing, preview, model-generated drafts, review and explicit revisions. `Ctrl+S` saves; normal typing also autosaves. Generated drafting checkpoints and previous versions provide recovery options.

Use **Humanize** or **Deslop** when you need a prose-editing pass. The proposed result is separate from your draft until accepted. [Voice and editing →](VOICE-AND-PROSE.md)

## 7. Export the result

Use **Export** for Word, Markdown, HTML or a portable project backup. Science adds APA references and research-package exports. Keep the source passages accessible while verifying factual claims.

A project backup contains the current project state, not the complete local revision database. Close GraphPaper and copy its data directory for a full-history backup. [Export and backup details →](EXPORTS-AND-APA.md)

## Before a large job

Check the target length, selected model, reasoning, context budget and maximum requests. Review a small extraction first. A source library can require many model calls, and a high reasoning level can increase latency and token use. Cancellation stops further work but cannot guarantee an in-flight request will not be billed.

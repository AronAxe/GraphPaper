# GraphPaper 0.8.0

Connect local AI agents to GraphPaper and export articles and polemics with their references.

- **Local MCP adapter.** Agents can read projects, sources, and graphs, apply saved voices, edit drafts, and run GraphPaper jobs. The adapter supports both the desktop and a separate headless workspace. The Windows ZIP includes the adapter and a setup guide. [Connect an agent](https://github.com/AronAxe/GraphPaper/wiki/Connect-an-AI-Agent)
- **References in the writing desk.** In Nonfiction and Polemic, Preview and Split show clickable citations and a reference list in order of first citation. GraphPaper flags missing, excluded, and non-evidence sources.
- **PDF and Word export.** Choose **Write → Export draft** for a PDF or editable Word file (`.docx`). Both include the same numbered citations and bibliography. [Export guide](https://github.com/AronAxe/GraphPaper/wiki/Exports-and-APA)
- **Resolve concurrent edits.** If an agent or another window saves first, the writing desk lets you compare the saved draft with your unsaved edits and save a merged version.

Extract the entire Windows ZIP into a new folder and open **GraphPaper.exe** with `_internal` beside it. GraphPaper reads projects from your existing data directory. The MCP adapter uses Python 3.11 or later. [Windows installation](https://github.com/AronAxe/GraphPaper/wiki/Windows-Installation)

# Publishing and Windows packages

The GraphPaper source is published to **AronAxe/GraphPaper** through the authorized GitHub connector. The earlier claim that the connector was read-only was incorrect. The optional GUI publisher remains useful for independently distributing a verified source package, but is not required for this repository upload.

## Build a Windows package

After merge to the default branch, open **Actions → Windows desktop package → Run workflow**. A successful run produces a GraphPaper-Windows-x64 artifact containing the executable and companion files. Run a native interactive smoke test before treating an unsigned build as a public release.

The import workflow assembles checksum-verified frontend source, runs the test suite and browser checks, and regenerates illustrative assets. Its commit removes the temporary transfer chunks; ordinary users receive regular application source files.

## Optional no-terminal publisher

Install Git for Windows with Git Credential Manager. Double-click **Publish GraphPaper.vbs** in a source package and choose Publish source. The helper checks the source manifest, creates a new branch of AronAxe/GraphPaper, and opens GitHub for review and merging. It never force-pushes, overwrites main directly, deletes unknown existing repository files, or includes local manuscripts and API keys.

The helper's actual Git push has not been exercised by this build session; repository writes were performed through the connector. Path/hash controls have automated tests. For subsequent edited development, use ordinary Git or GitHub Desktop instead of relying on an old source-package manifest.

The GitHub main branch and original MIT license are preserved through a normal pull-request merge. CI artifacts and releases should be judged by their actual run results, not by the existence of a workflow file.

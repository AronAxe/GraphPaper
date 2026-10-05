# Security and privacy

GraphPaper is a single-user local application, not a hardened multi-tenant hosted service. Do not expose its loopback server through a public proxy or bind it to the LAN.

## Data at rest

Source text, manuscripts, extraction cache and revisions are stored in local SQLite **without database encryption**. Use OS disk encryption and appropriate account permissions for confidential material. Project JSON backups include the source text; treat them as confidential documents.

On Windows, stored API credentials are protected with DPAPI and tied to the user context. On other systems, an available OS keyring is used; otherwise keys are session-only. There is no plaintext fallback. Keys are not returned to the browser or exported in project backups.

## Network and providers

Cloud processing requires explicit consent. Once enabled, task-relevant source passages, project instructions and drafts are sent to the selected providers, including JEV when enabled. Their retention/training/processing terms apply; local storage does not imply offline model processing.

URL imports are explicit network operations separate from model consent. They support public HTTP/S resources on ordinary ports, validate DNS addresses, pin a vetted address for connection and revalidate redirects. Private, loopback and link-local article URLs are rejected. TLS verification stays enabled. There is no credentialed browser scraping, hidden cookie forwarding or paywall bypass.

A custom **model** base URL is deliberately different from an article URL: localhost is supported so users can run local inference. Only configure a provider endpoint you trust with the associated key.

## Local interface

The service uses a per-session HttpOnly, SameSite cookie plus a custom request header for stateful API access and validates Origin/Host. Content Security Policy disallows arbitrary scripts, eval and framing. User source text and model output are rendered with escaping; the app does not execute code received from a model. Native file access is limited to explicit export dialogs. External links open outside the app; file-URL navigation and implicit downloads are disabled in the shell.

The Python bridge's export and close operations are narrow but are not an isolation boundary against malicious code already running under your Windows account. This app does not claim to defend a compromised computer.

## Optional Graphify

Running Graphify executes a user-selected local program. Only choose a trusted installation. It receives the configured model credential and a temporary source-text corpus. As an independent program it is outside GraphPaper's internal request accounting; do not assume the app can audit every action or guarantee all child-process behaviour. Use native extraction instead when that additional trust is inappropriate.

## Publishing helper

The optional publisher uses a hash-checked allowlist, not the studio database directory. It clones a fixed repository into a fresh working folder, copies the source package, commits, pushes a new branch and opens a comparison. It never requests a raw GitHub token, disables Git security or force-pushes main. Git Credential Manager is responsible for sign-in.

A manifest detects accidental changes, not a sophisticated attacker who can replace both the code and its hashes. The package is **not digitally signed**. Review source changes and use the GitHub pull request before merging. The publisher is not called by normal startup.

## Reporting

Report security issues privately to the repository owner before publishing sensitive details. Do not include credentials or confidential manuscript text in screenshots, issue attachments or logs. Review files before sharing an entire local data folder.

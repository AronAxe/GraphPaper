# Privacy and security

GraphPaper is a single-user local desktop application. Local-first describes where the project is stored and who controls actions; it does not mean a selected cloud model runs offline.

## What stays on the device

The SQLite database holds source text, manuscripts, settings, extraction cache and revisions. Project folders hold Inbox material and preserved originals. This content is **not database-encrypted**. Use OS account protections, disk encryption and appropriate backups for confidential work.

Project JSON backups include source text. Research packages include the manuscript, protocol and evidence metadata. Treat both as documents that may contain sensitive information; they are not anonymized automatically.

## Credential storage

Windows API credentials use DPAPI rather than plaintext storage. Other systems can use an available OS keyring; otherwise keys remain session-only. The interface receives presence/status flags, not the saved API secrets, and project exports do not include them.

Codex manages its own sign-in state in GraphPaper’s separate `codex-account` directory. Do not treat that directory as an ordinary shareable project folder. Signing out there does not automatically sign out unrelated Codex installations. DPAPI-protected keys may not be portable to a different Windows account or computer.

Do not paste tokens into manuscript prompts, source documents, command examples or public screenshots. Environment-provided credentials used for development deserve the same protection.

## When network requests happen

| Action | What may leave the device |
|---|---|
| Cloud extraction, drafting, review, voice learning or prose editing | Task-relevant project text sent to the selected writing provider |
| JEV decisions | The candidate/evidence or editorial state required for the decision |
| Public URL import / author-page discovery | The requested URL and ordinary network request information |
| Scholarly search / full-text retrieval | Search terms, requested identifiers, and an optional service credential |
| Codex browser sign-in | The official account-authentication flow handled by Codex |
| Optional Graphify subprocess | A temporary source corpus and the configured provider connection |

Cloud generation requires permission. Website imports and scholarly searches are distinct user-triggered network operations and do not require an LLM key. Provider processing, retention, account and rate-limit policies still apply. The app has no analytics or hidden automatic publishing.

## Local interface protections

The backend binds to an ephemeral **127.0.0.1** port, not the LAN. API access uses a per-session HttpOnly/SameSite cookie, a custom header and Origin/Host checks. The interface escapes imported text and generated output, uses a restrictive Content Security Policy and does not execute model-provided code.

The native bridge exposes four explicit methods rather than recursively exposing database, runner or Windows objects. Save-before-close dispatches without blocking the Windows message loop. These boundaries prevent the known native interaction defect; they are not a defense against malicious software already running as your user.

Do not expose the local service through a public reverse proxy or change it into a multi-user hosted deployment without a separate security design.

## Files and public URLs

Ingestion enforces limits and checks supported types. Public article retrieval validates network destinations, rejects private/loopback/link-local addresses, pins a validated address and rechecks redirects. It does not use your authenticated browser cookies or bypass access controls.

The **model endpoint** is deliberately different: localhost is permitted for local inference. Only enter a provider URL you trust with the associated credential.

Inbox import checks stable files and rejects unsafe filesystem cases such as symlinks. Those checks do not turn an untrusted downloaded program into a safe attachment. Imported documents remain untrusted data for model prompts.

## Optional executables and release integrity

Graphify is a separate executable selected by the user. Its behavior, retries and child processes are outside GraphPaper’s internal metering. Use a trusted installation or native extraction instead.

The Windows release bundles an official Codex runtime with version and checksum provenance. `SHA256SUMS.txt` identifies the exact application ZIP. The GraphPaper binary is unsigned; a checksum is not a signed publisher identity or an independent audit.

## Sharing and reporting

Before sharing a log, screenshot or project, remove credentials, confidential writing and personal data. Report ordinary reproducible defects through [Issues](https://github.com/AronAxe/GraphPaper/issues). Use an established private contact route to the repository maintainer for a security-sensitive report; do not publish active credentials or an exploit against someone’s live installation.

This documentation describes implemented safeguards and their limits, not a formal penetration-test certification. [Validation scope →](QUALITY.md)

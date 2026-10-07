# Releases and Windows packaging

Most users should download the compiled Windows ZIP from [Releases](https://github.com/AronAxe/GraphPaper/releases/latest). This page is for maintainers producing an application release, not for everyday writing.

## Source, artifact and release are different

**Source** is the repository or GitHub’s automatic source archive. It is not a compiled Windows application.

**Actions artifacts** are outputs of an individual workflow run. Their existence does not mean a public release has been published.

**A release asset** is the versioned Windows ZIP attached to a release, accompanied by `SHA256SUMS.txt`. The author should be able to identify the exact file that was validated.

A documentation-only update normally does not require rebuilding or renumbering the application. Keep published binaries and their checksums untouched unless intentionally creating a new version.

## Build and validate

The [Windows workflow](../.github/workflows/windows.yml) provides the executable release path. The [build script](../scripts/build_release.ps1) installs the desktop build dependencies, verifies the official Codex runtime, packages the application with PyInstaller and checks the compiled backend/assets.

The release pipeline then exercises the **actual native window**, including the Science workspace. It does not substitute a browser-only test for the desktop shell. Preserve the private bridge and asynchronous save-before-close behavior when changing desktop code.

Run the unit/integration and browser workflows as well. Use isolated temporary project directories and controlled fixtures. Live scholarly connectivity is a separate opt-in check; no user credentials or private manuscripts belong in test artifacts.

[Developer commands →](DEVELOPMENT.md#run-the-tests)

## Package integrity

The application is a one-directory build: `GraphPaper.exe` needs its companion `_internal` files. The [streaming packager](../scripts/package_windows.py) writes a ZIP without buffering the full runtime in memory, verifies CRCs and records SHA-256.

The official Codex vendor bundle includes version and checksum provenance. Preserve the applicable third-party licenses. Do not label an unsigned application as signed or equate a digest with publisher certification.

Before publishing, verify that the package contains the current interface, version and release documentation, not assets copied from an older build.

## Publish a new version

Update the application version and changelog deliberately. Review the workflow’s current release-note path; it must describe the version being built. Run validation and inspect the reports before attaching the asset.

A version tag must match the application version. The workflow publishes a versioned ZIP and checksum, and avoids silently overwriting an existing verified release asset. If a fix is needed after publication, create a new corrective release with its own version and evidence.

The release notes should distinguish native/local validation from hosted Actions results, and live provider checks from controlled test doubles. Do not present an unavailable or throttled database as tested successfully.

## The source publishing helper

`Publish GraphPaper.vbs` opens an optional GUI publisher for a verified source package. It is separate from normal app startup, targets `AronAxe/GraphPaper`, verifies a code-only manifest and pushes a new branch for review. It is not the portable executable installer.

The helper requires Git for Windows and Git Credential Manager. It does not need a raw token pasted into the application, does not force-push main and does not upload the local manuscript database. Modified development code should use ordinary Git or GitHub Desktop rather than an outdated package manifest.

When maintaining a source package, regenerate `publish-manifest.json` from the staged source after changes. Verify hashes against the committed bytes, including line-ending normalization; the manifest is not a digital signature.

$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
python -m pip install -q -r requirements-desktop.txt 'pyinstaller>=6.16,<7'
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
python scripts/bundle_codex.py
if ($LASTEXITCODE -ne 0) { throw 'Official Codex runtime verification failed.' }
python scripts/check_codex.py
if ($LASTEXITCODE -ne 0) { throw 'Codex runtime protocol check failed.' }
python -m PyInstaller --noconfirm --clean --windowed --onedir --name GraphPaper --paths . --icon ui/graphpaper.ico --add-data 'ui;ui' --add-data 'vendor;vendor' --collect-all webview scripts/desktop_entry.py
if ($LASTEXITCODE -ne 0) { throw 'Windows desktop build failed.' }
Copy-Item README.md, LICENSE -Destination dist/GraphPaper/
Copy-Item docs/RELEASE-0.2.1.md -Destination dist/GraphPaper/WHATS-NEW.md
python scripts/check_package.py dist/GraphPaper
if ($LASTEXITCODE -ne 0) { throw 'Compiled application self-test failed.' }
$version = python -c "from graphpaper import __version__; print(__version__)"
$zip = "dist/GraphPaper-v$version-Windows-x64.zip"
Compress-Archive -Path dist/GraphPaper -DestinationPath $zip -Force
$hash = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
"$hash  GraphPaper-v$version-Windows-x64.zip" | Set-Content -Encoding ascii "dist/SHA256SUMS.txt"
Write-Host "Built $zip"

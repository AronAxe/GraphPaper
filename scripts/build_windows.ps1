$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
python -m pip install -r requirements-desktop.txt 'pyinstaller>=6.16,<7'
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
python -m PyInstaller --noconfirm --clean --windowed --onedir --name GraphPaper --paths . --icon ui/graphpaper.ico --add-data 'ui;ui' --collect-all webview scripts/desktop_entry.py
if ($LASTEXITCODE -ne 0) { throw 'Windows desktop build failed.' }
Copy-Item README.md, LICENSE -Destination dist/GraphPaper/
Compress-Archive -Path dist/GraphPaper -DestinationPath dist/GraphPaper-Windows-x64.zip -Force
Write-Host 'Built dist/GraphPaper-Windows-x64.zip'

$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
python -m pip install -r requirements-desktop.txt 'pyinstaller>=6.16,<7'
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
python -m PyInstaller --noconfirm --clean --windowed --onedir --name GraphPaper --paths . --icon ui/graphpaper.ico --add-data 'ui;ui' --collect-data reportlab --collect-all webview scripts/desktop_entry.py
if ($LASTEXITCODE -ne 0) { throw 'Windows desktop build failed.' }
Copy-Item README.md, LICENSE -Destination dist/GraphPaper/
New-Item -ItemType Directory -Force -Path dist/GraphPaper/agent, dist/GraphPaper/docs | Out-Null
Copy-Item skills/graphpaper/scripts/gp.py, skills/graphpaper/scripts/graphpaper_mcp.py, skills/graphpaper/scripts/requirements-mcp.txt -Destination dist/GraphPaper/agent/
Copy-Item docs/AGENT-MCP.md -Destination dist/GraphPaper/docs/
Compress-Archive -Path dist/GraphPaper -DestinationPath dist/GraphPaper-Windows-x64.zip -Force
Write-Host 'Built dist/GraphPaper-Windows-x64.zip'

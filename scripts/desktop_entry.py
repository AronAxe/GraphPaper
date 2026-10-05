"""PyInstaller entry point; execute from repository root."""
import sys
from pathlib import Path
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from graphpaper.desktop import main
main()

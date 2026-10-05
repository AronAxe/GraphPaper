"""PyInstaller entry point with machine-readable packaging diagnostics."""
import json
import sys
import traceback
from pathlib import Path
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from graphpaper.desktop import main
    main()
except Exception:
    if '--self-test' in sys.argv:
        index = sys.argv.index('--self-test') + 1
        if index < len(sys.argv):
            Path(sys.argv[index]).write_text(json.dumps({'ok':False, 'error':traceback.format_exc()}), encoding='utf-8')
        raise SystemExit(1)
    raise

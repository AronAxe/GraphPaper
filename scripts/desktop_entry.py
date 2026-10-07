"""PyInstaller entry point with machine-readable packaging diagnostics."""
import json
import sys
import traceback
from pathlib import Path
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
if len(sys.argv) > 1 and sys.argv[1] == '--graphify-worker':
    from graphpaper.graphify_worker import main as graphify_main
    raise SystemExit(graphify_main(sys.argv[2:]))
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

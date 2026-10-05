"""Assemble checksum-verified source chunks and update the CSP-safe browser harness."""
from pathlib import Path
import hashlib
import shutil
root = Path(__file__).resolve().parents[1]
items = [("app", 9, "ui/app.js", "837aa4111bd7fc4003768e96551a0c630a7d9c1cf6e40d484bdc825d0d93bddb"), ("css", 3, "ui/styles.css", "99fb8fb724a74d2d8cc31ea1e7e6b4422f87dfff7015d26313129e999d8631c2")]
for folder, count, target, expected in items:
    parts = sorted((root / "_transfer" / folder).glob("*.part"))
    if len(parts) != count:
        raise RuntimeError("Incomplete source transfer: " + folder)
    data = b"".join(p.read_bytes() for p in parts)
    if hashlib.sha256(data).hexdigest() != expected:
        raise RuntimeError("Source checksum mismatch: " + target)
    (root / target).write_bytes(data)
    print("Verified", target, len(data), "bytes")
# Playwright's string-predicate polling may eval under a strict CSP. Poll through
# the DevTools evaluate API instead. Keep the application CSP unchanged.
p = root / 'scripts/ui_smoke.py'
text = p.read_text(encoding='utf-8')
for action in [None, 'draft', 'revise']:
    predicate = "state.job?.state === 'completed'" if action is None else f"state.job?.action === '{action}' && state.job?.state === 'completed'"
    old = 'page.wait_for_function(' + repr(predicate).replace("\\'", "'") + ')'
    old = 'page.wait_for_function("' + predicate + '")'
    new = 'wait_for_completion(page)' if action is None else f'wait_for_completion(page, {action!r})'
    text = text.replace(old, new)
helper = '''def wait_for_completion(page, action=None):
    """CSP-safe polling of the actual job state; do not weaken the app policy."""
    deadline = time.monotonic() + 30
    last = None
    while time.monotonic() < deadline:
        last = page.evaluate("() => state.job ? ({state: state.job.state, action: state.job.action, error: state.job.error}) : null")
        if last and (action is None or last["action"] == action):
            if last["state"] == "completed":
                return
            if last["state"] in {"failed", "cancelled"}:
                raise AssertionError("UI job did not succeed: " + json.dumps(last))
        page.wait_for_timeout(100)
    raise AssertionError("UI job did not complete: " + json.dumps(last))


'''
if 'def wait_for_completion' not in text:
    text = text.replace('def main():\n', helper + 'def main():\n', 1)
if 'page.wait_for_function(' in text:
    raise RuntimeError('Unconverted browser polling assertion')
p.write_text(text, encoding='utf-8')
shutil.rmtree(root / "_transfer")

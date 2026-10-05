"""Assemble checksum-verified source chunks once during repository import."""
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
shutil.rmtree(root / "_transfer")

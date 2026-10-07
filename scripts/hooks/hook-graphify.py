"""PyInstaller hook for the pinned public Graphify command, not a fork."""
from importlib.metadata import distributions
from PyInstaller.utils.hooks import collect_all, copy_metadata

datas,binaries,hiddenimports=collect_all('graphify')
datas+=copy_metadata('graphifyy',recursive=True)
# Dynamic grammar imports are declared upstream. Shipping metadata without the
# corresponding grammar modules would not be a complete public runtime.
for dist in distributions():
    name=dist.metadata['Name'].lower()
    if name.startswith('tree-sitter'):
        package=name.replace('-','_')
        d,b,h=collect_all(package)
        datas+=d;binaries+=b;hiddenimports+=h
for package in ['openai','tiktoken','tiktoken_ext']:
    d,b,h=collect_all(package)
    datas+=d;binaries+=b;hiddenimports+=h

for distribution_name in ["openai", "tiktoken"]:
    datas += copy_metadata(distribution_name, recursive=True)

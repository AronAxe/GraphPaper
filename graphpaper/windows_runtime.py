"""Repair only verified, bundled window DLL download marks, with explicit consent.

Never loads remote assemblies, changes machine security policy, or recursively
unblocks a user's folder. The per-build hashes live inside the frozen executable.
"""
from __future__ import annotations
import hashlib
import logging
import re
import stat
import sys
from pathlib import Path, PurePosixPath
from typing import Callable

PREFIXES = ('pythonnet/runtime/', 'webview/lib/', 'clr_loader/ffi/dlls/')
PRIMARY = 'pythonnet/runtime/Python.Runtime.dll'


class RuntimePackageError(RuntimeError):
    pass


class RepairDeclined(Exception):
    """The user chose not to trust the downloaded packaged DLLs. Exit quietly."""


def _path(root: Path, relative: str) -> Path:
    parts = PurePosixPath(relative).parts
    if (not relative.startswith(PREFIXES) or not relative.lower().endswith('.dll')
            or '\\' in relative or ':' in relative or '..' in parts
            or PurePosixPath(relative).is_absolute() or not parts):
        raise RuntimePackageError('Invalid bundled runtime path.')
    path = root
    for part in parts:
        path = path / part
        try:
            info = path.lstat()
        except FileNotFoundError as exc:
            raise RuntimePackageError('The application bundle is incomplete: '+relative+'. Extract the complete ZIP into a fresh folder.') from exc
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise RuntimePackageError('A bundled runtime path is a link or junction: '+relative)
    if not path.is_file() or root.resolve() not in path.resolve().parents:
        raise RuntimePackageError('Invalid bundled runtime file: '+relative)
    return path


def file_hash(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_bundle(root: Path, hashes: dict[str, str]) -> dict[str, Path]:
    if not hashes or PRIMARY not in hashes or len(hashes) > 100:
        raise RuntimePackageError('The packaged runtime manifest is missing. Extract a complete official GraphPaper release.')
    paths = {}
    for relative, expected in hashes.items():
        if not isinstance(expected, str) or not re.fullmatch('[a-f0-9]{64}', expected):
            raise RuntimePackageError('Invalid runtime checksum.')
        path = _path(root, relative)
        if file_hash(path) != expected:
            raise RuntimePackageError('The runtime file does not match this executable: '+relative+'. Do not mix files from different releases; extract the ZIP into a fresh folder.')
        paths[relative] = path
    return paths


def _zone(path: Path) -> Path:
    return Path(str(path)+':Zone.Identifier')


def repair_bundle(root: Path, hashes: dict[str, str], confirm: Callable[[list[str]], bool]) -> list[str]:
    """Return names repaired; default behavior cannot authorize itself."""
    paths = verify_bundle(root, hashes)
    marked = []
    for name, path in paths.items():
        try:
            with _zone(path).open('rb') as stream:
                value = stream.read(8192)
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise RuntimePackageError('Could not inspect the download mark on '+name+'. Check folder permissions.') from exc
        if re.search(rb'(?mi)^\s*ZoneId\s*=\s*[34]\s*$', value):
            marked.append(name)
    if not marked:
        return []
    if not confirm(marked):
        raise RepairDeclined()
    # The dialog can remain open a long time: verify all bytes and paths again
    # before making any changes. Do not trust an altered manifest on disk.
    paths = verify_bundle(root, hashes)
    for name in marked:
        try:
            _zone(paths[name]).unlink(missing_ok=True)
        except OSError as exc:
            raise RuntimePackageError('Could not unblock '+name+'. Close GraphPaper, open the downloaded ZIP Properties, choose Unblock, then extract into a fresh writable folder.') from exc
    logging.warning('Author approved removal of Internet-zone marks from bundled runtime files: %s', ', '.join(marked))
    return marked


def _confirm(names: list[str]) -> bool:
    import ctypes
    from ctypes import wintypes
    box = ctypes.WinDLL('user32', use_last_error=True).MessageBoxW
    box.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
    box.restype = ctypes.c_int
    message = ("Windows marked GraphPaper's window components as Internet downloads and may block them from loading.\n\n"
               "These files match the checksums embedded in this executable. Allow GraphPaper to remove their download marks?\n\n"
               + '\n'.join(names) +
               "\n\nChoose Yes only if you trust the GraphPaper release you downloaded. No documents, unrelated files or Windows-wide security settings will change. No cancels startup.")
    return box(None, message, 'GraphPaper runtime permission', 0x4 | 0x20 | 0x100) == 6


def prepare() -> list[str]:
    if sys.platform != 'win32' or not getattr(sys, 'frozen', False):
        return []
    from ._runtime_hashes import FILES
    return repair_bundle(Path(sys._MEIPASS), FILES, _confirm)


def startup_advice(error: Exception) -> str:
    text = str(error).lower()
    if isinstance(error, RuntimePackageError):
        return 'The packaged runtime could not be prepared. Your project data has not been replaced.'
    if 'python.runtime' in text or 'clr_loader' in text:
        return ('The Python/.NET bridge could not load. A downloaded-file block or mismatched runtime files can cause this. '
                'For an older build, right-click the original release ZIP, choose Properties > Unblock, and extract the complete ZIP into a fresh folder. '
                'If no Unblock checkbox exists or this persists, keep the local desktop.log for diagnosis; this message alone does not establish the cause.')
    if 'webview2' in text or 'edgechromium' in text:
        return 'The window renderer could not initialize. Check that Microsoft Edge WebView2 Runtime is installed; see desktop.log for the actual renderer error.'
    if '.net runtime' in text or 'netfx' in text:
        return 'The Windows .NET runtime could not initialize. Check the supported .NET Framework installation and desktop.log.'
    return 'See the actual error and GraphPaper\'s local desktop.log. A window-runtime reinstall is not a general remedy for this error.'

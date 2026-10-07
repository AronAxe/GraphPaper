"""Windows DPAPI / OS keyring. Never fall back to plaintext storage."""
from __future__ import annotations
import base64
import ctypes
import json
import os
from pathlib import Path


class Vault:
    NAMES = {"llm", "openrouter", "typesafe", "tavily", "ncbi", "semantic_scholar"}

    def __init__(self, root: Path):
        self.path = root / "credentials.dpapi"
        self.memory: dict[str, str] = {}
        self.keyring = None
        self.mode = "session only"
        if os.name == "nt":
            self.mode = "Windows DPAPI"
            if self.path.exists():
                try:
                    self.memory = json.loads(self._crypt(base64.b64decode(self.path.read_bytes()), False))
                except Exception:
                    # Corrupt or another Windows user's vault: never expose or guess.
                    self.memory = {}
        else:
            try:
                import keyring
                if keyring.get_keyring().priority > 0:
                    self.keyring = keyring
                    self.mode = "OS keyring"
            except Exception:
                pass

    @staticmethod
    def _crypt(raw: bytes, protect: bool) -> bytes:
        from ctypes import wintypes
        class BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]
        buffer = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
        source, target = BLOB(len(raw), buffer), BLOB()
        crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
        function = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
        function.restype = wintypes.BOOL
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p
        # CRYPTPROTECT_UI_FORBIDDEN; encrypted for current Windows user, not machine scope.
        ok = function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target))
        if not ok:
            raise OSError("Windows could not protect/unprotect credentials")
        try:
            return ctypes.string_at(target.pbData, target.cbData)
        finally:
            kernel32.LocalFree(target.pbData)

    def get(self, name: str) -> str:
        if name in self.memory:
            return self.memory[name]
        if self.keyring:
            try:
                v = self.keyring.get_password("GraphPaper", name)
                if v:
                    return v
            except Exception:
                pass
        env = {"llm": "OPENAI_API_KEY", "openrouter": "OPENROUTER_API_KEY", "typesafe": "TYPESAFE_API_KEY", "tavily": "TAVILY_API_KEY", "ncbi": "NCBI_API_KEY", "semantic_scholar": "SEMANTIC_SCHOLAR_API_KEY"}
        return os.getenv(env[name], "")

    def set(self, name: str, value: str, remember: bool):
        if name not in self.NAMES:
            raise ValueError("Unknown credential slot")
        self.memory[name] = value.strip()
        if os.name == "nt":
            if remember:
                temp = self.path.with_suffix(".tmp")
                temp.write_bytes(base64.b64encode(self._crypt(json.dumps(self.memory).encode(), True)))
                temp.replace(self.path)
            elif self.path.exists():
                self.path.unlink()
        elif self.keyring:
            try:
                if remember and value:
                    self.keyring.set_password("GraphPaper", name, value.strip())
                else:
                    self.keyring.delete_password("GraphPaper", name)
            except Exception:
                if remember:
                    self.mode = "session only"

    def forget_persistent(self):
        if self.path.exists():
            self.path.unlink()
        if self.keyring:
            for n in self.NAMES:
                try:
                    self.keyring.delete_password("GraphPaper", n)
                except Exception:
                    pass

    def flags(self):
        return {name: bool(self.get(name)) for name in self.NAMES}

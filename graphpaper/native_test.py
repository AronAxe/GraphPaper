"""Explicit, GitHub-hosted-only native test setup. Normal launches stay unchanged."""
from __future__ import annotations
import os
import sys
import tempfile
from pathlib import Path


def configure(port: str, environ=None):
    env=os.environ if environ is None else environ
    if sys.platform!='win32' or env.get('GITHUB_ACTIONS')!='true' or env.get('RUNNER_ENVIRONMENT')!='github-hosted':
        raise ValueError('The CI debugger option is restricted to GitHub-hosted Windows tests.')
    data=Path(env.get('GRAPHPAPER_DATA_DIR','')).resolve()
    if Path(tempfile.gettempdir()).resolve() not in data.parents or not data.name.startswith('GraphPaper-native-test-'):
        raise ValueError('The native test must use its own disposable project directory.')
    if not port.isascii() or not port.isdecimal() or not 1024<=int(port)<=65535:
        raise ValueError('Invalid native test debugger port.')
    # WebView2 on the hosted image does not forward the environment-only flag.
    # Use the supported pywebview setting; do not change CSP or expose new bridge methods.
    import webview
    webview.settings['REMOTE_DEBUGGING_PORT']=int(port)

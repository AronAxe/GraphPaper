"""Regression: Pythonw/PyInstaller --windowed do not provide console streams."""
import sys
from unittest.mock import patch
from fastapi import FastAPI
from graphpaper.desktop import server_config


def test_desktop_server_configuration_without_console_streams():
    with patch.object(sys, 'stdout', None), patch.object(sys, 'stderr', None):
        config = server_config(FastAPI(), log_level='warning', access_log=False)
        config.load()
    assert config.log_config is None
    assert config.loaded

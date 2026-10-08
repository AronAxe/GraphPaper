import sys
from types import SimpleNamespace
import pytest
from graphpaper.native_test import configure


def environment(tmp_path):
    return {'GITHUB_ACTIONS':'true','RUNNER_ENVIRONMENT':'github-hosted','GRAPHPAPER_DATA_DIR':str(tmp_path/'GraphPaper-native-test-fixture')}


def test_native_debugger_uses_the_official_setting_only_in_isolated_ci(tmp_path,monkeypatch):
    monkeypatch.setattr(sys,'platform','win32')
    monkeypatch.setattr('graphpaper.native_test.tempfile.gettempdir',lambda:str(tmp_path))
    webview=SimpleNamespace(settings={'REMOTE_DEBUGGING_PORT':None})
    monkeypatch.setitem(sys.modules,'webview',webview)
    configure('54321',environment(tmp_path))
    assert webview.settings=={'REMOTE_DEBUGGING_PORT':54321}


@pytest.mark.parametrize('replacement',[{'GITHUB_ACTIONS':'false'},{'RUNNER_ENVIRONMENT':'self-hosted'},{'GRAPHPAPER_DATA_DIR':'C:/Users/owner/AppData/Local/GraphPaper'},{'GRAPHPAPER_DATA_DIR':''}])
def test_normal_user_environment_is_rejected(tmp_path,monkeypatch,replacement):
    monkeypatch.setattr(sys,'platform','win32')
    monkeypatch.setattr('graphpaper.native_test.tempfile.gettempdir',lambda:str(tmp_path))
    with pytest.raises(ValueError):configure('54321',{**environment(tmp_path),**replacement})


@pytest.mark.parametrize('port',['0','80','65536','bad','1234 --other-flag','١٢٣٤'])
def test_debugger_argument_is_an_explicit_bounded_port(tmp_path,monkeypatch,port):
    monkeypatch.setattr(sys,'platform','win32')
    monkeypatch.setattr('graphpaper.native_test.tempfile.gettempdir',lambda:str(tmp_path))
    with pytest.raises(ValueError):configure(port,environment(tmp_path))

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import hashlib
import json
import pytest

from graphpaper.desktop import DesktopBridge
from graphpaper.graph import import_graph
from graphpaper.pipeline import Job
from scripts.publish_gui import package_files


def test_native_close_does_not_need_eval():
    bridge=DesktopBridge(None)
    bridge._window=Mock()
    assert bridge.notify_ready()
    assert bridge.request_close()=={"closed":True}
    assert bridge._close_authorized
    bridge._window.destroy.assert_called_once()


def test_native_close_preserves_running_job_when_declined():
    bridge=DesktopBridge(None,SimpleNamespace(jobs={"j":SimpleNamespace(state="running")}))
    bridge._window=Mock()
    bridge._window.create_confirmation_dialog.return_value=False
    assert bridge.request_close()=={"closed":False}
    bridge._window.destroy.assert_not_called()
    assert not bridge._close_authorized


def test_graph_import_bad_edge_is_validation_error():
    with pytest.raises(ValueError,match="edge must"):
        import_graph({"nodes":[{"id":"a"}],"edges":[None]})


def test_invalid_reported_cost_is_not_serialized():
    j=Job("p","test")
    j.before_call("test",10)
    j.record_usage("test",{"cost":float("nan"),"input_tokens":4},"test")
    assert j.receipts[-1]["cost"] is None
    assert j.usage["unpriced_calls"]==1
    json.dumps(j.public(),allow_nan=False)


def write_manifest(root,files):
    (root/"publish-manifest.json").write_text(json.dumps({"repository":"AronAxe/GraphPaper","files":files}))


def test_publisher_uses_verified_allowlist_not_extra_files(tmp_path):
    (tmp_path/"README.md").write_text("hello")
    (tmp_path/"private.db").write_text("never upload")
    write_manifest(tmp_path,{"README.md":hashlib.sha256(b"hello").hexdigest()})
    assert package_files(tmp_path)==[tmp_path/"README.md"]


def test_publisher_rejects_edited_package(tmp_path):
    (tmp_path/"README.md").write_text("edited")
    write_manifest(tmp_path,{"README.md":hashlib.sha256(b"hello").hexdigest()})
    with pytest.raises(ValueError,match="changed"):
        package_files(tmp_path)


@pytest.mark.parametrize("name",["../secret","/absolute",".git/config","C:/secret"])
def test_publisher_rejects_unsafe_manifest_paths(tmp_path,name):
    write_manifest(tmp_path,{name:"any"})
    with pytest.raises(ValueError,match="Unsafe"):
        package_files(tmp_path)

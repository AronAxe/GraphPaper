"""Regression coverage for native API reflection and UI-thread close dispatch."""
import threading
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from graphpaper.desktop import DesktopBridge


def test_public_bridge_contains_only_explicit_rpc_methods():
    bridge=DesktopBridge(Mock(), Mock())
    bridge._window=Mock()
    public={name:getattr(bridge,name) for name in dir(bridge) if not name.startswith('_')}
    assert set(public)=={'cancel_close','notify_ready','request_close','save_export'}
    assert all(callable(v) for v in public.values())
    for name in ['window','store','runner']:
        with pytest.raises(AttributeError):setattr(bridge,name,Mock())


def test_os_close_returns_before_slow_js_dispatch_finishes():
    entered=threading.Event();release=threading.Event()
    def run_js(script):
        assert script=='window.graphpaperRequestClose()'
        entered.set();release.wait(3)
    bridge=DesktopBridge(None);bridge._window=Mock();bridge._window.run_js.side_effect=run_js
    bridge.notify_ready()
    try:
        assert bridge._on_closing() is False
        assert entered.wait(1)
        assert not bridge._close_authorized
        assert bridge._on_closing() is False
        assert bridge._window.run_js.call_count==1
    finally:release.set()


def test_failed_save_can_reset_close_request():
    bridge=DesktopBridge(None)
    bridge._close_pending.set()
    assert bridge.cancel_close() is True
    assert not bridge._close_pending.is_set()


def test_declining_busy_close_allows_another_attempt():
    bridge=DesktopBridge(None,SimpleNamespace(jobs={'j':SimpleNamespace(state='running')}))
    bridge._window=Mock();bridge._window.create_confirmation_dialog.return_value=False
    bridge._close_pending.set()
    assert bridge.request_close()=={'closed':False}
    assert not bridge._close_pending.is_set()
    assert not bridge._close_authorized
    bridge._window.destroy.assert_not_called()


def test_authorized_close_never_dispatches_javascript_again():
    bridge=DesktopBridge(None);bridge._window=Mock();bridge.notify_ready()
    bridge._close_authorized=True
    assert bridge._on_closing() is True
    bridge._window.run_js.assert_not_called()


def test_native_close_worker_handles_failed_js_without_losing_save_choice():
    bridge=DesktopBridge(None);bridge._window=Mock()
    bridge._window.run_js.side_effect=RuntimeError('The renderer is unavailable')
    bridge._window.create_confirmation_dialog.return_value=False
    bridge._close_pending.set();bridge._ask_ui_to_close()
    assert not bridge._close_pending.is_set()
    assert not bridge._close_authorized
    bridge._window.destroy.assert_not_called()

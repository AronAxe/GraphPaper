"""Downloaded portable builds need scoped, consented runtime repair, not a global unblock."""
import hashlib
import importlib.util
from pathlib import Path
import pytest


def runtime():
    assert importlib.util.find_spec('graphpaper.windows_runtime'), 'Downloaded-runtime handling is missing'
    from graphpaper import windows_runtime
    return windows_runtime


def bundle(tmp_path):
    root=tmp_path/'_internal'
    path=root/'pythonnet/runtime/Python.Runtime.dll'
    path.parent.mkdir(parents=True)
    path.write_bytes(b'packaged assembly fixture')
    hashes={'pythonnet/runtime/Python.Runtime.dll':hashlib.sha256(path.read_bytes()).hexdigest()}
    return root,path,hashes


def tag(path):
    return Path(str(path)+':Zone.Identifier')


def test_marked_runtime_repair_preserves_bytes_and_unrelated_files(tmp_path):
    mod=runtime();root,path,hashes=bundle(tmp_path)
    tag(path).write_text('[ZoneTransfer]\nZoneId=3\n')
    other=root/'unrelated.dll';other.write_bytes(b'not ours');tag(other).write_text('ZoneId=3')
    document=tmp_path/'my project.txt';document.write_text('Author words');tag(document).write_text('ZoneId=3')
    prompts=[]
    result=mod.repair_bundle(root,hashes,lambda names:prompts.append(names) or True)
    assert result==['pythonnet/runtime/Python.Runtime.dll']
    assert prompts==[['pythonnet/runtime/Python.Runtime.dll']]
    assert not tag(path).exists()
    assert hashlib.sha256(path.read_bytes()).hexdigest()==hashes[result[0]]
    assert tag(other).exists() and tag(document).exists() and document.read_text()=='Author words'


def test_declined_repair_changes_nothing(tmp_path):
    mod=runtime();root,path,hashes=bundle(tmp_path);tag(path).write_text('ZoneId=3')
    with pytest.raises(mod.RepairDeclined):mod.repair_bundle(root,hashes,lambda names:False)
    assert tag(path).exists()


def test_unmarked_runtime_does_not_prompt(tmp_path):
    mod=runtime();root,path,hashes=bundle(tmp_path)
    assert mod.repair_bundle(root,hashes,lambda _:pytest.fail('Unexpected consent prompt'))==[]


def test_corrupt_assembly_is_not_unblocked(tmp_path):
    mod=runtime();root,path,hashes=bundle(tmp_path);path.write_bytes(b'changed');tag(path).write_text('ZoneId=3')
    # Truncating the primary stream can remove Windows ADS: mark the replaced fixture afterward.
    assert tag(path).exists()
    with pytest.raises(mod.RuntimePackageError,match='match'):mod.repair_bundle(root,hashes,lambda _:pytest.fail('Do not ask to trust mismatched files'))
    assert tag(path).exists()


@pytest.mark.parametrize('relative',['../outside.dll','/root/evil.dll','webview/lib/../../evil.dll','webview/lib/x.dll:other','vendor/evil.dll'])
def test_manifest_cannot_escape_runtime_allowlist(tmp_path,relative):
    mod=runtime();root,path,hashes=bundle(tmp_path);hashes[relative]='0'*64
    with pytest.raises(mod.RuntimePackageError):mod.repair_bundle(root,hashes,lambda _:True)


def test_symlink_not_followed(tmp_path):
    mod=runtime();root,path,hashes=bundle(tmp_path);outside=tmp_path/'other.dll';outside.write_bytes(path.read_bytes());path.unlink()
    try:path.symlink_to(outside)
    except OSError:pytest.skip('Account cannot create symlinks')
    tag(outside).write_text('ZoneId=3')
    with pytest.raises(mod.RuntimePackageError):mod.repair_bundle(root,hashes,lambda _:True)
    assert tag(outside).exists()


def test_changed_during_consent_is_rechecked(tmp_path):
    mod=runtime();root,path,hashes=bundle(tmp_path);tag(path).write_text('ZoneId=3')
    def consent(_):
        path.write_bytes(b'changed while dialog was open')
        tag(path).write_text('ZoneId=3')
        assert tag(path).exists()
        return True
    with pytest.raises(mod.RuntimePackageError,match='match'):mod.repair_bundle(root,hashes,consent)
    assert tag(path).exists()


def test_error_message_does_not_misdiagnose_pythonnet_as_webview():
    mod=runtime()
    text=mod.startup_advice(RuntimeError('Failed to resolve Python.Runtime.Loader.Initialize from D:\\Programs\\GraphPaper\\_internal\\pythonnet\\runtime\\Python.Runtime.dll'))
    assert 'Unblock' in text and 'WebView2' not in text
    assert 'WebView2' in mod.startup_advice(RuntimeError('WebView2 Runtime not found'))
    assert 'WebView2' not in mod.startup_advice(RuntimeError('Database is locked'))

import hashlib
from pathlib import Path
import zipfile
import pytest
from scripts.package_windows import package,sha256


def test_streamed_package_and_checksum(tmp_path):
    folder=tmp_path/'GraphPaper';(folder/'_internal/ui').mkdir(parents=True)
    (folder/'GraphPaper.exe').write_bytes(b'test executable fixture')
    (folder/'_internal/ui/app.js').write_text('test fixture',encoding='utf-8')
    target=tmp_path/'result.zip'
    size,digest=package(folder,target)
    assert size==target.stat().st_size and digest==hashlib.sha256(target.read_bytes()).hexdigest()
    assert digest==sha256(target)
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        assert z.read('GraphPaper/GraphPaper.exe')==b'test executable fixture'
        assert 'GraphPaper/_internal/ui/app.js' in z.namelist()
    assert not target.with_suffix('.zip.tmp').exists()


def test_packager_requires_complete_application(tmp_path):
    folder=tmp_path/'GraphPaper';folder.mkdir()
    with pytest.raises(ValueError):package(folder,tmp_path/'result.zip')
    (folder/'GraphPaper.exe').write_bytes(b'fixture')
    with pytest.raises(ValueError,match='interface'):package(folder,tmp_path/'result.zip')


def test_package_output_cannot_recurse_into_itself(tmp_path):
    folder=tmp_path/'GraphPaper';folder.mkdir();(folder/'GraphPaper.exe').write_bytes(b'fixture')
    with pytest.raises(ValueError,match='outside'):package(folder,folder/'result.zip')

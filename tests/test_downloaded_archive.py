"""The downloaded-build gate resolves its extraction root before containment checks."""
from pathlib import Path
import zipfile
import pytest
from scripts import check_downloaded_release as checker


def extract(archive,target):
    assert hasattr(checker,'extract_archive'), 'Safe fresh-archive extraction helper is missing'
    return checker.extract_archive(archive,target)


def archive_at(tmp_path,name):
    archive=tmp_path/'package.zip'
    with zipfile.ZipFile(archive,'w') as z:z.writestr(name,b'fixture')
    return archive


def test_regular_archive_extracts(tmp_path):
    archive=archive_at(tmp_path,'GraphPaper/GraphPaper.exe')
    target=tmp_path/'unpacked';target.mkdir()
    root=extract(archive,target)
    assert root==target.resolve() and (root/'GraphPaper/GraphPaper.exe').read_bytes()==b'fixture'


def test_aliased_root_is_resolved_on_both_sides(tmp_path):
    target=tmp_path/'real';target.mkdir();alias=tmp_path/'alias'
    try:alias.symlink_to(target,target_is_directory=True)
    except OSError:pytest.skip('Account cannot create directory aliases')
    archive=archive_at(tmp_path,'GraphPaper/GraphPaper.exe')
    root=extract(archive,alias)
    assert root==target.resolve() and (root/'GraphPaper/GraphPaper.exe').is_file()


@pytest.mark.parametrize('name',['../escaped.txt','C:/escaped.txt','/escaped.txt'])
def test_unsafe_archive_rejected_before_extraction(tmp_path,name):
    archive=archive_at(tmp_path,name);target=tmp_path/'unpacked';target.mkdir()
    with pytest.raises(ValueError,match='Unsafe ZIP entry'):extract(archive,target)
    assert not list(target.iterdir())

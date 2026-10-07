"""Validation and compatibility tests for external graph results."""
import time
import pytest
from graphpaper.graphify_adapter import validate_graph,load_graph,source_refs
from graphpaper.graphify_runtime import check_runtime
from graphpaper.graphify_gateway import JobScope
from graphpaper.pipeline import Job
from graphpaper.models import Source
from graphpaper.providers import ProviderError,Cancelled


@pytest.mark.parametrize('raw',[{},[],{'nodes':[],'edges':[]},{'nodes':[{'id':'a'}]},
    {'nodes':[{'id':'a'},{'id':'a'}],'edges':[]},
    {'nodes':[{'id':'a'}],'edges':[{'source':'a','target':'missing'}]},
    {'nodes':[{'id':False}],'edges':[]},
    {'nodes':[{'id':'a','label':None}],'edges':[]}])
def test_invalid_graph_is_not_installed(raw):
    with pytest.raises(ValueError):validate_graph(raw)


def test_json_must_be_complete_and_finite(tmp_path):
    path=tmp_path/'graph.json'
    for content in ['{"nodes":[','{"nodes":[{"id":"a"}],"edges":[],"weight":NaN}']:
        path.write_text(content)
        with pytest.raises(ValueError):load_graph(path,tmp_path)


def test_custom_runtime_path_must_exist(tmp_path):
    status=check_runtime(str(tmp_path/'not-installed.exe'))
    assert not status['available'] and status['selection']=='custom'


def test_file_attribution_is_limited_to_exported_sources(tmp_path):
    root=tmp_path/'input';root.mkdir()
    files={'source-0001.md':Source(id='S1',title='Synthetic document',text='Text.')}
    assert source_refs({'source_file':'source-0001.md'},files,root)==['S1']
    assert source_refs({'source_file':'unknown.md'},files,root)==[]
    assert source_refs({'source_file':'other/source-0001.md'},files,root)==[]


def test_expired_job_scope_reports_timeout():
    job=Job('synthetic','graph')
    scope=JobScope(job,10)
    # Windows Python 3.12 can expose a coarse monotonic clock. Test the
    # expiry predicate deterministically; the process test covers real time.
    scope.deadline=time.monotonic()-1
    with pytest.raises(ProviderError,match='timeout'):scope.check()


def test_cancelled_scope_and_late_accounting():
    job=Job('synthetic','graph');scope=JobScope(job,10)
    job.cancel.set()
    with pytest.raises(Cancelled):scope.check()
    job.cancel.clear();scope.close()
    before=dict(job.usage)
    scope.record_usage('fixture',{'input_tokens':200},'fixture')
    assert job.usage==before

import copy
import json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from graphpaper.models import Project,VoiceProfile,Source
from graphpaper.voice_library import VoiceLibrary
from graphpaper.storage import Store
from graphpaper.desktop import DesktopBridge


def test_native_voice_export_uses_existing_explicit_save_bridge(tmp_path,monkeypatch):
    import sys
    store=Store(tmp_path);library=VoiceLibrary(store)
    v=library.create(VoiceProfile(name='Power voice',instructions='Keep the fucking point and comic timing.'),
        [Source(id='S1',title='Private training',role='voice',text='SECRET_TRAINING_TEXT')])
    target=tmp_path/'voice.json'
    monkeypatch.setitem(sys.modules,'webview',SimpleNamespace(FileDialog=SimpleNamespace(SAVE=1)))
    bridge=DesktopBridge(store);bridge._window=Mock()
    bridge._window.create_file_dialog.return_value=str(target)
    assert bridge.save_export(v.id,'voice')=={'saved':True}
    value=json.loads(target.read_text())
    assert value['format']=='graphpaper-voice-1'
    assert 'fucking' in target.read_text()
    assert 'SECRET_TRAINING_TEXT' not in target.read_text()
    assert not value['profile']['sample_ids']
    assert set(name for name in dir(bridge) if callable(getattr(bridge,name)) and not name.startswith('_'))=={'notify_ready','request_close','cancel_close','save_export'}


def test_training_bounds_apply_before_creating_a_library_entry(tmp_path):
    library=VoiceLibrary(Store(tmp_path))
    samples=[Source(id=f'S{i}',title='Training',role='voice',text='Some writing.') for i in range(25)]
    with pytest.raises(ValueError,match='24'):library.create(samples=samples)
    assert library.list()==[]


def test_manual_project_override_replaces_the_derived_graph(client,app):
    p=Project(voice_profile=VoiceProfile(instructions='Understated by default.'))
    app.state.store.create(p)
    library=app.state.voices;v=library.create(p.voice_profile);library.apply(p,v);app.state.store.save(p,0)
    p=app.state.store.get(p.id);before=copy.deepcopy(p.voice_profile.graph)
    profile=p.voice_profile.model_dump();profile['instructions']='Use uncompromising power language for this piece.';profile['graph']={}
    r=client.patch('/api/projects/'+p.id,json={'version':p.version,'voice_profile':profile})
    assert r.status_code==200
    from graphpaper.voice import voice_context
    context=voice_context(app.state.store.get(p.id))
    assert 'power language' in str(context['graph'])
    assert library.get(v.id)[0].profile.graph==before

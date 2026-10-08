from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'tests/test_voice_library.py';t=p.read_text(encoding='utf-8')
old='    app.state.runner.clients_factory=ScriptedClients'
new='''    class VoiceClients(ScriptedClients):
        def complete(self,system,user,**kwargs):
            data=json.loads(user)
            if data.get('task','').startswith('Build an editable author voice profile'):
                self._record('extraction')
                assert 'samples' in data and 'Original writing' in str(data['samples'])
                return {'name':'Reusable fixture','instructions':'Preserve incisive phrasing, varied rhythm and the author\\'s forceful conclusion.','observations':['Synthetic material only.']}
            return super().complete(system,user,**kwargs)
    app.state.runner.clients_factory=VoiceClients'''
assert t.count(old)==1;t=t.replace(old,new).replace("assert status['state']=='completed',status","assert status['state']=='completed',status.get('error',status)")
p.write_text(t,encoding='utf-8',newline='\n')
p=root/'ui/studio.js';t=p.read_text(encoding='utf-8');old="if(v.instructions!==state.p.voice_profile.instructions)v.sample_hash='';";new="if(v.instructions!==state.p.voice_profile.instructions){v.sample_hash='';v.graph={};}";assert t.count(old)==1;p.write_text(t.replace(old,new),encoding='utf-8',newline='\n')
print('Voice-learning fixture now exercises the actual profile schema; manual project voice overrides invalidate the derived graph.')

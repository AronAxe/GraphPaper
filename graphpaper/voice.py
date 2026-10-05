"""Author-controlled voice profiles. Samples guide style, never factual support."""
from __future__ import annotations
import hashlib
import json
import re
import statistics
from .models import now


def samples(project):
    return [s for s in project.sources if s.enabled and s.role == 'voice']


def fingerprint(project):
    return hashlib.sha256(json.dumps([(s.id, hashlib.sha256(s.text.encode()).hexdigest()) for s in samples(project)]).encode()).hexdigest()


def metrics(text):
    words = re.findall(r"\b[\w]+(?:['’][\w]+)?\b", text)
    sentences = [len(re.findall(r'\w+', s)) for s in re.split(r'[.!?]+(?:\s|$)', text) if re.search(r'\w', s)]
    paragraphs = [len(re.findall(r'\w+', s)) for s in re.split(r'\n\s*\n', text) if s.strip()]
    return {'words': len(words), 'sentences': len(sentences), 'mean_sentence_words': round(statistics.mean(sentences), 1) if sentences else 0,
            'sentence_variation': round(statistics.pstdev(sentences), 1) if sentences else 0,
            'mean_paragraph_words': round(statistics.mean(paragraphs), 1) if paragraphs else 0,
            'questions_per_1000_words': round(text.count('?') * 1000 / max(1, len(words)), 1),
            'dashes_per_1000_words': round(len(re.findall('[—–]', text)) * 1000 / max(1, len(words)), 1)}


def sample_pack(project, budget=24000):
    """Balanced start/middle/end excerpts, not just the first article's introduction."""
    selected = samples(project)
    if not selected:
        return []
    selected = selected[:24]
    per_source = max(200, budget // len(selected))
    result = []
    for s in selected:
        if len(s.text) <= per_source:
            excerpts = [s.text]
        else:
            width = per_source // 3
            middle = max(0, len(s.text)//2 - width//2)
            excerpts = [s.text[:width], s.text[middle:middle+width], s.text[-width:]]
        result.append({'source_id': s.id, 'title': s.title, 'excerpts': excerpts})
    return result


def voice_context(project, budget=9000):
    profile = project.voice_profile
    if not profile.enabled or profile.strength == 0:
        return {'enabled': False}
    stale = bool(profile.sample_hash and profile.sample_hash != fingerprint(project))
    return {'enabled': True, 'influence_percent': profile.strength,
            'instructions': profile.instructions if not stale else '',
            'profile_needs_refresh': stale,
            'samples': sample_pack(project, budget),
            'rule': 'Match authorial choices, rhythm, diction and wit, not specific sentences or personal experiences. Samples are style material only, not facts. Preserve deliberate literary devices and the brief. Do not invent lived experience. A stale profile is ignored; current samples still guide style.'}


def learn_voice(project, clients, job):
    from .providers import ProviderError
    from .pipeline import BOUNDARY
    from .models import VoiceProfile
    material = samples(project)
    if not material:
        raise ValueError('Add writing samples using the Voice role first.')
    if sum(len(s.text.split()) for s in material) < 80:
        raise ValueError('Use at least 80 words of your writing; several full pieces produce a more representative profile.')
    job.note('Learning rhythm, diction, structure and rhetorical habits from your selected writing.', 15)
    budget = min(28000, max(4000, clients.settings.context_chars - 9000))
    raw = clients.complete(BOUNDARY,
        json.dumps({'task': 'Build an editable author voice profile from these samples. Observe prose mechanics, not personality, identity, factual beliefs or biography. Distinguish recurring choices from one-off subject matter. Preserve nuanced qualifiers and intentional punctuation; do not impose a generic casual style. Produce instructions usable for both new writing and faithful editing. Note limited or mixed evidence. Do not quote or copy distinctive sample sentences.',
                    'samples': sample_pack(project, budget), 'measured_style': [metrics(s.text) for s in material],
                    'output_schema': {'name': 'Short author voice label', 'instructions': 'Specific prose guidance with headings for rhythm, diction, structure, stance, humor, imagery, punctuation, fiction/nonfiction differences and avoidances.', 'observations': ['Short, evidence-limited observations']}}, ensure_ascii=False),
        role='extraction', json_mode=True)
    if not isinstance(raw.get('instructions'), str) or len(raw['instructions'].strip()) < 30:
        raise ProviderError('The model did not return a usable voice profile. Existing profile preserved.')
    project.voice_profile = VoiceProfile(name=str(raw.get('name', 'My writing voice'))[:160], instructions=raw['instructions'][:12000],
        enabled=True, strength=project.voice_profile.strength, sample_ids=[s.id for s in material], sample_hash=fingerprint(project),
        learned_at=now(), metrics=metrics('\n\n'.join(s.text for s in material)),
        observations=[str(x)[:500] for x in raw.get('observations', [])[:12]])
    job.note('Voice profile ready. Edit it, adjust its influence, or switch it off.', 95)

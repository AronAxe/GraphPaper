"""Prose craft tools: explainable local lint plus reversible model-assisted edits."""
from __future__ import annotations
from collections import Counter
import difflib
import hashlib
import json
import re
from .voice import metrics, voice_context

# Independent editorial heuristics informed by the projects credited in docs/UPDATE-0.2.md.
RULES = [
 ('staged-opening', r"\b(?:let['’]s (?:dive in|delve|explore)|without further ado|here['’]s what you need to know|in today['’]s (?:fast[- ]paced|rapidly evolving|digital) (?:world|landscape))\b", 'Open with the actual point rather than announcing it.'),
 ('empty-emphasis', r'\b(?:a testament to|pivotal moment|plays a (?:crucial|vital|key) role|cannot be overstated|game[- ]changer|revolutionary breakthrough)\b', 'Replace inflated importance with a supported mechanism or consequence.'),
 ('staged-contrast', r"\bnot (?:just|merely|only)\b[^.!?\n]{1,150}\bbut\b", 'Keep this contrast only when both halves do real argumentative work.'),
 ('vague-authority', r'\b(?:experts agree|studies show|research suggests|many believe|it is widely (?:known|believed))\b', 'Name the source or keep the attribution appropriately limited.'),
 ('stock-transition', r'(?m)^\s*(?:Moreover|Furthermore|Additionally|In conclusion|In summary|To sum up)[,:]', 'Check whether the transition adds meaning or repeats a template.'),
 ('stacked-hedges', r'\b(?:could potentially|might possibly|may perhaps|potentially possibly)\b', 'Remove redundant qualifiers, not genuine scientific uncertainty.'),
 ('filler', r'\b(?:it is (?:important|worthwhile|essential) to (?:note|mention|remember)|at the end of the day|in order to|the fact of the matter is)\b', 'Say the useful part directly.'),
 ('empty-closer', r'\b(?:let that sink in|read that again|that is the real (?:win|lesson)|the future is bright|only time will tell)\b', 'End with a concrete development, not a repeated moral.'),
 ('corporate-language', r'\b(?:leverage synergies|unlock (?:the )?(?:full )?potential|seamless integration|holistic approach|ever[- ]evolving landscape|rich tapestry)\b', 'Prefer the exact action, relationship or image.'),
 ('chat-wrapper', r"(?m)^\s*(?:Certainly!|Absolutely!|Here is (?:the|your) (?:revised|rewritten)|I hope this helps)", 'Remove chat scaffolding from the manuscript.'),
]
PROTECTED = re.compile(r'(?ms)```.*?```|~~~.*?~~~|^---\n.*?\n---(?=\n|$)|^>[^\n]*(?:\n>[^\n]*)*|`[^`\n]+`|\[[^\]\n]*\]\([^\)\n]+\)|\[S\d+\]|https?://[^\s<>]+|“[^”]+”|"[^"\n]+"|(?<!\w)[+-]?\d+(?:[.,:/-]\d+)*(?:\s?%|\b)')


def mask(text):
    nonce = hashlib.sha256(text.encode()).hexdigest()[:10]
    saved = {}
    def keep(match):
        token = f'GPKEEP{nonce}X{len(saved)}END'
        saved[token] = match.group(0)
        return token
    return PROTECTED.sub(keep, text), saved


def unmask(text, saved):
    for token, original in saved.items():
        if text.count(token) != 1:
            raise ValueError('The edit changed a protected quotation, number, citation, link or code span. It was not applied; try a lighter edit.')
    if set(re.findall(r'GPKEEP[a-f0-9]+X\d+END', text)) != set(saved):
        raise ValueError('The edit introduced an unknown protected-span marker.')
    for token, original in saved.items():
        text = text.replace(token, original)
    return text


def lint(text):
    masked = list(text)
    for m in PROTECTED.finditer(text):
        masked[m.start():m.end()] = ' ' * (m.end()-m.start())
    prose = ''.join(masked)
    findings = []
    for key, pattern, suggestion in RULES:
        for m in re.finditer(pattern, prose, re.I):
            findings.append({'rule': key, 'start': m.start(), 'end': m.end(), 'excerpt': text[m.start():m.end()], 'suggestion': suggestion})
            if len(findings) >= 160:
                break
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', prose) if p.strip()]
    openings = Counter(' '.join(re.findall(r'\w+', p.lower())[:3]) for p in paragraphs)
    repeated = [k for k, count in openings.items() if count >= 3 and len(k.split()) == 3]
    return {'findings': findings[:160], 'count': len(findings), 'repeated_openings': repeated[:15], 'metrics': metrics(text),
            'note': 'Editorial cues, not AI-authorship detection. Deliberate repetition, dashes, formal vocabulary and genuine uncertainty may be correct. English-specific phrase cues; the model edit can work in the manuscript language.'}


def polish_draft(project, clients, job, mode, instruction=''):
    from .editorial import system as editorial_system, context as editorial_context, review_stamp
    from .models import PolishCandidate, now
    from .providers import ProviderError
    if mode not in {'humanize', 'deslop', 'both'}:
        raise ValueError('Unknown prose edit mode.')
    original = project.draft
    if not original.strip():
        raise ValueError('Write or generate a draft first.')
    before = lint(original)
    masked, saved = mask(original)
    job.note('Inspecting prose habits and preserving quotations, citations, numbers, links and code.', 10)
    task = ('HUMANIZE: make this sound like the author, with purposeful rhythm, natural syntax and concrete existing detail. '
            if mode == 'humanize' else 'DESLOP: remove filler, repeated conclusions, stock emphasis, staged contrasts, vague authority and templated cadence. '
            if mode == 'deslop' else 'HUMANIZE AND DESLOP: remove formulaic filler while restoring the author’s natural rhythm and specificity. ')
    prompt = {'task': task + 'Return the complete revised Markdown only. Use the same language. Preserve every material claim, uncertainty, causal direction, named entity, narrator, character motivation and intended ending. Do not invent personal experiences, facts, anecdotes, evidence or additional scenes. Do not mechanically ban punctuation or replace every formal word. Author samples override generic style rules. Every GPKEEP marker must remain exactly once, in its correct semantic position. Markers conceal protected spans; do not rewrite, renumber or infer new contents for them.',
              'mode': project.mode, 'brief': project.brief.model_dump(), 'voice': voice_context(project),
              'author_instruction': instruction, 'lint': before, 'draft': masked, **editorial_context(project)}
    candidate = clients.complete(editorial_system(project, "polish"), json.dumps(prompt, ensure_ascii=False), role='editor')
    candidate = unmask(candidate, saved)
    if Counter(m.group(0) for m in PROTECTED.finditer(original)) != Counter(m.group(0) for m in PROTECTED.finditer(candidate)):
        raise ProviderError('The proposed edit introduced or altered protected factual material. Original preserved.')
    if len(candidate.strip()) < max(20, len(original.strip()) * .3):
        raise ProviderError('The proposed edit discarded too much of the manuscript. Original preserved.')
    job.note('Checking the edit for meaning drift before presenting it beside the original.', 65)
    review = clients.complete(editorial_system(project, "polish"), json.dumps({'task': 'Compare original and proposed prose edit. Identify factual/semantic drift, altered named entities, lost qualifiers or reordered citations that no longer support their claims. For fiction also check narrator, scene events, motivation and ending. Judge fidelity separately from fluency. Preserve the intended thesis, indignation, satire, humor and force; polite equivocation is a meaning change, not an improvement. Distinguish essential factual qualifiers from gratuitous caveats. Return an honest review. Do not rewrite.', 'mode': project.mode, 'original': original, 'candidate': candidate, 'author_instruction': instruction, **editorial_context(project),
        'schema': {'meaning_preserved': True, 'stance_preserved': True, 'voice_preserved': True, 'summary': 'Specific editorial assessment', 'warnings': ['Concrete risks or unresolved differences'], 'improvements': ['Specific changes']}}, ensure_ascii=False), role='editor', json_mode=True)
    if not isinstance(review.get('meaning_preserved'), bool):
        raise ProviderError('The edit reviewer did not provide a valid fidelity assessment. Original preserved.')
    if review.get('stance_preserved') is False:
        review['meaning_preserved'] = False
    project.polish = PolishCandidate(mode=mode, context_hash=review_stamp(project), original_hash=hashlib.sha256(original.encode()).hexdigest(), draft=candidate,
        created=now(), review=review, before=before, after=lint(candidate), protected_spans=len(saved),
        diff=list(difflib.unified_diff(original.splitlines(), candidate.splitlines(), fromfile='Original', tofile='Proposed', lineterm=''))[:12000])
    job.note('Proposed edit ready. Compare the versions and explicitly accept or discard it.', 95)

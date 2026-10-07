"""Provider-native reasoning controls. Catalogued levels are never silently remapped."""
from __future__ import annotations
import re
from typing import Any

DEFAULT = 'default'
PROTOCOL_LEVELS = ['none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max']
ORDER = ['none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra']


def clean_levels(raw) -> list[str]:
    if not isinstance(raw, list):
        return []
    result = []
    for item in raw:
        value = item.get('reasoningEffort', item.get('effort', item.get('value', ''))) if isinstance(item, dict) else item
        if isinstance(value, str) and re.fullmatch(r'[a-z][a-z0-9_-]{0,31}', value) and value not in result:
            result.append(value)
    return result


def normalize_model(raw: dict, provider: str) -> dict:
    ident = raw.get('model') if provider == 'codex' else raw.get('id')
    ident = ident or raw.get('id', '')
    explicit = next((raw[k] for k in ['supportedReasoningEfforts', 'supported_reasoning_efforts', 'reasoning_efforts'] if isinstance(raw.get(k), list)), None)
    levels = clean_levels(explicit)
    caps = raw.get('capabilities') or {}
    effort = caps.get('effort') or caps.get('reasoning_effort') or {}
    if explicit is None and isinstance(effort, dict) and 'supported' in effort:
        explicit = [k for k, v in effort.items() if isinstance(v, dict) and v.get('supported') and k != 'supported']
        levels = clean_levels(explicit)
    params = raw.get('supported_parameters')
    source = 'model catalog' if explicit is not None else 'provider vocabulary; per-model support not advertised'
    if explicit is None and provider != 'codex':
        if provider == 'anthropic':
            # Model APIs without capabilities: documented families, not invented universal support.
            if re.match(r'claude-(opus|sonnet)-(5|4-[78])|claude-(fable|mythos)', ident):
                levels = ['low', 'medium', 'high', 'xhigh', 'max']
                source = 'documented Claude family; refresh model catalog for capabilities'
            elif re.match(r'claude-(opus|sonnet)-4-6', ident):
                levels = ['low', 'medium', 'high', 'max']
                source = 'documented Claude family'
            elif ident.startswith('claude-opus-4-5'):
                levels = ['low', 'medium', 'high']
                source = 'documented Claude family'
            else:
                levels = []
                source = 'no effort capability advertised'
        elif provider == 'openrouter' and isinstance(params, list) and not any(x in params for x in ['reasoning', 'reasoning.effort', 'reasoning_effort']):
            levels = []
            source = 'catalog does not advertise reasoning'
        else:
            levels = list(PROTOCOL_LEVELS)
    elif explicit is None:
        source = 'Codex did not advertise effort levels; use its default'
    thinking = caps.get('thinking') or {}
    types = thinking.get('types') or {}
    budget = bool(types.get('enabled', {}).get('supported')) if isinstance(types.get('enabled'), dict) else False
    if provider == 'anthropic' and not thinking:
        budget = bool(re.match(r'claude-(opus-4-5|sonnet-4-5|haiku-4-5|sonnet-3-7)', ident))
    return {'id': ident, 'name': raw.get('displayName', raw.get('name', raw.get('display_name', ident))),
            'reasoning_levels': levels, 'reasoning_source': source,
            'default_reasoning': raw.get('defaultReasoningEffort', raw.get('default_reasoning_effort', '')),
            'is_default': bool(raw.get('isDefault', raw.get('is_default', False))),
            'supports_budget': budget or (provider == 'openrouter' and bool(levels)),
            'supports_adaptive': bool(types.get('adaptive', {}).get('supported')) if isinstance(types.get('adaptive'), dict) else False,
            'supported_parameters': params, 'capabilities': caps}


def selected_effort(settings, role: str) -> str:
    key = {'writer': 'reasoning_effort', 'editor': 'editor_reasoning_effort', 'extraction': 'extraction_reasoning_effort'}.get(role, 'reasoning_effort')
    value = getattr(settings, key, DEFAULT) or DEFAULT
    if not re.fullmatch(r'[a-z][a-z0-9_-]{0,31}', value):
        raise ValueError('Invalid reasoning level.')
    return value


def validate_effort(effort: str, model: dict | None, provider: str):
    if effort == DEFAULT:
        return
    if effort == 'budget':
        if provider not in {'anthropic', 'openrouter'} or (model is not None and not model.get('supports_budget')):
            raise ValueError('An explicit thinking-token budget is not supported by this model connection.')
        return
    if model is not None and effort not in model.get('reasoning_levels', []):
        offered = ', '.join(model.get('reasoning_levels', [])) or 'provider default only'
        raise ValueError(f"{model['id'] or 'Default model'} does not advertise '{effort}'. Available: {offered}. Refresh models or select Provider default.")
    if model is None and (provider == 'codex' or effort not in PROTOCOL_LEVELS):
        raise ValueError('Load this model\'s capabilities before selecting an extended reasoning level. No request was sent.')


def request_fields(settings, role: str, model_info: dict | None = None, output_cap: int = 7000) -> dict[str, Any]:
    effort = selected_effort(settings, role)
    validate_effort(effort, model_info, settings.provider)
    if effort == DEFAULT:
        return {}
    if effort == 'budget':
        budget = settings.reasoning_budget_tokens
        if not 1024 <= budget < output_cap:
            raise ValueError('Thinking budget must be at least 1,024 tokens and smaller than the total output-token limit.')
        return {'thinking': {'type': 'enabled', 'budget_tokens': budget}} if settings.provider == 'anthropic' else {'reasoning': {'max_tokens': budget}}
    if settings.provider == 'anthropic':
        result = {'output_config': {'effort': effort}}
        if model_info and model_info.get('supports_adaptive'):
            result['thinking'] = {'type': 'adaptive'}
        return result
    if settings.provider == 'openrouter':
        # require_parameters prevents routing to an endpoint that ignores the setting.
        return {'reasoning': {'effort': effort}, 'provider': {'require_parameters': True}}
    if settings.provider == 'openai-compatible':
        return {'reasoning_effort': effort}
    return {}

from __future__ import annotations

import json
import math
import os
import re
import time
from typing import Any, Callable
from urllib.parse import urlsplit

import httpx

from .models import Settings
from .secrets import Vault
from .reasoning import normalize_model, selected_effort, request_fields


class ProviderError(Exception):
    pass


class Cancelled(Exception):
    pass


def parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        value = json.loads(text, parse_constant=lambda v: (_ for _ in ()).throw(ValueError("Non-finite JSON number")))
    except ValueError as e:
        raise ProviderError("The model returned invalid JSON. No partial result was applied. Try again or choose a model with structured-output support.") from e
    if not isinstance(value, dict):
        raise ProviderError("The model must return a JSON object, not a list or scalar.")
    return value


def endpoint(base: str) -> str:
    p = urlsplit(base)
    if p.scheme not in {"https", "http"} or not p.hostname or p.username or p.password or p.query or p.fragment:
        raise ValueError("Set an HTTPS API base URL without credentials, query or fragment.")
    if p.scheme == "http" and p.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Unencrypted HTTP is allowed only for a local model server.")
    return base.rstrip("/")


class Clients:
    def __init__(self, settings: Settings, vault: Vault, job=None, transport=None):
        self.settings, self.vault, self.job, self.transport = settings, vault, job, transport
        self._model_cache = None
        self._active_effort = "default"

    def llm_key(self) -> str:
        if self.settings.provider == "openrouter":
            return self.vault.get("openrouter") or self.vault.get("llm")
        return self.vault.get("llm") or (os.getenv("ANTHROPIC_API_KEY", "") if self.settings.provider == "anthropic" else "")

    def check(self, url: str):
        if self.job:
            self.job.check()
        host = urlsplit(url).hostname
        if host not in {"localhost", "127.0.0.1", "::1"} and not self.settings.allow_cloud:
            raise ProviderError("Enable 'Allow selected content to be sent to my providers' in Connections first. Nothing has been sent.")

    def post(self, url: str, payload: dict, key: str, label: str, anthropic=False) -> dict:
        self.check(url)
        if not key and urlsplit(url).hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ProviderError(f"No API key configured for {label}. Open Connections.")
        headers = {"Content-Type": "application/json"}
        if anthropic:
            headers.update({"x-api-key": key, "anthropic-version": "2023-06-01"})
        elif key:
            headers["Authorization"] = f"Bearer {key}"
        if urlsplit(url).hostname == "openrouter.ai":
            headers["X-Title"] = "GraphPaper"
        for attempt in range(3):
            self.check(url)
            if self.job:
                self.job.before_call(label, self.settings.max_calls)
            try:
                with httpx.Client(timeout=httpx.Timeout(self.settings.request_timeout_seconds, connect=20), follow_redirects=False, transport=self.transport) as client:
                    res = client.post(url, json=payload, headers=headers)
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                # A timeout may have been billed: avoid automatically duplicating it.
                raise ProviderError(f"{label} could not be reached or timed out. No automatic retry of an ambiguous request; check your provider and try again.") from e
            if res.status_code in {429, 502, 503} and attempt < 2:
                if self.job:
                    self.job.note(f"{label}: temporary HTTP {res.status_code}; retrying once backoff completes.")
                    if self.job.cancel.wait(2 ** (attempt + 1)):
                        raise Cancelled()
                else:
                    time.sleep(2 ** (attempt + 1))
                continue
            if res.is_error:
                # Do not echo provider response bodies (may contain keys or manuscript text).
                advice = {401: "Check the API key.", 402: "Check your provider balance.", 403: "Check provider access.", 404: "Check the model ID and API base URL.", 400: "Check model support, context and output limits.", 413: "The request is too large; lower the context budget.", 429: "Provider rate limit reached."}.get(res.status_code, "Check the connection and provider status.")
                raise ProviderError(f"{label}: HTTP {res.status_code}. {advice}")
            if len(res.content) > 20_000_000:
                raise ProviderError("Provider response exceeded the size limit.")
            try:
                data = res.json()
            except ValueError as e:
                raise ProviderError(f"{label} returned non-JSON data.") from e
            if not isinstance(data, dict) or "error" in data:
                raise ProviderError(f"{label} returned an API error. No result was applied.")
            if self.job:
                self.job.record_usage(label, data.get("usage", {}), data.get("model", ""))
                if label != "JEV" and self.job.receipts:
                    self.job.receipts[-1]["reasoning_effort"] = self._active_effort
                self.job.check()
            return data
        raise ProviderError("Provider retry limit reached")

    def complete(self, system: str, user: str, *, role="writer", json_mode=False, max_tokens=None) -> str | dict:
        s = self.settings
        model = {"editor": s.editor_model, "extraction": s.extraction_model}.get(role) or s.model
        if not model.strip() and s.provider != "codex":
            raise ProviderError("Choose a writing model in Connections. Model IDs are configurable; GraphPaper does not silently substitute one.")
        if len(system) + len(user) > s.context_chars:
            raise ProviderError("This request exceeds your configured context character budget. Raise it for a suitable model, narrow the selected graph or split the project. Nothing was silently truncated.")
        cap = max_tokens or s.max_output_tokens
        effort = selected_effort(s, role)
        self._active_effort = effort
        info = None
        if effort != 'default' and s.provider != 'codex':
            catalog = self.discover_models()
            info = next((m for m in catalog if m['id'] == model), None)
        fields = request_fields(s, role, info, cap) if s.provider != 'codex' else {}
        base = endpoint(s.base_url)
        if json_mode:
            system += "\nReturn only a valid JSON object. No fences, commentary, NaN or Infinity."
        if s.provider == "codex":
            from .codex import get_codex
            self.check('https://chatgpt.com')
            text = get_codex(self.vault.path.parent, s.codex_executable).complete(system, user, model, self.job, s.max_calls, reasoning_effort=effort, timeout_seconds=s.request_timeout_seconds)
            return parse_json(text) if json_mode else text
        if s.provider == "anthropic":
            data = self.post((base if base.endswith("/v1") else base + "/v1") + "/messages", {"model": model, "system": system, "messages": [{"role": "user", "content": user}], "max_tokens": cap, **fields}, self.llm_key(), role, True)
            if data.get("stop_reason") == "max_tokens":
                raise ProviderError("Output limit reached. Raise the output budget or shorten this task; the truncated draft was not applied.")
            text = "".join(x.get("text", "") for x in data.get("content", []) if x.get("type") == "text")
        else:
            token_field = "max_completion_tokens" if urlsplit(base).hostname == "api.openai.com" else "max_tokens"
            payload = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], token_field: cap, **fields}
            if json_mode:
                payload["response_format"] = {"type": "json_object"}
            data = self.post(base + "/chat/completions", payload, self.llm_key(), role)
            choices = data.get("choices", [])
            if not choices:
                raise ProviderError("The writing model returned no completion.")
            if choices[0].get("finish_reason") in {"length", "content_filter"}:
                raise ProviderError("The completion was truncated or filtered. No partial result was applied.")
            text = choices[0].get("message", {}).get("content") or ""
            if not isinstance(text, str):
                text = "".join(x.get("text", "") for x in text if isinstance(x, dict))
        if not text.strip():
            raise ProviderError("The model returned no usable text.")
        return parse_json(text) if json_mode else text.strip()

    def jev_route(self):
        route = self.settings.jev_provider
        if route == "auto":
            route = "openrouter" if self.vault.get("openrouter") or (self.settings.provider == "openrouter" and self.vault.get("llm")) else "typesafe" if self.vault.get("typesafe") else "off"
        return route

    def decide(self, state: dict | str, questions: dict) -> dict | None:
        from .jev_budget import dispatch
        return dispatch(self,state,questions)

    def discover_models(self):
        if self._model_cache is not None:
            return self._model_cache
        if self.settings.provider == 'codex':
            from .codex import get_codex
            self._model_cache = get_codex(self.vault.path.parent, self.settings.codex_executable).models()
            return self._model_cache
        if self.settings.provider == "anthropic":
            headers = {"x-api-key": self.llm_key(), "anthropic-version": "2023-06-01"}
        else:
            headers = {"Authorization": "Bearer " + self.llm_key()} if self.llm_key() else {}
        base = endpoint(self.settings.base_url)
        if self.settings.provider == "anthropic" and not base.endswith("/v1"):
            base += "/v1"
        with httpx.Client(timeout=30, transport=self.transport) as c:
            res = c.get(base + "/models", headers=headers)
        if res.is_error:
            raise ProviderError(f"Model list: HTTP {res.status_code}. Enter your model ID manually.")
        raw = res.json().get("data", [])
        self._model_cache = [normalize_model(x, self.settings.provider) for x in raw if isinstance(x, dict) and x.get("id")][:2000]
        return self._model_cache

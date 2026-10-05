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
                with httpx.Client(timeout=httpx.Timeout(180, connect=20), follow_redirects=False, transport=self.transport) as client:
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
        base = endpoint(s.base_url)
        if json_mode:
            system += "\nReturn only a valid JSON object. No fences, commentary, NaN or Infinity."
        if s.provider == "codex":
            from .codex import get_codex
            self.check('https://chatgpt.com')
            text = get_codex(self.vault.path.parent, s.codex_executable).complete(system, user, model, self.job, s.max_calls)
            return parse_json(text) if json_mode else text
        if s.provider == "anthropic":
            data = self.post((base if base.endswith("/v1") else base + "/v1") + "/messages", {"model": model, "system": system, "messages": [{"role": "user", "content": user}], "max_tokens": cap}, self.llm_key(), role, True)
            if data.get("stop_reason") == "max_tokens":
                raise ProviderError("Output limit reached. Raise the output budget or shorten this task; the truncated draft was not applied.")
            text = "".join(x.get("text", "") for x in data.get("content", []) if x.get("type") == "text")
        else:
            token_field = "max_completion_tokens" if urlsplit(base).hostname == "api.openai.com" else "max_tokens"
            payload = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], token_field: cap}
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
        route = self.jev_route()
        if route == "off":
            return None
        if not questions or len(questions) > 100:
            raise ValueError("JEV batches must have 1–100 questions.")
        # This conservative character limit is not advertised as an exact token count.
        if len(json.dumps(state, ensure_ascii=False)) + len(json.dumps(questions)) > 60000:
            raise ProviderError("JEV state exceeds the conservative 60,000-character request limit. Reduce the batch.")
        bare = self.settings.jev_model.removeprefix("~typesafe/").removeprefix("typesafe/")
        if route == "openrouter":
            url = "https://openrouter.ai/api/alpha/decisions"
            model = "~typesafe/jev-latest" if bare == "jev-latest" else "typesafe/" + bare
        else:
            url, model = "https://api.typesafe.ai/v1/systemone", bare
        data = self.post(url, {"model": model, "state": state, "questions": questions}, (self.vault.get(route) or (self.llm_key() if route == "openrouter" and self.settings.provider == "openrouter" else "")), "JEV")
        answers = data.get("answers", {})
        for name, q in questions.items():
            answer = answers.get(name, {})
            if answer.get("type") != q["type"]:
                raise ProviderError(f"JEV returned an invalid answer type for {name}.")
            if q["type"] == "noul":
                v = answer.get("noul")
                if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1:
                    raise ProviderError("JEV returned an invalid probability.")
            elif q["type"] == "choice" and answer.get("choice") not in q["criteria"]:
                raise ProviderError("JEV returned a choice outside the declared options.")
        return answers

    def discover_models(self):
        if self.settings.provider == 'codex':
            from .codex import get_codex
            return get_codex(self.vault.path.parent, self.settings.codex_executable).models()
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
        return [{"id": x["id"], "name": x.get("name", x.get("display_name", x["id"]))} for x in raw if isinstance(x, dict) and x.get("id")][:2000]

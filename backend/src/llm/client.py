"""Unified LLM client using the OpenAI Python library.

All OpenAI-compatible providers (Ollama, OpenAI, Gemini, Grok) are handled
through ``openai.OpenAI`` with different ``base_url`` / ``api_key`` values.
Anthropic is handled via its own SDK but exposed through the same interface.

Default provider: ``local`` (Ollama at http://localhost:11434/v1).

Provider base URLs
------------------
- **local (Ollama)**:  ``http://localhost:11434/v1``
- **openai**:          ``https://api.openai.com/v1``
- **gemini**:          ``https://generativelanguage.googleapis.com/v1beta/openai/``
- **grok**:            ``https://api.x.ai/v1``
- **anthropic**:       Uses ``anthropic`` SDK directly (not OpenAI-compatible)
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass

log = logging.getLogger(__name__)

_MAX_RETRIES = 2

# ── Provider registry ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ProviderConfig:
    base_url: str | None
    env_key: str | None
    default_api_key: str
    default_model: str
    models: tuple[str, ...]
    label: str


PROVIDERS: dict[str, ProviderConfig] = {
    "local": ProviderConfig(
        base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434") + "/v1",
        env_key=None,
        default_api_key="ollama",
        default_model="qwen2.5-coder:7b",
        models=(
            "qwen2.5-coder:7b",
            "llama3.2:3b",
            "deepseek-coder-v2:16b",
            "mistral:7b",
            "gemma2:9b",
        ),
        label="Local LLM (Ollama)",
    ),
    "openai": ProviderConfig(
        base_url="https://api.openai.com/v1",
        env_key="OPENAI_API_KEY",
        default_api_key="",
        default_model="gpt-4o",
        models=("gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o3-mini"),
        label="OpenAI",
    ),
    "anthropic": ProviderConfig(
        base_url=None,
        env_key="ANTHROPIC_API_KEY",
        default_api_key="",
        default_model="claude-sonnet-4-20250514",
        models=(
            "claude-sonnet-4-20250514",
            "claude-3-5-haiku-20241022",
        ),
        label="Anthropic (Claude)",
    ),
    "gemini": ProviderConfig(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        env_key="GEMINI_API_KEY",
        default_api_key="",
        default_model="gemini-2.0-flash",
        models=("gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-pro"),
        label="Google Gemini",
    ),
    "grok": ProviderConfig(
        base_url="https://api.x.ai/v1",
        env_key="XAI_API_KEY",
        default_api_key="",
        default_model="grok-3-mini",
        models=("grok-3", "grok-3-mini"),
        label="xAI (Grok)",
    ),
}


def get_providers_info() -> list[dict]:
    """Return serialisable provider metadata for the frontend."""
    result = []
    for key, cfg in PROVIDERS.items():
        has_key = True
        if cfg.env_key:
            has_key = bool(os.getenv(cfg.env_key))
        result.append({
            "id": key,
            "label": cfg.label,
            "models": list(cfg.models),
            "default_model": cfg.default_model,
            "configured": has_key,
        })
    return result


# ── Unified client ───────────────────────────────────────────────────────────


class LLMClient:
    """Provider-agnostic LLM client.

    Uses the ``openai`` library for OpenAI-compatible providers and falls back
    to the ``anthropic`` library for Claude.

    Usage::

        llm = LLMClient()                              # local Ollama
        llm = LLMClient(provider="openai")              # GPT-4o
        llm = LLMClient(provider="gemini", model="gemini-2.0-flash")
        data = llm.generate_json(prompt, system)
    """

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.provider_name = provider or os.getenv("LLM_PROVIDER", "local")
        cfg = PROVIDERS.get(self.provider_name)
        if cfg is None:
            raise ValueError(
                f"Unknown provider '{self.provider_name}'. "
                f"Choose from: {', '.join(PROVIDERS)}"
            )
        self._cfg = cfg
        self.model = model or os.getenv("LLM_MODEL") or cfg.default_model

        resolved_key = api_key
        if not resolved_key and cfg.env_key:
            resolved_key = os.getenv(cfg.env_key, "")
        if not resolved_key:
            resolved_key = cfg.default_api_key

        if cfg.env_key and not resolved_key:
            raise ValueError(
                f"Provider '{self.provider_name}' requires {cfg.env_key} to be set."
            )

        self._api_key = resolved_key
        self._is_anthropic = self.provider_name == "anthropic"

        if self._is_anthropic:
            self._init_anthropic()
        else:
            self._init_openai()

    # ── provider init ────────────────────────────────────────────

    def _init_openai(self) -> None:
        from openai import OpenAI

        kwargs: dict = {"api_key": self._api_key}
        if self._cfg.base_url:
            kwargs["base_url"] = self._cfg.base_url
        self._openai = OpenAI(**kwargs)

    def _init_anthropic(self) -> None:
        from anthropic import Anthropic

        self._anthropic = Anthropic(api_key=self._api_key)

    # ── core API ─────────────────────────────────────────────────

    def chat(
        self,
        prompt: str,
        system: str | None = None,
        *,
        as_json: bool = False,
    ) -> str:
        """Send a chat message and return the assistant's reply text."""
        log.info("  Sending request to %s (%s)…", self.provider_name, self.model)

        if self._is_anthropic:
            return self._chat_anthropic(prompt, system, as_json=as_json)
        return self._chat_openai(prompt, system, as_json=as_json)

    def generate_json(
        self,
        prompt: str,
        system: str | None = None,
    ) -> dict:
        """Send a prompt, force JSON output, parse and return a dict.

        Retries up to ``_MAX_RETRIES`` times on malformed JSON.
        """
        last_err: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            raw = self.chat(prompt, system, as_json=True)
            try:
                parsed = json.loads(_extract_json(raw))
                log.info("  Received valid JSON from %s", self.provider_name)
                return parsed
            except json.JSONDecodeError as exc:
                log.warning(
                    "  Attempt %d/%d: invalid JSON from LLM, retrying… (%s)",
                    attempt, _MAX_RETRIES, exc,
                )
                last_err = exc
        raise ValueError(
            f"LLM returned invalid JSON after {_MAX_RETRIES} attempts"
        ) from last_err

    # ── OpenAI-compatible path ───────────────────────────────────

    def _chat_openai(
        self,
        prompt: str,
        system: str | None,
        *,
        as_json: bool = False,
    ) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict = {"model": self.model, "messages": messages}
        if as_json:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            resp = self._openai.chat.completions.create(**kwargs)
        except Exception as exc:
            self._handle_openai_error(exc)

        content = resp.choices[0].message.content or ""
        return content

    def _handle_openai_error(self, exc: Exception) -> None:
        err_str = str(exc).lower()
        exc_type = type(exc).__name__.lower()

        if "not found" in err_str and "model" in err_str:
            if self.provider_name == "local":
                raise RuntimeError(
                    f"Model '{self.model}' not found in Ollama. "
                    f"Pull it first:  ollama pull {self.model}"
                ) from exc
            raise RuntimeError(
                f"Model '{self.model}' not available for {self.provider_name}."
            ) from exc

        if "connect" in exc_type or "refused" in err_str or "connection" in exc_type:
            if self.provider_name == "local":
                raise ConnectionError(
                    "Cannot reach Ollama. Is it running?  "
                    "Start with:  ollama serve"
                ) from exc
            raise ConnectionError(
                f"Cannot reach {self.provider_name}: {exc}"
            ) from exc

        if "auth" in err_str or "api key" in err_str or "401" in err_str:
            raise RuntimeError(
                f"Authentication failed for {self.provider_name}. "
                f"Check your {self._cfg.env_key} in .env"
            ) from exc

        raise

    # ── Anthropic path ───────────────────────────────────────────

    def _chat_anthropic(
        self,
        prompt: str,
        system: str | None,
        *,
        as_json: bool = False,
    ) -> str:
        user_content = prompt
        if as_json:
            user_content += "\n\nYou MUST respond with valid JSON only. No markdown fences, no prose."

        kwargs: dict = {
            "model": self.model,
            "max_tokens": 8192,
            "messages": [{"role": "user", "content": user_content}],
        }
        if system:
            kwargs["system"] = system

        try:
            resp = self._anthropic.messages.create(**kwargs)
        except Exception as exc:
            err_str = str(exc).lower()
            if "auth" in err_str or "api key" in err_str:
                raise RuntimeError(
                    "Authentication failed for Anthropic. "
                    "Check your ANTHROPIC_API_KEY in .env"
                ) from exc
            raise

        content = resp.content[0].text if resp.content else ""
        return content


# ── Backward compatibility ───────────────────────────────────────────────────

OllamaClient = LLMClient


# ── Helpers ──────────────────────────────────────────────────────────────────

def _extract_json(text: str) -> str:
    """Strip markdown fences or surrounding prose, returning bare JSON."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    return text

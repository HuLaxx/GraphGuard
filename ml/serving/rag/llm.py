"""
LLM providers for RAG.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

import httpx


class LLMClient:
    def complete(self, messages: List[Dict[str, str]]) -> str:
        raise NotImplementedError

    @property
    def model(self) -> str:
        raise NotImplementedError


class GroqClient(LLMClient):
    def __init__(self, api_key: str, model: str, temperature: float, max_tokens: int):
        self._api_key = api_key
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._base_url = "https://api.groq.com/openai/v1"

    @property
    def model(self) -> str:
        return self._model

    def complete(self, messages: List[Dict[str, str]]) -> str:
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        response = httpx.post(
            f"{self._base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


class OpenAICompatibleClient(LLMClient):
    def __init__(self, base_url: str, api_key: str | None, model: str, temperature: float, max_tokens: int):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    @property
    def model(self) -> str:
        return self._model

    def complete(self, messages: List[Dict[str, str]]) -> str:
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        headers: Dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        response = httpx.post(
            f"{self._base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


class OllamaClient(LLMClient):
    def __init__(self, base_url: str, model: str, temperature: float, max_tokens: int):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    @property
    def model(self) -> str:
        return self._model

    def complete(self, messages: List[Dict[str, str]]) -> str:
        payload = {
            "model": self._model,
            "messages": messages,
            "options": {
                "temperature": self._temperature,
                "num_predict": self._max_tokens,
            },
            "stream": False,
        }
        response = httpx.post(
            f"{self._base_url}/api/chat",
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "").strip()


class MockLLM(LLMClient):
    def __init__(self, model: str = "mock"):
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    def complete(self, messages: List[Dict[str, str]]) -> str:
        last = messages[-1]["content"] if messages else ""
        return f"MOCK_RESPONSE: {last[:120]}"

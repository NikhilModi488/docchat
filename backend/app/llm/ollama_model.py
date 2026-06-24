"""
app/llm/ollama_model.py
=======================
Local LLM layer — a thin wrapper around LangChain's `ChatOllama`.

One model (llama3.2 by default) serves every role (translate / rephrase /
answer / recommend) via different prompts. Supports blocking (`invoke`) and
streaming (`stream`) generation, plus health/discovery helpers.
"""

from __future__ import annotations

from collections.abc import Iterator

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Cache ChatOllama clients by (model, temperature) so we don't rebuild per call.
_client_cache: dict[tuple[str, float], ChatOllama] = {}


class OllamaLLM:
    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
        host: str | None = None,
    ) -> None:
        cfg = settings.llm
        self.model = model or cfg.default_model
        self.temperature = cfg.temperature if temperature is None else temperature
        self.host = host or cfg.host

        key = (self.model, self.temperature)
        if key not in _client_cache:
            _client_cache[key] = ChatOllama(
                model=self.model,
                base_url=self.host,
                temperature=self.temperature,
                num_predict=cfg.num_predict,
            )
            logger.info("Initialised ChatOllama(model=%s, host=%s)", self.model, self.host)
        self._llm = _client_cache[key]

    def invoke(self, prompt: ChatPromptTemplate, **variables) -> str:
        chain = prompt | self._llm
        result = chain.invoke(variables)
        return result.content

    def stream(self, prompt: ChatPromptTemplate, **variables) -> Iterator[str]:
        chain = prompt | self._llm
        for chunk in chain.stream(variables):
            if chunk.content:
                yield chunk.content

    @staticmethod
    def list_models(host: str | None = None) -> list[str]:
        host = host or settings.llm.host
        try:
            import requests

            resp = requests.get(f"{host}/api/tags", timeout=5)
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
        except Exception as exc:
            logger.warning("Could not reach Ollama at %s: %s", host, exc)
            return []

    @staticmethod
    def is_available(host: str | None = None) -> bool:
        host = host or settings.llm.host
        try:
            import requests

            requests.get(f"{host}/api/tags", timeout=5).raise_for_status()
            return True
        except Exception:
            return False

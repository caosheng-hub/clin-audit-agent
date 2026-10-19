from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class LLMConfig:
    provider: str = "ollama"
    base_url: str = "http://localhost:11434"
    model: str = "qwen2.5:7b-instruct-q4_K_M"
    temperature: float = 0.0
    timeout_s: int = 180


def load_llm_config(path: Path) -> LLMConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    llm = raw.get("llm", {})
    return LLMConfig(
        provider=str(llm.get("provider", "ollama")),
        base_url=str(llm.get("base_url", "http://localhost:11434")).rstrip("/"),
        model=str(llm.get("model", "qwen2.5:7b-instruct-q4_K_M")),
        temperature=float(llm.get("temperature", 0.0)),
        timeout_s=int(llm.get("timeout_s", 180)),
    )


class OllamaProvider:
    def __init__(self, config: LLMConfig):
        self.config = config

    def chat(
        self,
        prompt: str,
        system: str | None = None,
        json_schema: dict | None = None,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload: dict = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self.config.temperature},
        }
        if json_schema is not None:
            payload["format"] = json_schema

        request = urllib.request.Request(
            f"{self.config.base_url}/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.config.timeout_s
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Ollama returned HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"无法连接 Ollama ({self.config.base_url})：{exc}. "
                "请先安装并启动 Ollama，或确认模型已 pull。"
            ) from exc
        return str(body.get("message", {}).get("content", ""))


class MockProvider:
    def chat(
        self,
        prompt: str,
        system: str | None = None,
        json_schema: dict | None = None,
    ) -> str:
        return '{"status": "ok", "provider": "mock"}'


def get_provider(config: LLMConfig):
    if config.provider == "mock":
        return MockProvider()
    if config.provider == "ollama":
        return OllamaProvider(config)
    raise ValueError(f"unsupported LLM provider: {config.provider!r}")

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import httpx


class OpenAIClient:
    """
    Minimal OpenAI Chat Completions client using httpx.

    Reads API key from env OPENAI_API_KEY or from .secrets/openai_api_key if present.
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.api_key = self._resolve_api_key()
        self.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

    def _resolve_api_key(self) -> str:
        key = os.environ.get("OPENAI_API_KEY")
        if key:
            return key
        secrets_path = os.path.join(os.getcwd(), ".secrets", "openai_api_key")
        if os.path.exists(secrets_path):
            with open(secrets_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        raise RuntimeError("OPENAI_API_KEY not set and .secrets/openai_api_key not found")

    def chat(self, messages: List[Dict[str, str]], response_format: Optional[Dict[str, Any]] = None, temperature: float = 0.0) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        body: Dict[str, Any] = {"model": self.model, "messages": messages, "temperature": temperature}
        if response_format is not None:
            body["response_format"] = response_format
        with httpx.Client(timeout=60) as client:
            resp = client.post(f"{self.base_url}/chat/completions", headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


def format_strategy_prompt(patch: str, inputs: Dict[str, Any], facts: Dict[str, Any], retrieval: Dict[str, Any], threat: Dict[str, Any]) -> List[Dict[str, str]]:
    system = (
        "You are an ARAM strategy assistant. Output ONLY valid JSON matching the StrategyDraft schema. "
        "Cite item ids from facts.items and include snippet ids in evidence. TL;DR must be ≤ 3 lines."
    )
    user = {
        "patch": patch,
        "inputs": inputs,
        "facts": {
            "items": [{"id": i["id"] if isinstance(i, dict) else i.id, "name": i["name"] if isinstance(i, dict) else i.name, "tags": i.get("tags", []) if isinstance(i, dict) else getattr(i, "tags", [])} for i in facts.get("items", [])],
        },
        "retrieval": {"snippets": [{"id": s["id"] if isinstance(s, dict) else s.id, "text": s["text"] if isinstance(s, dict) else s.text} for s in retrieval.get("snippets", [])]},
        "threat": threat,
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]



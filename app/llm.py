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


def _to_primitive_threat(threat: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not isinstance(threat, dict):
        return out
    scores = []
    for s in threat.get("scores", []) or []:
        if hasattr(s, "model_dump"):
            d = s.model_dump()
        elif isinstance(s, dict):
            d = s
        else:
            # best-effort fallback
            try:
                d = {
                    "unit": getattr(s, "unit", "unknown"),
                    "score": getattr(s, "score", 0),
                    "reasons": list(getattr(s, "reasons", [])),
                }
            except Exception:
                d = {"unit": "unknown", "score": 0, "reasons": []}
        scores.append({
            "unit": d.get("unit"),
            "score": d.get("score"),
            "reasons": d.get("reasons", []),
        })
    if scores:
        out["scores"] = scores
    return out


def format_strategy_prompt(patch: str, inputs: Dict[str, Any], facts: Dict[str, Any], retrieval: Dict[str, Any], threat: Dict[str, Any]) -> List[Dict[str, str]]:
    system = (
        "You are a League of Legends ARAM strategy assistant. Return ONE valid JSON object ONLY, matching this exact schema and lowercase keys. "
        "No prose, no markdown, no extra keys. Cite item ids and snippet ids.\n\n"
        "Required keys and types:\n"
        "- tldr: array of up to 3 short strings\n"
        "- assumptions: object\n"
        "- threats: array of {name: string, why: string}\n"
        "- role: one of [peel, engage, poke, zone, front_to_back, anti_dive]\n"
        "- build_plan: array of {trigger: string, items: array of {id: number, name: string}, why: string, timing?: string}\n"
        "- evidence: array of {type: 'item'|'snippet', id: number|string}\n\n"
        "Output template example (fill with your content):\n"
        "{\n"
        "  \"tldr\": [\"...\", \"...\"],\n"
        "  \"assumptions\": {\"patch\": \"...\", \"ally_comp\": [], \"enemy_comp\": []},\n"
        "  \"threats\": [{\"name\": \"...\", \"why\": \"...\"}],\n"
        "  \"role\": \"front_to_back\",\n"
        "  \"build_plan\": [{\"trigger\": \"...\", \"items\": [{\"id\": 0, \"name\": \"...\"}], \"why\": \"...\", \"timing\": \"...\"}],\n"
        "  \"evidence\": [{\"type\": \"item\", \"id\": 0}, {\"type\": \"snippet\", \"id\": \"...\"}]\n"
        "}"
    )
    user = {
        "patch": patch,
        "inputs": inputs,
        "facts": {
            "items": [{"id": i["id"] if isinstance(i, dict) else i.id, "name": i["name"] if isinstance(i, dict) else i.name, "tags": i.get("tags", []) if isinstance(i, dict) else getattr(i, "tags", [])} for i in facts.get("items", [])],
        },
        "retrieval": {"snippets": [{"id": s["id"] if isinstance(s, dict) else s.id, "text": s["text"] if isinstance(s, dict) else s.text} for s in retrieval.get("snippets", [])]},
        "threat": _to_primitive_threat(threat),
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]



"""The only module that talks to the model servers.

Both servers speak the OpenAI protocol: vLLM for chat, TEI for embeddings.
"""

import json
import re
from functools import lru_cache

import httpx
from openai import OpenAI

from app.config import get_settings

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


@lru_cache
def _chat_client() -> OpenAI:
    s = get_settings()
    return OpenAI(base_url=s.llm_url, api_key=s.llm_api_key, timeout=120)


@lru_cache
def _embed_client() -> OpenAI:
    s = get_settings()
    return OpenAI(base_url=s.embed_url, api_key=s.embed_api_key, timeout=60)


def strip_thinking(text: str) -> str:
    """Remove Qwen3's <think> block, including one cut off by max_tokens."""
    text = _THINK_RE.sub("", text)
    if "<think>" in text:
        text = text.split("<think>", 1)[0]
    return text.strip()


def chat(
    messages: list[dict],
    *,
    temperature: float = 0.0,
    max_tokens: int = 800,
    thinking: bool = False,
    json_schema: dict | None = None,
    seed: int | None = None,
) -> tuple[str, dict]:
    """Return (text, usage). Thinking is off unless asked for: Qwen3 otherwise
    spends its token budget on a <think> block before answering."""
    kwargs: dict = {}
    if seed is not None:
        kwargs["seed"] = seed
    if json_schema is not None:
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "output", "schema": json_schema},
        }
    resp = _chat_client().chat.completions.create(
        model=get_settings().llm_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        extra_body={"chat_template_kwargs": {"enable_thinking": thinking}},
        **kwargs,
    )
    usage = resp.usage.model_dump() if resp.usage else {}
    return strip_thinking(resp.choices[0].message.content or ""), usage


def chat_json(messages: list[dict], schema: dict, **kwargs) -> dict:
    """Chat with the output constrained to `schema` by the server's guided decoder."""
    text, _ = chat(messages, json_schema=schema, **kwargs)
    return json.loads(text)


def embed(texts: list[str]) -> list[list[float]]:
    s = get_settings()
    vectors: list[list[float]] = []
    for i in range(0, len(texts), s.embed_batch_size):
        batch = texts[i : i + s.embed_batch_size]
        resp = _embed_client().embeddings.create(model=s.embed_model, input=batch)
        vectors.extend(d.embedding for d in sorted(resp.data, key=lambda d: d.index))
    return vectors


def llm_reachable() -> bool:
    s = get_settings()
    try:
        r = httpx.get(
            f"{s.llm_url}/models",
            headers={"Authorization": f"Bearer {s.llm_api_key}"},
            timeout=3,
        )
        return r.status_code == 200
    except httpx.HTTPError:
        return False


def embedder_reachable() -> bool:
    # TEI has no /v1/models route; its health probe lives at the server root.
    s = get_settings()
    root = s.embed_url.rstrip("/").removesuffix("/v1")
    try:
        r = httpx.get(
            f"{root}/health",
            headers={"Authorization": f"Bearer {s.embed_api_key}"},
            timeout=3,
        )
        return r.status_code == 200
    except httpx.HTTPError:
        return False

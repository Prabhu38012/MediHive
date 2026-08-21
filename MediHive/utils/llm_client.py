"""
utils/llm_client.py

Single wrapper around the LLM provider. All agents call through this module
so that swapping OpenAI <-> Ollama <-> any future provider only requires
changes here, not in every agent file.

Design note: we ask the model to return STRICT JSON matching a known schema
(answer, reasoning, confidence) so downstream code (memory, debate, fusion)
never has to guess how to parse free text.
"""

import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

JSON_INSTRUCTION = """
You must respond with STRICT JSON only, no markdown fences, no preamble.
Schema:
{
  "answer": "<concise direct answer>",
  "reasoning": "<step by step medical reasoning behind the answer>",
  "confidence": <float between 0.0 and 1.0>
}
"""


def _extract_json(raw_text: str) -> dict:
    """Best-effort extraction of a JSON object from model output.
    Handles cases where the model wraps JSON in ```json fences despite
    instructions, or adds stray text around it.
    """
    text = raw_text.strip()
    text = re.sub(r"^```json|^```|```$", "", text, flags=re.MULTILINE).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: grab the first {...} block
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # Last resort: return a low-confidence stub rather than crashing the
    # whole pipeline over one malformed agent response.
    return {
        "answer": text[:500] if text else "No answer produced.",
        "reasoning": "Model did not return valid JSON; raw text captured as answer.",
        "confidence": 0.2,
    }


def _call_openai(system_prompt: str, user_prompt: str) -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt + JSON_INSTRUCTION},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
    )
    raw = response.choices[0].message.content
    return _extract_json(raw)


def _call_ollama(system_prompt: str, user_prompt: str) -> dict:
    import httpx

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt + JSON_INSTRUCTION},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
    }
    resp = httpx.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=600)
    resp.raise_for_status()
    raw = resp.json()["message"]["content"]
    return _extract_json(raw)


def call_llm(system_prompt: str, user_prompt: str) -> dict:
    """Route to the configured provider. Returns dict with
    keys: answer, reasoning, confidence.
    """
    if LLM_PROVIDER == "ollama":
        return _call_ollama(system_prompt, user_prompt)
    return _call_openai(system_prompt, user_prompt)

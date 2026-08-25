"""
utils/llm_client.py

Single wrapper around the LLM provider (Ollama / Groq). All agents call through
this module so that swapping providers only requires changes here.

Design note: we ask the model to return STRICT JSON matching a known schema
(answer, reasoning, confidence) so downstream code (memory, debate, fusion)
never has to guess how to parse free text.
"""

import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))


JSON_INSTRUCTION = """

CRITICAL OUTPUT FORMAT INSTRUCTION:
You MUST respond with a single, valid JSON object ONLY. No markdown code fences, no introductory remarks, no trailing text.
JSON Schema:
{
  "answer": "<exact option letter (e.g., 'A', 'B', 'C', 'D') for MCQs, or 'yes'/'no'/'maybe' for PubMedQA, or concise direct answer>",
  "reasoning": "<step-by-step clinical chain-of-thought: 1. Key patient findings -> 2. Pathophysiology / Mechanism -> 3. Elimination of incorrect options -> 4. Final conclusion>",
  "confidence": <calibrated float between 0.0 and 1.0 representing diagnostic certainty>
}
"""


def _sanitize_and_repair_json(text: str) -> str:
    """Pre-process text to fix common LLM JSON syntax errors."""
    # Strip markdown fences
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()

    # Find the outermost JSON object
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]

    # Fix unquoted single-letter option values (e.g. "answer": A, -> "answer": "A",)
    cleaned = re.sub(r'("answer"\s*:\s*)([A-Da-d])(\s*[,}])', r'\1"\2"\3', cleaned)

    # Fix unquoted yes/no/maybe values (e.g. "answer": yes, -> "answer": "yes",)
    cleaned = re.sub(r'("answer"\s*:\s*)(yes|no|maybe)(\s*[,}])', r'\1"\2"\3', cleaned, flags=re.IGNORECASE)

    # Replace single quotes around keys/values with double quotes if needed
    cleaned = re.sub(r"'([a-zA-Z0-9_]+)'\s*:", r'"\1":', cleaned)

    # Remove trailing commas before closing braces
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)

    return cleaned


def _extract_json(raw_text: str) -> dict:
    """Robust multi-tier extraction of JSON object from model output."""
    text = (raw_text or "").strip()
    if not text:
        return {"answer": "", "reasoning": "Empty model output", "confidence": 0.0}

    # Tier 1: Try direct parse on cleaned text
    cleaned = _sanitize_and_repair_json(text)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict) and "answer" in parsed:
            # Ensure confidence is a float
            try:
                parsed["confidence"] = float(parsed.get("confidence", 0.8))
            except (ValueError, TypeError):
                parsed["confidence"] = 0.8
            return parsed
    except json.JSONDecodeError:
        pass

    # Tier 2: Regex extraction of individual fields if full JSON parse fails
    answer_match = re.search(r'"answer"\s*:\s*"?([A-Da-d]|yes|no|maybe|[^",}\n]+)"?', text, re.IGNORECASE)
    confidence_match = re.search(r'"confidence"\s*:\s*([0-1]?(?:\.\d+)?)', text)
    reasoning_match = re.search(r'"reasoning"\s*:\s*"?(.*?)"?\s*(?:,\s*"confidence"|\}$)', text, re.DOTALL)

    if answer_match:
        extracted_answer = answer_match.group(1).strip().strip('"').strip("'")
        extracted_conf = float(confidence_match.group(1)) if confidence_match else 0.75
        extracted_reasoning = reasoning_match.group(1).strip() if reasoning_match else text[:500]
        return {
            "answer": extracted_answer,
            "reasoning": extracted_reasoning,
            "confidence": min(max(extracted_conf, 0.0), 1.0),
        }

    # Tier 3: Direct option letter / word detection from raw output
    opt_match = re.search(r'\b([A-D])\b', text)
    decision_match = re.search(r'\b(yes|no|maybe)\b', text, re.IGNORECASE)
    fallback_answer = opt_match.group(1) if opt_match else (decision_match.group(1) if decision_match else text[:100])

    return {
        "answer": fallback_answer,
        "reasoning": text[:500] if text else "Raw model response captured.",
        "confidence": 0.5,
    }


_groq_client = None


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        from openai import OpenAI
        load_dotenv(override=True)
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set in your .env file. Get a free key at https://console.groq.com")
        _groq_client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    return _groq_client


def _call_groq(system_prompt: str, user_prompt: str, max_retries: int = 10) -> dict:
    import time
    import random
    from openai import RateLimitError, APIError

    client = _get_groq_client()
    model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    if not model_name or "llama-" in model_name:
        model_name = "openai/gpt-oss-20b"

    time.sleep(random.uniform(0.1, 0.4))

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt + JSON_INSTRUCTION},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=LLM_TEMPERATURE,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            return _extract_json(raw)
        except RateLimitError as e:
            msg = str(e)
            match = re.search(r"try again in (\d+(?:\.\d+)?)s", msg)
            wait_time = (float(match.group(1)) + 1.0) if match else ((attempt + 1) * 3.0)
            if attempt < max_retries - 1:
                time.sleep(wait_time)
            else:
                raise e
        except APIError as e:
            if attempt < max_retries - 1:
                time.sleep(2.0)
            else:
                raise e


def _call_ollama(system_prompt: str, user_prompt: str) -> dict:
    import httpx

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt + JSON_INSTRUCTION},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": LLM_TEMPERATURE,
        },
    }
    resp = httpx.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=600)
    resp.raise_for_status()
    raw = resp.json()["message"]["content"]
    return _extract_json(raw)


def call_llm(system_prompt: str, user_prompt: str) -> dict:
    """Route to the configured provider ('ollama' or 'groq'). Returns dict with
    keys: answer, reasoning, confidence.
    """
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    if provider == "groq":
        return _call_groq(system_prompt, user_prompt)
    return _call_ollama(system_prompt, user_prompt)

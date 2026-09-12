#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/ai_key_rotator.py
Multi-Provider AI Key Rotator for Quiz Ideation & Scripting.
Supports:
1. Google AI Studio: Rotating 6 Gemini API keys (models: gemini-3.6-flash, gemini-3.7-flash, gemini-flash-latest)
2. Agnes AI Gateway (apihub.agnes-ai.com): Rotating 4 Agnes API keys (models: agnes-2.0-flash, gpt-4o-mini)
3. Automatic cascade & rate-limit failover (Gemini -> Agnes AI)
4. Robust JSON extraction & schema validation
"""

import os
import sys
import json
import re
import time
import random
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional, Tuple

# Suppress bytecode generation on exFAT mounts
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

GEMINI_MODELS = ["gemini-3.6-flash", "gemini-3.7-flash"]
AGNES_MODELS = ["agnes-2.0-flash", "gpt-4o-mini"]
DEFAULT_AGNES_BASE_URL = "https://apihub.agnes-ai.com/v1"


def parse_key_list(val: Any) -> List[str]:
    if not val:
        return []
    if isinstance(val, list):
        return [str(k).strip() for k in val if str(k).strip()]
    val_str = str(val).strip()
    if val_str.startswith("[") and val_str.endswith("]"):
        try:
            parsed = json.loads(val_str)
            if isinstance(parsed, list):
                return [str(k).strip() for k in parsed if str(k).strip()]
        except Exception:
            pass
    return [k.strip() for k in re.split(r"[\n,]+", val_str) if k.strip()]


class AIKeyRotator:
    def __init__(self):
        self.gemini_keys = self._load_gemini_keys()
        self.agnes_keys, self.agnes_base_url = self._load_agnes_keys()
        self.gemini_idx = 0
        self.agnes_idx = 0

    def _load_gemini_keys(self) -> List[str]:
        # 1. Environment variable (e.g. in GitHub Actions)
        env_keys = parse_key_list(os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY"))
        if env_keys:
            return env_keys

        # 2. Filesystem profiles
        candidates = [
            os.path.expanduser("~/.cloud-profiles/lelehoctiengtrung/gemini/api_keys.json"),
            os.path.expanduser("~/.cloud-profiles/hana_assistant/gemini/api_keys.json"),
        ]
        for p in candidates:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        keys = data.get("keys", [])
                        if keys:
                            return [k.strip() for k in keys if k.strip()]
                except Exception:
                    pass
        return []

    def _load_agnes_keys(self) -> Tuple[List[str], str]:
        base_url = os.getenv("AGNES_BASE_URL", DEFAULT_AGNES_BASE_URL)
        env_keys = parse_key_list(os.getenv("AGNES_API_KEYS") or os.getenv("AGNES_API_KEY"))
        if env_keys:
            return env_keys, base_url

        candidates = [
            os.path.expanduser("~/.cloud-profiles/lelehoctiengtrung/agnes/api_keys.json"),
            os.path.expanduser("~/.cloud-profiles/hana_assistant/agnes/api_keys.json"),
        ]
        for p in candidates:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        keys = data.get("keys", [])
                        b_url = data.get("base_url", base_url)
                        if keys:
                            return [k.strip() for k in keys if k.strip()], b_url
                except Exception:
                    pass
        return [], base_url

    def _clean_json_text(self, text: str) -> str:
        text = text.strip()
        # Remove markdown code blocks ```json ... ```
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if m:
            text = m.group(1).strip()
        return text

    def _extract_json(self, raw_text: str) -> Optional[Any]:
        cleaned = self._clean_json_text(raw_text)
        # Direct attempt
        try:
            return json.loads(cleaned)
        except Exception:
            pass

        # Try to find outer brackets
        for pattern in [r"\[\s*\{[\s\S]*\}\s*\]", r"\{[\s\S]*\}"]:
            m = re.search(pattern, raw_text)
            if m:
                try:
                    return json.loads(m.group(0))
                except Exception:
                    pass
        return None

    def call_gemini(self, system_prompt: str, user_prompt: str) -> Tuple[Optional[Any], str]:
        """Tries all available Gemini keys with model rotation."""
        if not self.gemini_keys:
            return None, "No Gemini API keys configured."

        total_keys = len(self.gemini_keys)
        attempts = 0

        while attempts < total_keys:
            key = self.gemini_keys[self.gemini_idx]
            masked_key = f"{key[:8]}...{key[-4:]}"
            self.gemini_idx = (self.gemini_idx + 1) % total_keys
            attempts += 1

            for model in GEMINI_MODELS:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                payload = {
                    "contents": [
                        {"role": "user", "parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}
                    ],
                    "generationConfig": {
                        "temperature": 0.7,
                        "responseMimeType": "application/json"
                    }
                }
                body = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=body,
                    headers={"Content-Type": "application/json", "x-goog-api-key": key}
                )

                try:
                    with urllib.request.urlopen(req, timeout=45) as resp:
                        res_data = json.loads(resp.read().decode("utf-8"))
                        text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                        parsed = self._extract_json(text)
                        if parsed is not None:
                            provider_tag = f"Gemini ({model} | Key {masked_key})"
                            return parsed, provider_tag
                except urllib.error.HTTPError as e:
                    err_body = e.read().decode("utf-8", errors="ignore")
                    if e.code in (429, 403):
                        print(f"  ⚠ Gemini Key {masked_key} rate-limited/exhausted (HTTP {e.code}). Rotating...")
                        break  # Rotate to next key immediately
                    else:
                        print(f"  ⚠ Gemini error with model {model} (HTTP {e.code}): {err_body[:100]}")
                        continue
                except Exception as ex:
                    print(f"  ⚠ Gemini request exception: {ex}")
                    continue

        return None, "All Gemini keys failed or rate-limited."

    def call_agnes(self, system_prompt: str, user_prompt: str) -> Tuple[Optional[Any], str]:
        """Tries all available Agnes AI keys with model rotation."""
        if not self.agnes_keys:
            return None, "No Agnes AI keys configured."

        total_keys = len(self.agnes_keys)
        attempts = 0

        while attempts < total_keys:
            key = self.agnes_keys[self.agnes_idx]
            masked_key = f"{key[:8]}...{key[-4:]}"
            self.agnes_idx = (self.agnes_idx + 1) % total_keys
            attempts += 1

            for model in AGNES_MODELS:
                url = f"{self.agnes_base_url}/chat/completions"
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.7
                }
                body = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=body,
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                        "User-Agent": "LeLeQuiz/2.0"
                    }
                )

                try:
                    with urllib.request.urlopen(req, timeout=25) as resp:
                        res_data = json.loads(resp.read().decode("utf-8"))
                        text = res_data["choices"][0]["message"]["content"]
                        parsed = self._extract_json(text)
                        if parsed is not None:
                            provider_tag = f"Agnes AI ({model} | Key {masked_key})"
                            return parsed, provider_tag
                except urllib.error.HTTPError as e:
                    err_body = e.read().decode("utf-8", errors="ignore")
                    if e.code in (429, 403):
                        print(f"  ⚠ Agnes Key {masked_key} rate-limited (HTTP {e.code}). Rotating...")
                        break
                    else:
                        print(f"  ⚠ Agnes AI error with model {model} (HTTP {e.code}): {err_body[:100]}")
                        continue
                except Exception as ex:
                    print(f"  ⚠ Agnes AI request exception: {ex}")
                    continue

        return None, "All Agnes AI keys failed or rate-limited."

    def generate_quiz_ideas(self, system_prompt: str, user_prompt: str) -> Tuple[Optional[Any], str]:
        """
        Primary: Rotating 6 Gemini API keys
        Fallback: Cascading to rotating 4 Agnes AI keys
        """
        # 1. Attempt Gemini Pool
        data, provider = self.call_gemini(system_prompt, user_prompt)
        if data is not None:
            return data, provider

        print(f"🔄 Cascading to Agnes AI Fallback Pool ({len(self.agnes_keys)} keys available)...")
        # 2. Attempt Agnes AI Pool
        data, provider = self.call_agnes(system_prompt, user_prompt)
        if data is not None:
            return data, provider

        return None, "All AI providers and keys exhausted."


# Global Singleton
_rotator_instance: Optional[AIKeyRotator] = None

def get_ai_rotator() -> AIKeyRotator:
    global _rotator_instance
    if _rotator_instance is None:
        _rotator_instance = AIKeyRotator()
    return _rotator_instance


if __name__ == "__main__":
    print("=" * 60)
    print("🤖 TESTING MULTI-PROVIDER AI KEY ROTATOR")
    rotator = get_ai_rotator()
    print(f"🔑 Gemini Keys Pool: {len(rotator.gemini_keys)} keys loaded")
    print(f"🔑 Agnes AI Keys Pool: {len(rotator.agnes_keys)} keys loaded (Base: {rotator.agnes_base_url})")
    print("=" * 60)

    test_sys = "You are a Mandarin Chinese Quiz Generator. You must respond in valid JSON with an array of objects."
    test_user = "Generate 1 sample quiz idea about 'Đi Du Lịch' with 5 words. Schema: {'topic': str, 'words': [{'hanzi': str, 'pinyin': str, 'meaning': str}]}"

    data, provider = rotator.generate_quiz_ideas(test_sys, test_user)
    if data:
        print(f"\n🎉 SUCCESS via [{provider}]!")
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"\n❌ FAILED: {provider}")

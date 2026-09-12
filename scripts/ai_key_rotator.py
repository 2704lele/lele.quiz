#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/ai_key_rotator.py
Multi-Provider AI Key Rotator with Circuit Breaker & Rate-Limit Resilience.
Lê Lê Học Tiếng Trung Quiz v2.0 Pipeline (Milestone 4 / Features F15-F17).

Key Features:
1. Multi-Provider Pools:
   - 6 Google Gemini API keys (~/.cloud-profiles/lelehoctiengtrung/gemini/api_keys.json)
     Models: gemini-3.6-flash, gemini-3.7-flash
   - 4 Agnes AI Gateway keys (~/.cloud-profiles/lelehoctiengtrung/agnes/api_keys.json)
     Models: agnes-2.0-flash, gpt-4o-mini, Base URL: https://apihub.agnes-ai.com/v1
2. Zero-Leak Credential Security:
   - Header-only authentication:
     * Google Gemini: `x-goog-api-key: {key}`
     * Agnes AI Gateway: `Authorization: Bearer {key}`
   - Zero URL leakage: Query parameter `?key=` strictly forbidden and stripped.
   - Comprehensive masking in all logs and exception tracebacks: `key[:6] + "..." + key[-4:]`
3. Circuit Breaker State Machine & Rate-Limit Resilience:
   - Key states: `HEALTHY`, `COOLDOWN`, `DEAD`
   - HTTP 429: Mark key in cooldown for 60s, rotate to next key.
   - HTTP 503 High Demand: Mark key in cooldown for 30s, retry with next model/key with exponential backoff.
   - HTTP 400 / 401 / 403: Mark key permanently `DEAD`.
   - Network / socket timeouts: Randomized exponential backoff with jitter: `delay * (0.8 + 0.4 * random.random())`.
4. Cascading Fallback:
   - Tier 1: Gemini Pool (rotates 6 keys across healthy pool)
   - Tier 2: Agnes AI Gateway Fallback (cascades automatically on Gemini exhaustion/cooldown)
5. Interface Compatibility:
   - ResilientAIKeyRotator (primary)
   - AIKeyRotator (backwards-compatible alias)
   - get_ai_rotator(), get_resilient_ai_rotator()
"""

import os
import sys
import json
import re
import time
import random
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional, Tuple, Callable

# Suppress bytecode generation on exFAT mounts
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

DEFAULT_GEMINI_MODELS = ["gemini-3.6-flash", "gemini-3.7-flash"]
DEFAULT_AGNES_MODELS = ["agnes-2.0-flash", "gpt-4o-mini"]
DEFAULT_AGNES_BASE_URL = "https://apihub.agnes-ai.com/v1"

# Exported constants for compatibility
GEMINI_MODELS = DEFAULT_GEMINI_MODELS
AGNES_MODELS = DEFAULT_AGNES_MODELS


def parse_key_list(val: Any) -> List[str]:
    """Parses keys from string, list, or JSON string."""
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


class KeyState:
    """Circuit breaker state enumeration."""
    HEALTHY = "HEALTHY"
    COOLDOWN = "COOLDOWN"
    DEAD = "DEAD"


class APIKeyEntry:
    """
    Individual API Key entry tracking circuit breaker state,
    cooldown expiration, error history, and safe masked representation.
    """
    def __init__(self, key: str, provider: str):
        self.key: str = key.strip()
        self.provider: str = provider
        self.state: str = KeyState.HEALTHY
        self.cooldown_until: float = 0.0
        self.fail_count: int = 0
        self.success_count: int = 0
        self.last_error: Optional[str] = None

    @property
    def masked(self) -> str:
        """Masked string representation: key[:6] + "..." + key[-4:]."""
        k = self.key
        if len(k) <= 10:
            return f"{k[:2]}...{k[-2:]}" if len(k) >= 4 else "****"
        return f"{k[:6]}...{k[-4:]}"

    def is_available(self, current_time: Optional[float] = None) -> bool:
        """
        Determines if key can receive traffic.
        Recovers COOLDOWN keys back to HEALTHY once cooldown_until passes.
        """
        now = time.time() if current_time is None else current_time
        if self.state == KeyState.DEAD:
            return False
        if self.state == KeyState.COOLDOWN:
            if now >= self.cooldown_until:
                self.state = KeyState.HEALTHY
                self.cooldown_until = 0.0
                return True
            return False
        return True

    def mark_rate_limited(self, duration: float = 60.0, current_time: Optional[float] = None, error_msg: Optional[str] = None):
        """HTTP 429: Key put in cooldown for duration seconds."""
        now = time.time() if current_time is None else current_time
        self.state = KeyState.COOLDOWN
        self.cooldown_until = now + duration
        self.fail_count += 1
        if error_msg:
            self.last_error = error_msg

    def mark_cooldown(self, duration: float = 30.0, current_time: Optional[float] = None, error_msg: Optional[str] = None):
        """HTTP 503 / High Demand: Key put in cooldown for duration seconds."""
        now = time.time() if current_time is None else current_time
        self.state = KeyState.COOLDOWN
        self.cooldown_until = now + duration
        self.fail_count += 1
        if error_msg:
            self.last_error = error_msg

    def mark_dead(self, error_msg: Optional[str] = None):
        """HTTP 400 / 401 / 403: Key permanently invalidated."""
        self.state = KeyState.DEAD
        self.cooldown_until = float("inf")
        self.fail_count += 1
        if error_msg:
            self.last_error = error_msg

    def mark_success(self):
        """Records successful response, keeps or restores HEALTHY state."""
        self.state = KeyState.HEALTHY
        self.cooldown_until = 0.0
        self.success_count += 1
        self.last_error = None

    def __repr__(self) -> str:
        return f"<APIKeyEntry {self.provider}:{self.masked} state={self.state} fails={self.fail_count}>"


class ResilientAIKeyRotator:
    """
    Multi-Provider AI Key Rotator with Circuit Breaker, Cascading Failover,
    Zero-Leak Header Authentication, and Randomized Jitter Backoff.
    """
    def __init__(
        self,
        gemini_models: Optional[List[str]] = None,
        agnes_models: Optional[List[str]] = None,
        agnes_base_url: Optional[str] = None,
        sleep_fn: Optional[Callable[[float], None]] = None,
    ):
        self.sleep_fn: Callable[[float], None] = sleep_fn if sleep_fn is not None else time.sleep
        self.gemini_models: List[str] = gemini_models or list(DEFAULT_GEMINI_MODELS)
        self.agnes_models: List[str] = agnes_models or list(DEFAULT_AGNES_MODELS)

        # Load key pools
        raw_gemini_keys = self._load_gemini_keys()
        self.gemini_keys: List[APIKeyEntry] = [APIKeyEntry(k, "gemini") for k in raw_gemini_keys]

        raw_agnes_keys, detected_agnes_url = self._load_agnes_keys()
        self.agnes_base_url: str = agnes_base_url or detected_agnes_url or DEFAULT_AGNES_BASE_URL
        self.agnes_keys: List[APIKeyEntry] = [APIKeyEntry(k, "agnes") for k in raw_agnes_keys]

        self.gemini_idx: int = 0
        self.agnes_idx: int = 0

    def _load_gemini_keys(self) -> List[str]:
        """Loads 6 Google Gemini API keys from environment or filesystem profile."""
        env_keys = parse_key_list(os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY"))
        if env_keys:
            return env_keys

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
                        parsed = [str(k).strip() for k in keys if str(k).strip()]
                        if parsed:
                            return parsed
                except Exception:
                    pass
        return []

    def _load_agnes_keys(self) -> Tuple[List[str], str]:
        """Loads 4 Agnes AI Gateway keys from environment or filesystem profile."""
        base_url = os.getenv("AGNES_BASE_URL", DEFAULT_AGNES_BASE_URL)
        env_keys = parse_key_list(os.getenv("AGNES_API_KEYS") or os.getenv("AGNES_API_KEY"))

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
                        parsed = [str(k).strip() for k in keys if str(k).strip()]
                        if env_keys:
                            return env_keys, b_url
                        if parsed:
                            return parsed, b_url
                except Exception:
                    pass
        return (env_keys, base_url) if env_keys else ([], base_url)

    def scrub_text(self, text: Any, extra_keys: Optional[List[str]] = None) -> str:
        """
        Zero-leak sanitizer: Scrubs any known raw API keys and pattern-matched credentials
        from text or exception strings, replacing them with masked `key[:6] + "..." + key[-4:]`.
        """
        if not text:
            return ""
        result = str(text)
        all_keys = [k.key for k in self.gemini_keys] + [k.key for k in self.agnes_keys]
        if extra_keys:
            all_keys.extend([k for k in extra_keys if k])

        for k in all_keys:
            if k and len(k) >= 6 and k in result:
                masked = f"{k[:6]}...{k[-4:]}"
                result = result.replace(k, masked)

        # General credential pattern scrubbing (Google AI Studio AIzaSy..., ag-..., sk-...)
        def _mask_match(m: re.Match) -> str:
            val = m.group(0)
            return f"{val[:6]}...{val[-4:]}"

        result = re.sub(r"AIzaSy[0-9a-zA-Z_\-]{20,}", _mask_match, result)
        result = re.sub(r"(?:ag-|sk-)[0-9a-zA-Z_\-]{16,}", _mask_match, result)
        return result

    def _calculate_jitter_delay(
        self, base_delay: float, attempt: int = 0, backoff_factor: float = 1.5, max_delay: float = 30.0
    ) -> float:
        """
        Calculates randomized exponential backoff with jitter:
        `scaled_delay * (0.8 + 0.4 * random.random())`
        Produces values within [0.8 * scaled, 1.2 * scaled].
        """
        scaled = min(base_delay * (backoff_factor ** attempt), max_delay)
        jittered = scaled * (0.8 + 0.4 * random.random())
        return jittered

    def _execute_with_jitter_backoff(self, delay: float, attempt: int = 0):
        """Sleeps with randomized jitter backoff."""
        jittered = self._calculate_jitter_delay(delay, attempt)
        self.sleep_fn(jittered)

    def _clean_json_text(self, text: str) -> str:
        """Removes markdown code fences from LLM responses."""
        text = text.strip()
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if m:
            text = m.group(1).strip()
        return text

    def _extract_json(self, raw_text: str) -> Optional[Any]:
        """Extracts and validates JSON payload from LLM response text."""
        if not raw_text:
            return None
        cleaned = self._clean_json_text(raw_text)
        try:
            return json.loads(cleaned)
        except Exception:
            pass

        # Search for outer array or object
        for pattern in [r"\[\s*\{[\s\S]*\}\s*\]", r"\{[\s\S]*\}"]:
            m = re.search(pattern, raw_text)
            if m:
                try:
                    return json.loads(m.group(0))
                except Exception:
                    pass
                # Try cleaning trailing commas
                cleaned_m = re.sub(r",(\s*[}\]])", r"\1", m.group(0))
                try:
                    return json.loads(cleaned_m)
                except Exception:
                    pass
        return None

    def call_gemini(
        self, system_prompt: str, user_prompt: str, mock_dispatcher: Optional[Callable] = None
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Executes idea generation against the Google Gemini key pool.
        - Zero-leak: `x-goog-api-key: {key}` header ONLY. NO key in URL query strings.
        - Circuit breaker:
          * 429 -> cooldown 60s, rotate to next key
          * 503 -> cooldown 30s, retry next model/key with jitter backoff
          * 400/401/403 -> permanently DEAD, rotate to next key
          * Timeouts/Sockets -> randomized exponential backoff with jitter
        """
        if not self.gemini_keys:
            return None, "No Gemini API keys configured."

        available_keys = [k for k in self.gemini_keys if k.is_available()]
        if not available_keys:
            return None, "All Gemini keys in cooldown or exhausted."

        total_keys = len(self.gemini_keys)
        attempts = 0

        while attempts < total_keys:
            key_entry = self.gemini_keys[self.gemini_idx]
            self.gemini_idx = (self.gemini_idx + 1) % total_keys
            attempts += 1

            if not key_entry.is_available():
                continue

            for model_idx, model in enumerate(self.gemini_models):
                if not key_entry.is_available():
                    break

                # Mock dispatcher path for test harnesses
                if mock_dispatcher is not None:
                    res_data, status_code, err_msg = mock_dispatcher("gemini", key_entry.key, model, system_prompt, user_prompt)
                    if status_code == 200 and res_data is not None:
                        key_entry.mark_success()
                        return res_data, f"Gemini ({model} | Key {key_entry.masked})"
                    elif status_code == 429:
                        key_entry.mark_rate_limited(60.0, error_msg=err_msg)
                        break
                    elif status_code == 503:
                        key_entry.mark_cooldown(30.0, error_msg=err_msg)
                        self._execute_with_jitter_backoff(delay=0.01, attempt=model_idx)
                        continue
                    elif status_code in (400, 401, 403):
                        key_entry.mark_dead(error_msg=err_msg)
                        break
                    else:
                        self._execute_with_jitter_backoff(delay=0.01, attempt=model_idx)
                        continue

                # ZERO-LEAK SECURITY: Never include ?key={key} in URL
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
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
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": key_entry.key,
                        "User-Agent": "LeLeQuiz/2.0"
                    }
                )

                try:
                    with urllib.request.urlopen(req, timeout=35) as resp:
                        res_data = json.loads(resp.read().decode("utf-8"))
                        text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                        parsed = self._extract_json(text)
                        if parsed is not None:
                            key_entry.mark_success()
                            provider_tag = f"Gemini ({model} | Key {key_entry.masked})"
                            return parsed, provider_tag
                        else:
                            print(f"  ⚠ Gemini model {model} (Key {key_entry.masked}) returned invalid JSON format. Retrying...")
                            continue
                except urllib.error.HTTPError as e:
                    err_body = e.read().decode("utf-8", errors="ignore")
                    err_safe = self.scrub_text(err_body)
                    if e.code == 429:
                        key_entry.mark_rate_limited(60.0, error_msg=f"HTTP 429: {err_safe[:80]}")
                        print(f"  ⚠ Gemini Key {key_entry.masked} rate-limited (HTTP 429). Cooldown 60s. Rotating...")
                        break  # Rotate to next key
                    elif e.code == 503:
                        key_entry.mark_cooldown(30.0, error_msg=f"HTTP 503: {err_safe[:80]}")
                        print(f"  ⚠ Gemini Service Unavailable / High Demand (HTTP 503) on model {model} (Key {key_entry.masked}). Cooldown 30s. Backing off...")
                        self._execute_with_jitter_backoff(delay=2.0, attempt=model_idx)
                        continue  # Retry with next model/key
                    elif e.code in (400, 401, 403):
                        key_entry.mark_dead(error_msg=f"HTTP {e.code}: {err_safe[:80]}")
                        print(f"  ⚠ Gemini Key {key_entry.masked} invalid or disabled (HTTP {e.code}). Marked DEAD.")
                        break  # Key permanently dead, rotate to next
                    else:
                        print(f"  ⚠ Gemini HTTP error {e.code} on model {model} (Key {key_entry.masked}): {err_safe[:100]}. Backing off...")
                        self._execute_with_jitter_backoff(delay=2.0, attempt=model_idx)
                        continue
                except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as ex:
                    err_safe = self.scrub_text(str(ex))
                    print(f"  ⚠ Gemini network/timeout error on model {model} (Key {key_entry.masked}): {err_safe}. Backing off with jitter...")
                    self._execute_with_jitter_backoff(delay=1.5, attempt=model_idx)
                    continue
                except Exception as ex:
                    err_safe = self.scrub_text(str(ex))
                    print(f"  ⚠ Gemini unexpected exception on model {model} (Key {key_entry.masked}): {err_safe}")
                    self._execute_with_jitter_backoff(delay=1.0, attempt=model_idx)
                    continue

        return None, "All Gemini keys failed or in cooldown."

    def call_agnes(
        self, system_prompt: str, user_prompt: str, mock_dispatcher: Optional[Callable] = None
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Executes idea generation against the Agnes AI Gateway key pool.
        - Zero-leak: `Authorization: Bearer {key}` header ONLY. NO key in URL query strings.
        - Circuit breaker:
          * 429 -> cooldown 60s, rotate to next key
          * 503 -> cooldown 30s, retry next model/key with jitter backoff
          * 400/401/403 -> permanently DEAD, rotate to next key
          * Timeouts/Sockets -> randomized exponential backoff with jitter
        """
        if not self.agnes_keys:
            return None, "No Agnes AI keys configured."

        available_keys = [k for k in self.agnes_keys if k.is_available()]
        if not available_keys:
            return None, "All Agnes AI keys in cooldown or exhausted."

        total_keys = len(self.agnes_keys)
        attempts = 0

        while attempts < total_keys:
            key_entry = self.agnes_keys[self.agnes_idx]
            self.agnes_idx = (self.agnes_idx + 1) % total_keys
            attempts += 1

            if not key_entry.is_available():
                continue

            for model_idx, model in enumerate(self.agnes_models):
                if not key_entry.is_available():
                    break

                # Mock dispatcher path for test harnesses
                if mock_dispatcher is not None:
                    res_data, status_code, err_msg = mock_dispatcher("agnes", key_entry.key, model, system_prompt, user_prompt)
                    if status_code == 200 and res_data is not None:
                        key_entry.mark_success()
                        return res_data, f"Agnes AI ({model} | Key {key_entry.masked})"
                    elif status_code == 429:
                        key_entry.mark_rate_limited(60.0, error_msg=err_msg)
                        break
                    elif status_code == 503:
                        key_entry.mark_cooldown(30.0, error_msg=err_msg)
                        self._execute_with_jitter_backoff(delay=0.01, attempt=model_idx)
                        continue
                    elif status_code in (400, 401, 403):
                        key_entry.mark_dead(error_msg=err_msg)
                        break
                    else:
                        self._execute_with_jitter_backoff(delay=0.01, attempt=model_idx)
                        continue

                # ZERO-LEAK SECURITY: Bearer token in header, never in URL
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
                        "Authorization": f"Bearer {key_entry.key}",
                        "Content-Type": "application/json",
                        "User-Agent": "LeLeQuiz/2.0"
                    }
                )

                try:
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        res_data = json.loads(resp.read().decode("utf-8"))
                        text = res_data["choices"][0]["message"]["content"]
                        parsed = self._extract_json(text)
                        if parsed is not None:
                            key_entry.mark_success()
                            provider_tag = f"Agnes AI ({model} | Key {key_entry.masked})"
                            return parsed, provider_tag
                        else:
                            print(f"  ⚠ Agnes AI model {model} (Key {key_entry.masked}) returned invalid JSON. Retrying...")
                            continue
                except urllib.error.HTTPError as e:
                    err_body = e.read().decode("utf-8", errors="ignore")
                    err_safe = self.scrub_text(err_body)
                    if e.code == 429:
                        key_entry.mark_rate_limited(60.0, error_msg=f"HTTP 429: {err_safe[:80]}")
                        print(f"  ⚠ Agnes Key {key_entry.masked} rate-limited (HTTP 429). Cooldown 60s. Rotating...")
                        break
                    elif e.code == 503:
                        key_entry.mark_cooldown(30.0, error_msg=f"HTTP 503: {err_safe[:80]}")
                        print(f"  ⚠ Agnes Service Unavailable (HTTP 503) on model {model} (Key {key_entry.masked}). Cooldown 30s. Backing off...")
                        self._execute_with_jitter_backoff(delay=2.0, attempt=model_idx)
                        continue
                    elif e.code in (400, 401, 403):
                        key_entry.mark_dead(error_msg=f"HTTP {e.code}: {err_safe[:80]}")
                        print(f"  ⚠ Agnes Key {key_entry.masked} invalid or unauthorized (HTTP {e.code}). Marked DEAD.")
                        break
                    else:
                        print(f"  ⚠ Agnes AI HTTP error {e.code} on model {model} (Key {key_entry.masked}): {err_safe[:100]}. Backing off...")
                        self._execute_with_jitter_backoff(delay=2.0, attempt=model_idx)
                        continue
                except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as ex:
                    err_safe = self.scrub_text(str(ex))
                    print(f"  ⚠ Agnes AI network/socket/timeout error on model {model} (Key {key_entry.masked}): {err_safe}. Backing off with jitter...")
                    self._execute_with_jitter_backoff(delay=1.5, attempt=model_idx)
                    continue
                except Exception as ex:
                    err_safe = self.scrub_text(str(ex))
                    print(f"  ⚠ Agnes AI unexpected exception on model {model} (Key {key_entry.masked}): {err_safe}")
                    self._execute_with_jitter_backoff(delay=1.0, attempt=model_idx)
                    continue

        return None, "All Agnes AI keys failed or in cooldown."

    def call_agnes_fallback(
        self, system_prompt: str, user_prompt: str, mock_dispatcher: Optional[Callable] = None
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """Direct alias for call_agnes."""
        return self.call_agnes(system_prompt, user_prompt, mock_dispatcher=mock_dispatcher)

    def generate_quiz_ideas(
        self, system_prompt: str, user_prompt: str, mock_dispatcher: Optional[Callable] = None
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Primary entry point:
        1. Attempts Gemini pool (6 keys, gemini-3.6-flash, gemini-3.7-flash).
        2. On Gemini exhaustion or cooldown, automatically cascades to Agnes AI Gateway (4 keys, agnes-2.0-flash, gpt-4o-mini).
        3. Returns (parsed_json_dict, provider_tag).
        """
        # Tier 1: Gemini Pool
        data, provider = self.call_gemini(system_prompt, user_prompt, mock_dispatcher=mock_dispatcher)
        if data is not None:
            return data, provider

        # Tier 2: Agnes AI Pool
        data, agnes_provider = self.call_agnes(system_prompt, user_prompt, mock_dispatcher=mock_dispatcher)
        if data is not None:
            return data, agnes_provider

        return None, f"All AI providers and keys exhausted. Last Gemini status: {provider}; Agnes status: {agnes_provider}"

    def get_pool_status(self) -> Dict[str, Any]:
        """Returns structured circuit breaker status without leaking credentials."""
        return {
            "gemini": {
                "total": len(self.gemini_keys),
                "healthy": sum(1 for k in self.gemini_keys if k.state == KeyState.HEALTHY),
                "cooldown": sum(1 for k in self.gemini_keys if k.state == KeyState.COOLDOWN),
                "dead": sum(1 for k in self.gemini_keys if k.state == KeyState.DEAD),
                "keys": [
                    {
                        "masked": k.masked,
                        "state": k.state,
                        "cooldown_until": k.cooldown_until,
                        "fail_count": k.fail_count,
                        "success_count": k.success_count,
                    }
                    for k in self.gemini_keys
                ],
            },
            "agnes": {
                "total": len(self.agnes_keys),
                "healthy": sum(1 for k in self.agnes_keys if k.state == KeyState.HEALTHY),
                "cooldown": sum(1 for k in self.agnes_keys if k.state == KeyState.COOLDOWN),
                "dead": sum(1 for k in self.agnes_keys if k.state == KeyState.DEAD),
                "keys": [
                    {
                        "masked": k.masked,
                        "state": k.state,
                        "cooldown_until": k.cooldown_until,
                        "fail_count": k.fail_count,
                        "success_count": k.success_count,
                    }
                    for k in self.agnes_keys
                ],
            },
        }


# Backwards compatibility alias
AIKeyRotator = ResilientAIKeyRotator

# Global Singleton
_rotator_instance: Optional[ResilientAIKeyRotator] = None


def get_ai_rotator() -> ResilientAIKeyRotator:
    """Returns singleton instance of ResilientAIKeyRotator."""
    global _rotator_instance
    if _rotator_instance is None:
        _rotator_instance = ResilientAIKeyRotator()
    return _rotator_instance


def get_resilient_ai_rotator() -> ResilientAIKeyRotator:
    """Explicit alias for get_ai_rotator."""
    return get_ai_rotator()


# =====================================================================
# Comprehensive Self-Test Suite & CLI Runner
# =====================================================================

def run_self_tests(verbose: bool = True) -> bool:
    """
    Executes automated self-tests verifying:
    1. Key Loading: 6 Gemini keys + 4 Agnes keys loaded.
    2. Zero-Leak Credential Security: No query parameters, masked strings, headers verified.
    3. Circuit Breaker State Machine: Transitions between HEALTHY, COOLDOWN (429/503), DEAD (400/401/403).
    4. Exponential Backoff and Jitter: Formula delay * (0.8 + 0.4 * random.random()).
    5. Mocked Cascading Failover: Gemini exhaustion gracefully cascades to Agnes AI Gateway.
    """
    passed = 0
    total = 0

    def record_test(name: str, condition: bool, detail: str = ""):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            if verbose:
                print(f"  ✓ [PASS] {name}{f': {detail}' if detail else ''}")
        else:
            print(f"  ✗ [FAIL] {name}: {detail}")

    print("\n🔬 RUNNING AUTOMATED SELF-TESTS (ResilientAIKeyRotator)")
    print("-" * 65)

    # Test 1: Key Loading Verification
    rotator = ResilientAIKeyRotator(sleep_fn=lambda _: None)
    record_test(
        "T1.1: Gemini Key Pool Size",
        len(rotator.gemini_keys) == 6,
        f"{len(rotator.gemini_keys)} keys (expected 6)"
    )
    record_test(
        "T1.2: Agnes Key Pool Size",
        len(rotator.agnes_keys) == 4,
        f"{len(rotator.agnes_keys)} keys (expected 4)"
    )
    record_test(
        "T1.3: Agnes Base URL",
        rotator.agnes_base_url.rstrip("/") == "https://apihub.agnes-ai.com/v1",
        rotator.agnes_base_url
    )

    # Test 2: Zero-Leak Credential Security
    entry = APIKeyEntry("AIzaSyDTESTKEY1234567890abcdef", "gemini")
    record_test(
        "T2.1: Key Masking Format",
        entry.masked == "AIzaSy...cdef",
        f"Masked: {entry.masked}"
    )
    sample_trace = f"HTTP Error on key AIzaSyDTESTKEY1234567890abcdef: 403 Forbidden"
    scrubbed = rotator.scrub_text(sample_trace)
    record_test(
        "T2.2: Secret Scrubbing",
        "AIzaSyDTESTKEY1234567890abcdef" not in scrubbed,
        f"Scrubbed output: {scrubbed}"
    )

    # Test 3: Circuit Breaker State Machine Transitions
    test_key = APIKeyEntry("test_key_gemini_mock_00112233", "gemini")
    now = 1000.0
    record_test("T3.1: Initial State HEALTHY", test_key.state == KeyState.HEALTHY and test_key.is_available(now))

    # HTTP 429 Cooldown (60s)
    test_key.mark_rate_limited(60.0, current_time=now)
    record_test("T3.2: 429 State COOLDOWN", test_key.state == KeyState.COOLDOWN)
    record_test("T3.3: 429 Unavailable during Cooldown", not test_key.is_available(now + 30.0))
    record_test("T3.4: 429 Recovered after Cooldown", test_key.is_available(now + 61.0) and test_key.state == KeyState.HEALTHY)

    # HTTP 503 Cooldown (30s)
    test_key.mark_cooldown(30.0, current_time=now)
    record_test("T3.5: 503 State COOLDOWN", test_key.state == KeyState.COOLDOWN)
    record_test("T3.6: 503 Unavailable during Cooldown", not test_key.is_available(now + 15.0))
    record_test("T3.7: 503 Recovered after Cooldown", test_key.is_available(now + 31.0) and test_key.state == KeyState.HEALTHY)

    # HTTP 401/403 Permanent DEAD
    test_key.mark_dead("HTTP 401 Unauthorized")
    record_test("T3.8: 401 State DEAD", test_key.state == KeyState.DEAD)
    record_test("T3.9: DEAD remains unavailable forever", not test_key.is_available(now + 100000.0))

    # Test 4: Exponential Backoff and Randomized Jitter
    jitter_delays = [rotator._calculate_jitter_delay(base_delay=2.0, attempt=0) for _ in range(50)]
    all_in_range = all(2.0 * 0.8 <= d <= 2.0 * 1.2 for d in jitter_delays)
    has_variation = len(set(round(d, 4) for d in jitter_delays)) > 10
    record_test("T4.1: Jitter Range [0.8 * delay, 1.2 * delay]", all_in_range, f"Sample: {round(jitter_delays[0], 3)}s")
    record_test("T4.2: Jitter Random Variation", has_variation)

    # Test 5: Mocked Cascading Failover (Gemini Exhaustion -> Agnes Fallback)
    mock_rotator = ResilientAIKeyRotator(sleep_fn=lambda _: None)
    # Mark all Gemini keys as in cooldown
    for k in mock_rotator.gemini_keys:
        k.mark_rate_limited(60.0, current_time=time.time())

    # Call Gemini should return None
    g_res, g_tag = mock_rotator.call_gemini("sys", "user")
    record_test("T5.1: Gemini All Keys Cooldown Failfast", g_res is None, g_tag)

    # Mock Agnes success
    agnes_called = False
    original_call_agnes = mock_rotator.call_agnes

    def mock_agnes(sys_p, usr_p, *args, **kwargs):
        nonlocal agnes_called
        agnes_called = True
        return {"mock": "success"}, "Agnes AI (agnes-2.0-flash | Key ag-mock...1234)"

    mock_rotator.call_agnes = mock_agnes
    cascade_res, cascade_provider = mock_rotator.generate_quiz_ideas("sys", "user")
    record_test("T5.2: Cascading Fallback to Agnes Triggered", agnes_called)
    record_test(
        "T5.3: Cascading Response Received",
        cascade_res == {"mock": "success"} and "Agnes AI" in cascade_provider,
        cascade_provider
    )

    print("-" * 65)
    print(f"📊 SELF-TEST RESULTS: {passed}/{total} PASSED ({(passed/total)*100:.1f}%)")
    return passed == total


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Resilient AI Key Rotator (Milestone 4)")
    parser.add_argument("--test-only", action="store_true", help="Run only self-tests and exit")
    parser.add_argument("--no-live", action="store_true", help="Skip live API generation test")
    args = parser.parse_args()

    # 1. Run comprehensive self-tests
    tests_ok = run_self_tests(verbose=True)
    if not tests_ok:
        print("\n❌ SELF-TESTS FAILED!")
        sys.exit(1)

    if args.test_only or args.no_live:
        print("\n🎉 ALL SELF-TESTS PASSED CLEANLY (Zero-Leak Verified)!")
        sys.exit(0)

    # 2. Run live verification test
    print("\n" + "=" * 65)
    print("🤖 TESTING LIVE MULTI-PROVIDER AI KEY ROTATION & FALLBACK")
    rotator = get_ai_rotator()
    status = rotator.get_pool_status()
    print(f"🔑 Gemini Keys Pool: {status['gemini']['total']} keys loaded ({status['gemini']['healthy']} healthy)")
    print(f"🔑 Agnes AI Keys Pool: {status['agnes']['total']} keys loaded ({status['agnes']['healthy']} healthy, Base: {rotator.agnes_base_url})")
    print("=" * 65)

    test_sys = "You are a Mandarin Chinese Quiz Generator. You must respond strictly in valid JSON with an array of objects."
    test_user = "Generate 1 sample quiz idea about 'Học Tiếng Trung' with 5 words. Schema: {'topic': str, 'words': [{'hanzi': str, 'pinyin': str, 'meaning': str}]}"

    data, provider = rotator.generate_quiz_ideas(test_sys, test_user)
    if data:
        print(f"\n🎉 LIVE SUCCESS via [{provider}]!")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        print("\n✓ Live generation succeeded with zero credential leakage.")
        sys.exit(0)
    else:
        print(f"\n❌ LIVE CALL FAILED: {provider}")
        sys.exit(1)

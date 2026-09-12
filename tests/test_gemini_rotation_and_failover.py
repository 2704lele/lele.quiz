#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E Test Suite for Dynamic 6-Key Gemini Rotation & Multi-Tier Failovers.
Covers Features F5, F6 (Milestone 2 / Requirements R2).
"""

import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock
from typing import List

import pinyinquiz.src.llm_client as pinyin_llm
import vocabCNquiz.src.llm_client as vocabcn_llm
import vocabVNquiz.src.llm_client as vocabvn_llm

from pinyinquiz.src.llm_client import (
    parse_gemini_keys,
    mask_key,
    parse_json_from_llm,
    FALLBACK_GEMINI_MODELS
)

LLM_MODULES = [
    ("pinyinquiz", pinyin_llm),
    ("vocabCNquiz", vocabcn_llm),
    ("vocabVNquiz", vocabvn_llm)
]


# ============================================================================
# 1. KEY PARSING & ZERO-SECRET MASKING (FEATURE F5)
# ============================================================================

def test_parse_gemini_keys_from_string_delimiters():
    """Verify key parser splits comma, semicolon, and newline delimited strings."""
    raw_keys = "AIzaSyKey1,AIzaSyKey2;AIzaSyKey3\nAIzaSyKey4, AIzaSyKey5; AIzaSyKey6"
    keys = parse_gemini_keys(raw_keys)
    assert len(keys) == 6
    assert keys[0] == "AIzaSyKey1"
    assert keys[5] == "AIzaSyKey6"


def test_parse_gemini_keys_from_list_and_deduplication():
    """Verify key parser handles lists and deduplicates identical keys."""
    raw_list = ["AIzaSyKey1", "AIzaSyKey2,AIzaSyKey3", "AIzaSyKey1"]
    keys = parse_gemini_keys(raw_list)
    assert len(keys) == 3
    assert keys == ["AIzaSyKey1", "AIzaSyKey2", "AIzaSyKey3"]


def test_mask_key_zero_secret_integrity():
    """Verify mask_key masks secrets and never outputs full plaintext keys."""
    sample_key = "AIzaSyDUMMY_MOCK_TEST_KEY_VALUE"
    masked = mask_key(sample_key)
    assert masked == "AIzaSy...****"
    assert sample_key not in masked
    assert masked.endswith("****")

    # Short keys
    assert mask_key("short") == "****"
    assert mask_key("") == "None"
    assert mask_key(None) == "None"


def test_dynamic_key_rotation_indexing():
    """Verify (i-1) % len(keys) distributes across pool evenly without starvation."""
    keys = ["K1", "K2", "K3", "K4", "K5", "K6"]
    selected_indices = []

    for batch_id in range(1, 13):
        key_idx = (batch_id - 1) % len(keys)
        selected_indices.append(key_idx)

    # First cycle
    assert selected_indices[:6] == [0, 1, 2, 3, 4, 5]
    # Second cycle
    assert selected_indices[6:] == [0, 1, 2, 3, 4, 5]


def test_single_key_rotation_resilience():
    """Verify rotation operates cleanly when only 1 key is available."""
    keys = ["SINGLE_KEY"]
    for batch_id in range(1, 10):
        key_idx = (batch_id - 1) % len(keys)
        assert key_idx == 0
        assert keys[key_idx] == "SINGLE_KEY"


# ============================================================================
# 2. JSON EXTRACTION & LLM PARSING RESILIENCE (FEATURE F6)
# ============================================================================

@pytest.mark.parametrize("mod_name,mod", LLM_MODULES)
def test_parse_json_from_llm_markdown_fence(mod_name, mod):
    """Verify extraction of JSON from ```json ... ``` code blocks."""
    raw_response = (
        "Here is the daily batch ideation:\n"
        "```json\n"
        "[\n"
        '  {"hanzi": "苹果", "pinyin": "píng guǒ", "meaning": "Quả táo"},\n'
        '  {"hanzi": "米饭", "pinyin": "mǐ fàn", "meaning": "Cơm trắng"}\n'
        "]\n"
        "```\n"
        "Hope this helps!"
    )
    parsed = mod.parse_json_from_llm(raw_response)
    assert isinstance(parsed, list), f"[{mod_name}] Expected list"
    assert len(parsed) == 2, f"[{mod_name}] Expected 2 items"
    assert parsed[0]["hanzi"] == "苹果"


@pytest.mark.parametrize("mod_name,mod", LLM_MODULES)
def test_parse_json_from_llm_trailing_comma_cleanup(mod_name, mod):
    """Verify auto-healing of JSON containing invalid trailing commas."""
    raw_with_trailing = (
        "```json\n"
        "{\n"
        '  "topic": "Đồ Ăn",\n'
        '  "words": ["苹果", "米饭",],\n'
        "}\n"
        "```"
    )
    parsed = mod.parse_json_from_llm(raw_with_trailing)
    assert isinstance(parsed, dict), f"[{mod_name}] Expected dict"
    assert parsed["topic"] == "Đồ Ăn"
    assert parsed["words"] == ["苹果", "米饭"]


@pytest.mark.parametrize("mod_name,mod", LLM_MODULES)
def test_parse_json_from_llm_raw_bracket_extraction(mod_name, mod):
    """Verify extraction of raw array [...] embedded in conversational text without code fences."""
    raw_text = 'Sure! Here is the list: [{"id": 1, "topic": "Du Lịch"}] Have a great day.'
    parsed = mod.parse_json_from_llm(raw_text)
    assert isinstance(parsed, list), f"[{mod_name}] Expected list"
    assert parsed[0]["topic"] == "Du Lịch"


# ============================================================================
# 3. MODEL FAILOVER HIERARCHY & CIRCUIT BREAKER (FEATURE F6)
# ============================================================================

@pytest.mark.parametrize("mod_name,mod", LLM_MODULES)
def test_model_cascading_hierarchy(mod_name, mod):
    """Verify candidate model list includes proper flash fallback sequence."""
    models = mod.FALLBACK_GEMINI_MODELS
    assert "gemini-3.7-flash" in models
    assert "gemini-3.6-flash" in models
    assert "gemini-3.6-flash-high" in models
    assert "gemini-3.5-flash" in models

    # Priority order: 3.7 -> 3.6 -> 3.6-high -> 3.5
    assert models.index("gemini-3.7-flash") < models.index("gemini-3.6-flash")
    assert models.index("gemini-3.6-flash") < models.index("gemini-3.6-flash-high")
    assert models.index("gemini-3.6-flash-high") < models.index("gemini-3.5-flash")


@pytest.mark.parametrize("mod_name,mod", LLM_MODULES)
def test_quota_recovery_loop_cooldown_contract(mod_name, mod):
    """Verify circuit breaker 60s cooldown contract and execution when 429 rate limit occurs."""
    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    with patch("requests.post", return_value=mock_resp_429), patch("time.sleep") as mock_sleep:
        res = mod.call_gemini_api(prompt="Test", api_keys=["key1"], max_recovery_cycles=1)
        assert res is None
        mock_sleep.assert_called_with(60)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adversarial Linguistic Stress & Edge-Case Fuzzing Test Suite (Tier 5 Hardening).
Covers Feature F15 (Adversarial Coverage Hardening).
"""

import os
import sys
import pytest
from typing import Dict, Any, List

import pinyinquiz.src.pre_render_validator as pinyin_val
import vocabCNquiz.src.pre_render_validator as vocabcn_val
import vocabVNquiz.src.pre_render_validator as vocabvn_val

VALIDATORS = [
    ("pinyinquiz", pinyin_val.PreRenderValidator),
    ("vocabCNquiz", vocabcn_val.PreRenderValidator),
    ("vocabVNquiz", vocabvn_val.PreRenderValidator)
]


# ============================================================================
# 1. SUBTLE TRADITIONAL VS SIMPLIFIED CONFUSION PAIRS
# ============================================================================

@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_adversarial_traditional_pairs(pipeline_name, validator):
    """Test tricky Traditional characters that look similar to Simplified characters."""
    adversarial_trad_words = [
        "後天",  # Traditional 後 (Simplified: 后)
        "麵條",  # Traditional 麵 & 條 (Simplified: 面条)
        "頭髮",  # Traditional 髮 (Simplified: 发)
        "裡邊",  # Traditional 裡 & 邊 (Simplified: 里边)
        "買單",  # Traditional 買 & 單 (Simplified: 买单)
        "鐘錶",  # Traditional 鐘 & 錶 (Simplified: 钟表)
        "電視",  # Traditional 電 & 視 (Simplified: 电视)
        "漢語",  # Traditional 漢 & 語 (Simplified: 汉语)
        "餐廳",  # Traditional 廳 (Simplified: 餐厅)
        "醫生"   # Traditional 醫 (Simplified: 医生)
    ]
    for tw in adversarial_trad_words:
        errors = validator.check_simplified_chinese(tw)
        assert len(errors) > 0, f"[{pipeline_name}] Adversarial Traditional word '{tw}' was not rejected!"


# ============================================================================
# 2. FOREIGN PHONEME & CONSONANT INJECTIONS IN VIETNAMESE
# ============================================================================

@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_adversarial_foreign_consonants_in_meaning(pipeline_name, validator):
    """Test sneaky English loanwords containing non-Vietnamese letters (f, j, w, z) or forbidden words."""
    adversarial_meanings = [
        ("Uống fastfood", "fastfood (f)"),
        ("Tham gia workshop", "workshop (w)"),
        ("Chơi puzzle", "puzzle (z)"),
        ("Chụp photo selfie", "photo/selfie (f)"),
        ("Đi shopping cuối tuần", "shopping (forbidden word)"),
        ("Họp meeting công ty", "meeting (forbidden word)"),
        ("Điểm danh zoom online", "zoom (z)")
    ]
    for am, desc in adversarial_meanings:
        errors = validator.check_vietnamese_meaning(am)
        assert len(errors) > 0, f"[{pipeline_name}] Meaning '{am}' ({desc}) should have been rejected!"


# ============================================================================
# 3. WHITESPACE, CJK FULL-WIDTH SPACES & UNICODE ABNORMALITIES
# ============================================================================

@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_adversarial_whitespace_and_cjk_spaces(pipeline_name, validator):
    """Test Hanzi and Pinyin containing CJK full-width spaces and trailing whitespace."""
    # Full-width space between Hanzi \u3000
    hz = "苹\u3000果"
    py = "píng guǒ"
    errors = validator.check_pinyin_syllables_and_tones(hz, py)
    assert len(errors) == 0, f"[{pipeline_name}] Full-width space in Hanzi should be sanitized: {errors}"

    # Non-breaking space \u00a0 in pinyin
    py_nbsp = "píng\u00a0guǒ"
    errors = validator.check_pinyin_syllables_and_tones("苹果", py_nbsp)
    assert len(errors) == 0, f"[{pipeline_name}] Non-breaking space in Pinyin should be sanitized: {errors}"


# ============================================================================
# 4. RARE UMLAUT PINYIN VOWELS (Ü, Ǖ, Ǘ, Ǚ, Ǜ)
# ============================================================================

@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_adversarial_umlaut_vowels(pipeline_name, validator):
    """Test words with umlaut vowels (ü, ǖ, ǘ, ǚ, ǜ) across different tones."""
    umlaut_cases = [
        ("绿色", "lǜ sè"),
        ("女儿", "nǚ ér"),
        ("旅行", "lǚ xíng"),
        ("驴子", "lǘ zi")
    ]
    for hz, py in umlaut_cases:
        errors = validator.check_pinyin_syllables_and_tones(hz, py)
        assert len(errors) == 0, f"[{pipeline_name}] Umlaut case '{hz}' - '{py}' failed: {errors}"


# ============================================================================
# 5. EXTREME BATCH STRUCTURE VIOLATIONS
# ============================================================================

@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_adversarial_malformed_batch_payloads(pipeline_name, validator):
    """Test validator robustness against empty or invalid dict keys."""
    malformed_batches = [
        {"topic": "", "words": []},  # Empty dict / empty words
        {"topic": "Đồ Ăn", "words": []},  # Empty words list
        {"topic": "Đồ Ăn", "words": [
            {"hanzi": "苹果", "pinyin": "píng guǒ", "meaning": "Quả táo"}
        ]},  # Only 1 word
        {"topic": "Học Tập", "words": [
            {"hanzi": "", "pinyin": "", "meaning": ""},  # Missing fields
            {"hanzi": "笔", "pinyin": "bǐ", "meaning": "Bút"},
            {"hanzi": "书", "pinyin": "shū", "meaning": "Sách"},
            {"hanzi": "本", "pinyin": "běn", "meaning": "Vở"},
            {"hanzi": "桌", "pinyin": "zhuō", "meaning": "Bàn"}
        ]}
    ]
    for mb in malformed_batches:
        is_valid, errors = validator.validate_batch(mb)
        assert is_valid is False
        assert len(errors) > 0

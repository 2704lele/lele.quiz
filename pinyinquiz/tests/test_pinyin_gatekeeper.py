#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Suite for Pinyin Quiz Gatekeeper 1 & Pre-Render Validation.
Tests 5 Linguistic Rules for Pinyin (Hanzi -> Pinyin) quiz generation.
"""

import os
import sys
import pytest

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from src.pre_render_validator import (
    PreRenderValidator,
    STRICT_TRADITIONAL_CHARS,
    ENGLISH_FORBIDDEN_WORDS,
    VALID_NEUTRAL_SYLLABLES
)

def test_rule_1_simplified_chinese_valid():
    """Simplified Chinese characters must pass validation."""
    valid_words = ["妈妈", "爸爸", "学校", "大门", "中国", "谢谢", "买东西", "书包", "铅笔"]
    for hz in valid_words:
        errors = PreRenderValidator.check_simplified_chinese(hz)
        assert len(errors) == 0, f"Expected '{hz}' to pass, got: {errors}"

def test_rule_1_traditional_chinese_rejected():
    """Traditional Chinese characters must be rejected."""
    for tc in ["媽媽", "開門", "買東西", "廣東"]:
        errors = PreRenderValidator.check_simplified_chinese(tc)
        assert len(errors) > 0, f"Expected '{tc}' to be rejected"

def test_rule_2_single_topic_valid():
    """Valid single topics must pass validation."""
    valid_topics = ["Đồ Dùng Học Tập", "Đồ Ăn Hàng Ngày", "Giao Tiếp Xã Hội", "Thời Gian"]
    for top in valid_topics:
        errors = PreRenderValidator.check_single_topic(top)
        assert len(errors) == 0, f"Expected topic '{top}' to pass, got: {errors}"

def test_rule_2_topic_delimiters_and_abbreviations_rejected():
    """Topics with list delimiters or abbreviations must be rejected."""
    invalid_topics = [
        "Đồ Ăn; Thức Uống",
        "Trường Học | Thư Viện",
        "Chào Hỏi, v.v.",
        "Đồ dùng vv",
        "Phương tiện etc."
    ]
    for top in invalid_topics:
        errors = PreRenderValidator.check_single_topic(top)
        assert len(errors) > 0, f"Expected topic '{top}' to be rejected"

def test_rule_3_vietnamese_meaning_no_english():
    """Pure Vietnamese meanings must pass, English words rejected."""
    valid_meanings = ["Cái bàn học", "Quả táo đỏ", "Đi học buổi sáng", "Uống nước lọc"]
    for vm in valid_meanings:
        errors = PreRenderValidator.check_vietnamese_meaning(vm)
        assert len(errors) == 0, f"Expected '{vm}' to pass, got: {errors}"

    invalid_meanings = ["Ăn apple", "Uống coffee", "Đi bằng taxi", "Mua pen"]
    for im in invalid_meanings:
        errors = PreRenderValidator.check_vietnamese_meaning(im)
        assert len(errors) > 0, f"Expected '{im}' to be rejected"

def test_rule_4_pinyin_syllable_count_and_tones():
    """Pinyin syllables must match Hanzi length 1:1 with tone marks."""
    valid_pairs = [
        ("爸爸", "bà ba"),
        ("妈妈", "mā ma"),
        ("苹果", "píng guǒ"),
        ("公共汽车", "gōng gòng qì chē")
    ]
    for hz, py in valid_pairs:
        errors = PreRenderValidator.check_pinyin_syllables_and_tones(hz, py)
        assert len(errors) == 0, f"Expected '{hz}' - '{py}' to pass, got: {errors}"

    # Syllable mismatch
    errors = PreRenderValidator.check_pinyin_syllables_and_tones("苹果", "píng")
    assert len(errors) > 0, "Expected syllable count mismatch to fail"

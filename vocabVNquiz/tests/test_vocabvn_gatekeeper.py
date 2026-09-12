#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Suite for VocabVN Quiz Gatekeeper 1 & Pre-Render Validation.
Tests 5 Linguistic Rules for VocabVN (Tiếng Việt -> Hanzi) quiz generation.
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
    valid_topics = ["Từ Vựng Du Lịch", "Đồ Dùng Hàng Ngày", "Giao Tiếp Xã Hội", "Thời Gian"]
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

    invalid_meanings = ["Ăn apple", "Uống coffee", "Đi bằng taxi"]
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

def test_rule_5_full_batch_validation_valid():
    """A valid 5-word batch must pass full Gatekeeper 1 validation."""
    batch = {
        "id": "4",
        "topic": "Gia Đình Thân Yêu",
        "level": "HSK 1",
        "words": [
            {"hanzi": "爸爸", "pinyin": "bà ba", "meaning": "Bố"},
            {"hanzi": "妈妈", "pinyin": "mā ma", "meaning": "Mẹ"},
            {"hanzi": "儿子", "pinyin": "ér zi", "meaning": "Con trai"},
            {"hanzi": "女儿", "pinyin": "nǚ ér", "meaning": "Con gái"},
            {"hanzi": "朋友", "pinyin": "péng you", "meaning": "Bạn bè"}
        ]
    }
    is_valid, errors = PreRenderValidator.validate_batch(batch)
    assert is_valid is True, f"Expected valid batch, got errors: {errors}"
    assert len(errors) == 0

def test_rule_5_intra_batch_duplicates_rejected():
    """Batches with duplicate Hanzi or duplicate Vietnamese meaning must be rejected."""
    batch_dup_hz = {
        "id": "10",
        "topic": "Trùng Từ Vựng",
        "level": "HSK 1",
        "words": [
            {"hanzi": "爸爸", "pinyin": "bà ba", "meaning": "Bố"},
            {"hanzi": "爸爸", "pinyin": "bà ba", "meaning": "Ba"},
            {"hanzi": "儿子", "pinyin": "ér zi", "meaning": "Con trai"},
            {"hanzi": "女儿", "pinyin": "nǚ ér", "meaning": "Con gái"},
            {"hanzi": "朋友", "pinyin": "péng you", "meaning": "Bạn bè"}
        ]
    }
    is_valid, errors = PreRenderValidator.validate_batch(batch_dup_hz)
    assert is_valid is False
    assert any("Trùng chữ Hán" in e for e in errors)

def test_history_deduplication_rejected():
    """Batches colliding with history topic or having >=2 overlapping words must be rejected."""
    history = {
        "recent_topics": ["Đồ Ăn", "Du Lịch"],
        "past_batches": [
            {"id": "2", "topic": "Đồ Ăn", "words": ["米饭", "面条", "苹果", "茶水", "牛奶"]}
        ]
    }
    # 1. Topic collision
    batch_top_dup = {
        "id": "11",
        "topic": "Đồ Ăn",
        "level": "HSK 1",
        "words": [
            {"hanzi": "包子", "pinyin": "bāo zi", "meaning": "Bánh bao"},
            {"hanzi": "饺子", "pinyin": "jiǎo zi", "meaning": "Sủi cảo"},
            {"hanzi": "鸡蛋", "pinyin": "jī dàn", "meaning": "Trứng gà"},
            {"hanzi": "面包", "pinyin": "miàn bāo", "meaning": "Bánh mì"},
            {"hanzi": "豆腐", "pinyin": "dòu fu", "meaning": "Đậu phụ"}
        ]
    }
    is_valid, errors = PreRenderValidator.validate_batch(batch_top_dup, history=history)
    assert is_valid is False
    assert any("trùng lặp với chủ đề" in e for e in errors)

    # 2. Overlap >= 2 words
    batch_word_overlap = {
        "id": "12",
        "topic": "Món Ăn Sáng",
        "level": "HSK 1",
        "words": [
            {"hanzi": "米饭", "pinyin": "mǐ fàn", "meaning": "Cơm trắng"},
            {"hanzi": "面条", "pinyin": "miàn tiáo", "meaning": "Mì sợi dai"},
            {"hanzi": "鸡蛋", "pinyin": "jī dàn", "meaning": "Trứng gà"},
            {"hanzi": "面包", "pinyin": "miàn bāo", "meaning": "Bánh mì"},
            {"hanzi": "豆腐", "pinyin": "dòu fu", "meaning": "Đậu phụ"}
        ]
    }
    is_valid, errors = PreRenderValidator.validate_batch(batch_word_overlap, history=history)
    assert is_valid is False
    assert any("Trùng lặp cặp" in e for e in errors)

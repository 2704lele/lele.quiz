#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_anti_duplication.py
Comprehensive Unit & Integration Tests for Gatekeeper 1 QC Topic & Word Anti-Duplication:
1. Topic normalization & string canonicalization
2. Strict Zero-Duplicate Topic Name detection
3. Exact Duplicate Hanzi Word detection within tab
4. Tab-Isolated Recent Hanzi Character overlap (< 35%)
5. Global Hanzi Character overlap (< 40%)
6. Incremental registration & live state updates
"""

import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.linguistic_qc import (
    GlobalHanziFrequencyMatrix,
    normalize_topic_string,
)


def test_normalize_topic_string():
    """Verify topic normalization strips prefixes, punctuation, and unifies symbols."""
    assert normalize_topic_string("1 Nghĩa 5 Cấp • Tự tin / Kiêu hãnh") == "tự tin kiêu hãnh"
    assert normalize_topic_string("1 Nghĩa 5 Cấp - Vui vẻ & Hạnh phúc") == "vui vẻ và hạnh phúc"
    assert normalize_topic_string("Đồ Ăn & Thức Uống (HSK 1)") == "đồ ăn và thức uống hsk 1"
    assert normalize_topic_string("  Phương Tiện Giao Thông!  ") == "phương tiện giao thông"


def test_matrix_topic_deduplication_detection():
    """Verify matrix detects duplicate topics with case-insensitivity and punctuation variations."""
    matrix = GlobalHanziFrequencyMatrix(spreadsheet_client=None)
    # Simulate existing pinyin tab data
    matrix.tab_topics["pinyin"].add("đồ ăn và thức uống")
    matrix.tab_raw_topics["pinyin"].append("Đồ ăn và Thức uống")

    assert matrix.is_topic_duplicated("pinyin", "Đồ ăn và Thức uống") is True
    assert matrix.is_topic_duplicated("pinyin", "ĐỒ ĂN & THỨC UỐNG") is True
    assert matrix.is_topic_duplicated("pinyin", "đồ ăn và thức uống") is True
    assert matrix.is_topic_duplicated("pinyin", "Phương tiện giao thông") is False


def test_matrix_evaluate_rejects_duplicate_topic():
    """Verify evaluate_candidate_batch immediately rejects duplicate topic."""
    matrix = GlobalHanziFrequencyMatrix(spreadsheet_client=None)
    matrix.tab_topics["pinyin"].add("đồ ăn và thức uống")
    matrix.tab_raw_topics["pinyin"].append("Đồ ăn và Thức uống")

    candidate_words = [
        {"hanzi": "香蕉", "pinyin": "xiāng jiāo", "meaning": "quả chuối"},
        {"hanzi": "西瓜", "pinyin": "xī guā", "meaning": "dưa hấu"}
    ]

    is_valid, ratio, errs, reason = matrix.evaluate_candidate_batch(
        candidate_words, topic="Đồ ăn và Thức uống", tab="pinyin"
    )
    assert is_valid is False
    assert "Duplicate Topic" in reason


def test_matrix_evaluate_rejects_duplicate_hanzi_words():
    """Verify evaluate_candidate_batch rejects exact Hanzi words already existing in tab."""
    matrix = GlobalHanziFrequencyMatrix(spreadsheet_client=None)
    matrix.tab_words["pinyin"].add("米饭")
    matrix.tab_words["pinyin"].add("牛奶")

    candidate_words = [
        {"hanzi": "米饭", "pinyin": "mǐ fàn", "meaning": "cơm"},
        {"hanzi": "西瓜", "pinyin": "xī guā", "meaning": "dưa hấu"}
    ]

    is_valid, ratio, errs, reason = matrix.evaluate_candidate_batch(
        candidate_words, topic="Chủ đề trái cây nhiệt đới mới", tab="pinyin"
    )
    assert is_valid is False
    assert "Duplicate Word" in reason
    assert "米饭" in errs


def test_matrix_tab_isolated_character_overlap():
    """Verify tab-isolated recent Hanzi character overlap triggers rejection at >35%."""
    matrix = GlobalHanziFrequencyMatrix(spreadsheet_client=None)
    matrix.tab_recent_hanzi["vocabCN"] = list("苹果香蕉西瓜葡萄草莓")  # 10 chars

    # Candidate with 2 overlapping chars (苹果) out of 4 total chars (苹果桃李) = 50% overlap > 35%
    candidate_words = [
        {"hanzi": "苹果", "pinyin": "píng guǒ", "meaning": "quả táo"},
        {"hanzi": "桃李", "pinyin": "táo lǐ", "meaning": "đào mận"}
    ]

    is_valid, ratio, errs, reason = matrix.evaluate_candidate_batch(
        candidate_words, topic="Chủ đề các loại hoa quả bốn mùa", tab="vocabCN"
    )
    assert is_valid is False
    assert "overlap with tab 'vocabCN' recent Hanzi" in reason or "35%" in reason


def test_matrix_register_ingested_batch_updates_all_registries():
    """Verify register_ingested_batch dynamically updates topics, words, tab recent and global recent."""
    matrix = GlobalHanziFrequencyMatrix(spreadsheet_client=None)
    words = [
        {"hanzi": "飞机", "pinyin": "fēi jī", "meaning": "máy bay"},
        {"hanzi": "轮船", "pinyin": "lún chuán", "meaning": "tàu thủy"}
    ]
    topic = "Phương tiện đường biển và đường hàng không"

    matrix.register_ingested_batch("pinyin", words, topic=topic)

    assert matrix.is_topic_duplicated("pinyin", topic) is True
    assert "飞机" in matrix.get_tab_existing_words("pinyin")
    assert "轮船" in matrix.get_tab_existing_words("pinyin")
    assert "飞" in matrix.get_tab_recent_50_tracked("pinyin")
    assert "船" in matrix.get_tab_recent_50_tracked("pinyin")

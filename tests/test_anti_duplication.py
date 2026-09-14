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
    clean_quiz_topic,
    validate_topic_spirit,
)


def test_normalize_topic_string():
    """Verify topic normalization strips prefixes, punctuation, and unifies symbols."""
    assert normalize_topic_string("1 Nghĩa 5 Cấp • Tự tin / Kiêu hãnh") == "tự tin kiêu hãnh"
    assert normalize_topic_string("1 Nghĩa 5 Cấp - Vui vẻ & Hạnh phúc") == "vui vẻ và hạnh phúc"
    assert normalize_topic_string("Đồ Ăn & Thức Uống (HSK 1)") == "đồ ăn và thức uống"
    assert normalize_topic_string("Chủ đề: Đồ Ăn & Thức Uống") == "đồ ăn và thức uống"
    assert normalize_topic_string("  Phương Tiện Giao Thông!  ") == "phương tiện giao thông"


def test_clean_quiz_topic():
    """Verify clean_quiz_topic strips prefixes, HSK tags, and formats multilevels."""
    assert clean_quiz_topic("Chủ đề: Đồ Gia Dụng (HSK 1)") == "Đồ Gia Dụng"
    assert clean_quiz_topic("Thử thách: Rau Củ Quả [HSK 2]") == "Rau Củ Quả"
    assert clean_quiz_topic("Từ vựng về: Phương Tiện Giao Thông") == "Phương Tiện Giao Thông"
    assert clean_quiz_topic("1 Nghĩa 5 Cấp • Tự Tin (HSK 1-5)", tab="multilevels") == "1 Nghĩa 5 Cấp • Tự Tin"
    assert clean_quiz_topic("Khái niệm: Vui Vẻ", tab="multilevels") == "1 Nghĩa 5 Cấp • Vui Vẻ"


def test_validate_topic_spirit():
    """Verify validate_topic_spirit rejects phonetic theory topics and overly long topics."""
    # Valid concise topics
    valid, errs = validate_topic_spirit("Đồ Gia Dụng", "pinyin")
    assert valid is True
    assert len(errs) == 0

    valid, errs = validate_topic_spirit("Phương Tiện Giao Thông", "vocabCN")
    assert valid is True

    # Banned phonetic theory topics
    valid, errs = validate_topic_spirit("Thử thách Phân biệt Thanh điệu 1 và 4", "pinyin")
    assert valid is False
    assert "thanh điệu" in errs[0].lower()

    valid, errs = validate_topic_spirit("Luyện đọc Thanh nhẹ và Biến điệu", "pinyin")
    assert valid is False

    valid, errs = validate_topic_spirit("Phân biệt Âm bật hơi", "pinyin")
    assert valid is False

    # Overly long topic
    valid, errs = validate_topic_spirit("Tổng hợp các loại từ vựng chỉ đồ ăn thức uống ngon miệng", "pinyin")
    assert valid is False
    assert "quá dài" in errs[0].lower()


def test_matrix_evaluate_rejects_banned_phonetic_theory_topic():
    """Verify evaluate_candidate_batch rejects topics with phonetic theory keywords."""
    matrix = GlobalHanziFrequencyMatrix(spreadsheet_client=None)
    candidate_words = [
        {"hanzi": "香蕉", "pinyin": "xiāng jiāo", "meaning": "quả chuối"},
        {"hanzi": "西瓜", "pinyin": "xī guā", "meaning": "dưa hấu"}
    ]
    is_valid, ratio, errs, reason = matrix.evaluate_candidate_batch(
        candidate_words, topic="Luyện đọc Thanh nhẹ tiếng Trung", tab="pinyin"
    )
    assert is_valid is False
    assert "Topic Spirit" in reason


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


def test_matrix_evaluate_rejects_pairwise_word_overlap_ge_3():
    """Verify evaluate_candidate_batch rejects candidate batch if it overlaps >= 3 words with any past row."""
    matrix = GlobalHanziFrequencyMatrix(spreadsheet_client=None)
    # Simulate an existing row in pinyin tab with 5 words
    matrix.tab_row_words["pinyin"].append({"苹果", "香蕉", "西瓜", "葡萄", "草莓"})

    # Candidate with 3 overlapping words (苹果, 香蕉, 西瓜) -> MUST BE REJECTED
    candidate_bad = [
        {"hanzi": "苹果", "pinyin": "píng guǒ", "meaning": "quả táo"},
        {"hanzi": "香蕉", "pinyin": "xiāng jiāo", "meaning": "quả chuối"},
        {"hanzi": "西瓜", "pinyin": "xī guā", "meaning": "dưa hấu"},
        {"hanzi": "橘子", "pinyin": "jú zi", "meaning": "quả quýt"},
        {"hanzi": "桃子", "pinyin": "táo zi", "meaning": "quả đào"},
    ]
    is_valid, ratio, errs, reason = matrix.evaluate_candidate_batch(
        candidate_bad, topic="Chủ đề trái cây nhiệt đới mới", tab="pinyin"
    )
    assert is_valid is False
    assert "Word Overlap >= 3" in reason
    assert len(errs) == 3

    # Candidate with only 2 overlapping words (苹果, 香蕉) -> MUST BE ALLOWED (as long as char ratio permits)
    matrix.tab_recent_hanzi["pinyin"] = []  # Clear char overlap constraint for isolation
    candidate_ok = [
        {"hanzi": "苹果", "pinyin": "píng guǒ", "meaning": "quả táo"},
        {"hanzi": "香蕉", "pinyin": "xiāng jiāo", "meaning": "quả chuối"},
        {"hanzi": "梨", "pinyin": "lí", "meaning": "quả lê"},
        {"hanzi": "芒果", "pinyin": "máng guǒ", "meaning": "quả xoài"},
        {"hanzi": "樱桃", "pinyin": "yīng táo", "meaning": "quả anh đào"},
    ]
    is_valid_ok, _, _, _ = matrix.evaluate_candidate_batch(
        candidate_ok, topic="Chủ đề vườn cây ăn trái", tab="pinyin"
    )
    assert is_valid_ok is True


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

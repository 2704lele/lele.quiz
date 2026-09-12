#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E Test Suite for Gatekeeper 1 Deterministic Engine across All 3 Pipelines.
Covers Features F7, F8, F15 (Milestone 2 / Requirements R2).
Tests 5 Linguistic Rules, Negative Context Deduplication, and VocabVN Harmonization.
"""

import os
import sys
import pytest
from typing import Dict, Any, List

QUIZ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Import validators from all 3 pipelines
import pinyinquiz.src.pre_render_validator as pinyin_val
import vocabCNquiz.src.pre_render_validator as vocabcn_val
import vocabVNquiz.src.pre_render_validator as vocabvn_val

VALIDATORS = [
    ("pinyinquiz", pinyin_val.PreRenderValidator),
    ("vocabCNquiz", vocabcn_val.PreRenderValidator),
    ("vocabVNquiz", vocabvn_val.PreRenderValidator)
]


# ============================================================================
# 1. RULE 1: 100% SIMPLIFIED CHINESE (0% TRADITIONAL CHARACTERS)
# ============================================================================

@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_rule_1_simplified_chinese_valid(pipeline_name, validator):
    """Simplified Chinese characters must pass Rule 1 across all 3 pipelines."""
    valid_words = [
        "妈妈", "爸爸", "学校", "大门", "中国", "谢谢", "买东西",
        "书包", "铅笔", "苹果", "公共汽车", "出租车", "高兴", "飞机", "米饭"
    ]
    for hz in valid_words:
        errors = validator.check_simplified_chinese(hz)
        assert len(errors) == 0, f"[{pipeline_name}] Expected '{hz}' to pass Simplified Chinese check, got: {errors}"


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_rule_1_traditional_chinese_single_char_rejected(pipeline_name, validator):
    """Traditional Chinese single characters must be rejected across all 3 pipelines."""
    trad_chars = ["國", "學", "門", "媽", "體", "書", "買", "點", "開", "關", "車", "愛", "話", "錢", "飯"]
    for tc in trad_chars:
        errors = validator.check_simplified_chinese(tc)
        assert len(errors) > 0, f"[{pipeline_name}] Expected Traditional char '{tc}' to be rejected"
        assert any("Phồn thể" in err for err in errors), f"[{pipeline_name}] Error message should mention 'Phồn thể': {errors}"


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_rule_1_traditional_chinese_multi_char_rejected(pipeline_name, validator):
    """Words containing Traditional Chinese characters must be rejected."""
    trad_words = [
        ("媽媽", "Traditional 媽"),
        ("開門", "Traditional 開 and 門"),
        ("買東西", "Traditional 買"),
        ("廣東", "Traditional 廣 and 東"),
        ("學生", "Traditional 學"),
        ("電話", "Traditional 電 and 話"),
        ("飛機", "Traditional 飛 and 機")
    ]
    for hz, desc in trad_words:
        errors = validator.check_simplified_chinese(hz)
        assert len(errors) > 0, f"[{pipeline_name}] Expected '{hz}' ({desc}) to be rejected"


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_rule_1_universal_heritage_characters_accepted(pipeline_name, validator):
    """Universal heritage characters identical in both Simplified and Traditional must be accepted."""
    heritage_words = ["生", "衣服", "桌椅", "床", "房间", "数量", "折扣", "水", "人", "天"]
    for hw in heritage_words:
        errors = validator.check_simplified_chinese(hw)
        assert len(errors) == 0, f"[{pipeline_name}] Expected heritage word '{hw}' to pass, got: {errors}"


# ============================================================================
# 2. RULE 2: SINGLE FOCUSED TOPIC VALIDATION
# ============================================================================

@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_rule_2_single_topic_valid(pipeline_name, validator):
    """Valid natural single topics must pass Rule 2."""
    valid_topics = [
        "Đồ Dùng Nhà Bếp",
        "HSK 1 • Đồ Ăn",
        "HSK 2 • Giao Thông",
        "Cảm xúc và tâm trạng",
        "Thời tiết bốn mùa",
        "Gia Đình & Bạn Bè",
        "Từ Vựng Du Lịch"
    ]
    for top in valid_topics:
        errors = validator.check_single_topic(top)
        assert len(errors) == 0, f"[{pipeline_name}] Expected topic '{top}' to pass, got: {errors}"


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_rule_2_topic_delimiters_and_abbreviations_rejected(pipeline_name, validator):
    """Topics with list delimiters (; or |) or abbreviations (etc., v.v.) must be rejected."""
    invalid_topics = [
        "Đồ Ăn; Thức Uống",
        "Gia Đình | Nhà Trường",
        "Chào Hỏi, v.v.",
        "Đồ dùng vv",
        "Phương tiện etc.",
        "Trường Học | Thư Viện",
        "Đồ Ăn; Trái Cây; Thức Uống"
    ]
    for top in invalid_topics:
        errors = validator.check_single_topic(top)
        assert len(errors) > 0, f"[{pipeline_name}] Expected topic '{top}' to be rejected"


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_rule_2_topic_length_boundaries(pipeline_name, validator):
    """Topic length must be between 2 and 50 characters."""
    assert len(validator.check_single_topic("")) > 0  # Empty
    assert len(validator.check_single_topic("A")) > 0   # Too short (<2)
    assert len(validator.check_single_topic("A" * 51)) > 0  # Too long (>50)
    assert len(validator.check_single_topic("AB")) == 0  # Min boundary (2)
    assert len(validator.check_single_topic("A" * 50)) == 0  # Max boundary (50)


# ============================================================================
# 3. RULE 3: 100% PURE VIETNAMESE DEFINITION & FORBIDDEN ENGLISH FILTER
# ============================================================================

@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_rule_3_vietnamese_meaning_valid(pipeline_name, validator):
    """Pure Vietnamese meanings and homographs must pass Rule 3."""
    valid_meanings = [
        "Cái bàn học", "Quả táo đỏ", "Đi học buổi sáng", "Uống nước lọc",
        "Sữa bò tươi", "Máy bay quốc tế", "Ga tàu hỏa", "Quyển vở ghi chép",
        "Ăn no", "No bụng", "Tự do", "Lý do", "Say xe", "Say rượu", "Thỏi son", "Men rượu"
    ]
    for vm in valid_meanings:
        errors = validator.check_vietnamese_meaning(vm)
        assert len(errors) == 0, f"[{pipeline_name}] Expected '{vm}' to pass, got: {errors}"


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_rule_3_forbidden_english_words_rejected(pipeline_name, validator):
    """Vietnamese meanings containing forbidden English words must be rejected."""
    invalid_meanings = [
        ("Ăn apple", "apple"),
        ("Uống coffee buổi sáng", "coffee"),
        ("Mua chair mới", "chair"),
        ("Đi bằng car", "car"),
        ("Đi taxi đến school", "school"),
        ("Gặp doctor tại hospital", "doctor")
    ]
    for im, desc in invalid_meanings:
        errors = validator.check_vietnamese_meaning(im)
        assert len(errors) > 0, f"[{pipeline_name}] Expected '{im}' (contains '{desc}') to be rejected"


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_rule_3_loanword_whitelist_accepted(pipeline_name, validator):
    """Legitimate modern Vietnamese loanwords in whitelist must be accepted."""
    whitelist_meanings = [
        "Cà phê sữa đá",
        "Đi xe buýt đến trường",
        "Đi xe taxi về nhà",
        "Xem video trên tivi",
        "Kết nối mạng wifi internet",
        "Áo sơ-mi trắng"
    ]
    for wm in whitelist_meanings:
        errors = validator.check_vietnamese_meaning(wm)
        assert len(errors) == 0, f"[{pipeline_name}] Expected loanword meaning '{wm}' to be accepted, got: {errors}"


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_rule_3_hidden_pinyin_artifacts_rejected(pipeline_name, validator):
    """Meanings containing hidden pinyin underscore '_' artifacts must be rejected."""
    artifact_meanings = [
        "p _ _ _   g _ _",
        "Quả táo _ _",
        "b _   b _"
    ]
    for am in artifact_meanings:
        errors = validator.check_vietnamese_meaning(am)
        assert len(errors) > 0, f"[{pipeline_name}] Expected '{am}' to be rejected due to underscore artifacts"


# ============================================================================
# 4. RULE 4: 1:1 PINYIN SYLLABLE & TONE VALIDATION
# ============================================================================

@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_rule_4_pinyin_syllables_and_tones_valid(pipeline_name, validator):
    """Pinyin syllables must match Hanzi length 1:1 with valid tones."""
    valid_pairs = [
        ("爸爸", "bà ba"),
        ("妈妈", "mā ma"),
        ("苹果", "píng guǒ"),
        ("公共汽车", "gōng gòng qì chē"),
        ("飞机场", "fēi jī chǎng"),
        ("你好", "nǐ hǎo")
    ]
    for hz, py in valid_pairs:
        errors = validator.check_pinyin_syllables_and_tones(hz, py)
        assert len(errors) == 0, f"[{pipeline_name}] Expected '{hz}' - '{py}' to pass, got: {errors}"


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_rule_4_erhua_contractions_valid(pipeline_name, validator):
    """Erhua contracted syllables ending with 'r' must be accepted."""
    erhua_pairs = [
        ("哪儿", "nǎr"),
        ("这儿", "zhèr"),
        ("那儿", "nàr"),
        ("玩儿", "wánr"),
        ("花儿", "huār"),
        ("一点儿", "yì diǎnr")
    ]
    for hz, py in erhua_pairs:
        errors = validator.check_pinyin_syllables_and_tones(hz, py)
        assert len(errors) == 0, f"[{pipeline_name}] Expected Erhua '{hz}' - '{py}' to pass, got: {errors}"


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_rule_4_syllable_count_mismatch_rejected(pipeline_name, validator):
    """Pinyin syllable count not matching Hanzi length must be rejected."""
    mismatches = [
        ("苹果", "píng"),  # 2 Hanzi, 1 Pinyin
        ("苹果", "píng guǒ shù"),  # 2 Hanzi, 3 Pinyin
        ("公共汽车", "gōng gòng")  # 4 Hanzi, 2 Pinyin
    ]
    for hz, py in mismatches:
        errors = validator.check_pinyin_syllables_and_tones(hz, py)
        assert len(errors) > 0, f"[{pipeline_name}] Expected syllable mismatch '{hz}' - '{py}' to fail"


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_rule_4_missing_tones_rejected(pipeline_name, validator):
    """Multi-syllable words without tone marks or invalid neutral tones must fail."""
    invalid_tones = [
        ("苹果", "ping guo"),  # No tone marks
        ("飞机", "fei ji"),    # No tone marks
        ("学校", "xue xiao")   # No tone marks
    ]
    for hz, py in invalid_tones:
        errors = validator.check_pinyin_syllables_and_tones(hz, py)
        assert len(errors) > 0, f"[{pipeline_name}] Expected missing tones '{hz}' - '{py}' to fail"


# ============================================================================
# 5. RULE 5: FULL BATCH & NEGATIVE CONTEXT DEDUPLICATION
# ============================================================================

@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_rule_5_full_batch_validation_valid(pipeline_name, validator, sample_valid_pinyin_batch):
    """A standard 5-word batch must pass full Gatekeeper 1 validation."""
    is_valid, errors = validator.validate_batch(sample_valid_pinyin_batch)
    assert is_valid is True, f"[{pipeline_name}] Expected valid batch, got errors: {errors}"
    assert len(errors) == 0


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_rule_5_intra_batch_duplicates_rejected(pipeline_name, validator):
    """Batches with duplicate Hanzi or duplicate Vietnamese meanings must be rejected."""
    dup_hanzi_batch = {
        "id": "201",
        "topic": "Đồ Ăn",
        "level": "HSK 1",
        "words": [
            {"hanzi": "苹果", "pinyin": "píng guǒ", "meaning": "Quả táo"},
            {"hanzi": "苹果", "pinyin": "píng guǒ", "meaning": "Trái táo tây"},
            {"hanzi": "米饭", "pinyin": "mǐ fàn", "meaning": "Cơm trắng"},
            {"hanzi": "面条", "pinyin": "miàn tiáo", "meaning": "Mì sợi"},
            {"hanzi": "喝水", "pinyin": "hē shuǐ", "meaning": "Uống nước"}
        ]
    }
    is_valid, errors = validator.validate_batch(dup_hanzi_batch)
    assert is_valid is False
    assert any("Trùng chữ Hán" in e for e in errors)

    dup_meaning_batch = {
        "id": "202",
        "topic": "Đồ Ăn",
        "level": "HSK 1",
        "words": [
            {"hanzi": "苹果", "pinyin": "píng guǒ", "meaning": "Quả táo"},
            {"hanzi": "红苹果", "pinyin": "hóng píng guǒ", "meaning": "Quả táo"},
            {"hanzi": "米饭", "pinyin": "mǐ fàn", "meaning": "Cơm trắng"},
            {"hanzi": "面条", "pinyin": "miàn tiáo", "meaning": "Mì sợi"},
            {"hanzi": "喝水", "pinyin": "hē shuǐ", "meaning": "Uống nước"}
        ]
    }
    is_valid, errors = validator.validate_batch(dup_meaning_batch)
    assert is_valid is False
    assert any("Trùng nghĩa tiếng Việt" in e for e in errors)


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_rule_5_invalid_word_count_rejected(pipeline_name, validator):
    """Batches with fewer or more than 5 words must be rejected."""
    four_word_batch = {
        "id": "203",
        "topic": "Gia Đình",
        "level": "HSK 1",
        "words": [
            {"hanzi": "爸爸", "pinyin": "bà ba", "meaning": "Bố"},
            {"hanzi": "妈妈", "pinyin": "mā ma", "meaning": "Mẹ"},
            {"hanzi": "儿子", "pinyin": "ér zi", "meaning": "Con trai"},
            {"hanzi": "女儿", "pinyin": "nǚ ér", "meaning": "Con gái"}
        ]
    }
    is_valid, errors = validator.validate_batch(four_word_batch)
    assert is_valid is False
    assert any("Số lượng từ không đúng chuẩn" in e for e in errors)


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_negative_context_history_deduplication(pipeline_name, validator):
    """Batches colliding with history topic or having >=2 overlapping words must fail."""
    history = {
        "recent_topics": ["Đồ Ăn & Thức Uống", "Giao Thông"],
        "past_batches": [
            {"id": "2", "topic": "Đồ Ăn & Thức Uống", "words": ["苹果", "米饭", "面条", "喝水", "牛奶"]}
        ]
    }

    # 1. Topic Collision
    dup_topic_candidate = {
        "id": "204",
        "topic": "Đồ Ăn & Thức Uống",
        "level": "HSK 1",
        "words": [
            {"hanzi": "包子", "pinyin": "bāo zi", "meaning": "Bánh bao"},
            {"hanzi": "饺子", "pinyin": "jiǎo zi", "meaning": "Sủi cảo"},
            {"hanzi": "鸡蛋", "pinyin": "jī dàn", "meaning": "Trứng gà"},
            {"hanzi": "面包", "pinyin": "miàn bāo", "meaning": "Bánh mì"},
            {"hanzi": "豆腐", "pinyin": "dòu fu", "meaning": "Đậu phụ"}
        ]
    }
    is_valid, errors = validator.validate_batch(dup_topic_candidate, history=history)
    assert is_valid is False
    assert any("trùng lặp với chủ đề" in e for e in errors)

    # 2. Overlap >= 2 Words Collision
    overlap_candidate = {
        "id": "205",
        "topic": "Bữa Ăn Sáng",
        "level": "HSK 1",
        "words": [
            {"hanzi": "苹果", "pinyin": "píng guǒ", "meaning": "Quả táo"},
            {"hanzi": "米饭", "pinyin": "mǐ fàn", "meaning": "Cơm trắng"},
            {"hanzi": "鸡蛋", "pinyin": "jī dàn", "meaning": "Trứng gà"},
            {"hanzi": "面包", "pinyin": "miàn bāo", "meaning": "Bánh mì"},
            {"hanzi": "豆腐", "pinyin": "dòu fu", "meaning": "Đậu phụ"}
        ]
    }
    is_valid, errors = validator.validate_batch(overlap_candidate, history=history)
    assert is_valid is False
    assert any("Trùng lặp cặp" in e for e in errors)

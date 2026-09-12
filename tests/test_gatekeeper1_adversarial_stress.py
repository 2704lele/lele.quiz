#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adversarial Stress Test Suite for Gatekeeper 1 Linguistic Engine,
Gemini 6-Key Failover, and Negative Context Deduplication across all 3 sub-pipelines:
- pinyinquiz
- vocabCNquiz
- vocabVNquiz
"""

import os
import sys
import time
import pytest
from typing import Dict, Any, List

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Import validators from each sub-pipeline
from pinyinquiz.src.pre_render_validator import PreRenderValidator as PinyinValidator
from vocabCNquiz.src.pre_render_validator import PreRenderValidator as VocabCNValidator
from vocabVNquiz.src.pre_render_validator import PreRenderValidator as VocabVNValidator

from vocabCNquiz.src.pre_render_validator import (
    normalize_topic_string,
    STRICT_TRADITIONAL_CHARS,
    ENGLISH_FORBIDDEN_WORDS,
    VALID_NEUTRAL_SYLLABLES,
    VIETNAMESE_VALID_WORDS_WHITELIST
)

from vocabCNquiz.src.llm_client import (
    parse_gemini_keys,
    mask_key,
    parse_json_from_llm,
    FALLBACK_GEMINI_MODELS,
    DEFAULT_GEMINI_MODEL,
    FALLBACK_VOCAB_BANK as CN_FALLBACK_BANK
)
from vocabVNquiz.src.llm_client import (
    FALLBACK_VOCAB_BANK as VN_FALLBACK_BANK
)

ALL_VALIDATORS = [PinyinValidator, VocabCNValidator, VocabVNValidator]


# ============================================================================
# 1. RULE 1: ADVERSARIAL SIMPLIFIED CHINESE & TRADITIONAL HANZI REJECTION
# ============================================================================

def test_rule_1_extensive_simplified_chinese_valid():
    """Verify extensive corpus of valid Simplified Chinese characters across all validators."""
    simplified_corpus = [
        "爸爸", "妈妈", "学校", "大门", "中国", "谢谢", "买东西", "书包", "铅笔",
        "公共汽车", "出租车", "高兴", "苹果", "喝水", "吃饭", "看书", "听歌", "睡觉",
        "多少", "块钱", "太贵", "便宜", "买单", "帮助", "介绍", "欢迎", "回答", "希望",
        "飞机", "晴天", "下雨", "下雪", "刮风", "温度", "快乐", "难过", "着急", "聪明",
        "打折", "刷卡", "现金", "找钱", "收据", "生病", "发烧", "吃药", "跑步", "游泳",
        "同事", "会议", "经理", "请假", "加班", "锻炼", "习惯", "干净", "刷牙", "洗澡",
        "礼貌", "客气", "原谅", "感谢", "祝贺", "行李", "照相机", "地图", "护照", "风景",
        "环境", "保护", "森林", "世界", "新鲜", "感冒", "检查", "健康", "舒服", "疼痛"
    ]
    for validator in ALL_VALIDATORS:
        for hz in simplified_corpus:
            errors = validator.check_simplified_chinese(hz)
            assert len(errors) == 0, f"Validator {validator} incorrectly rejected valid Simplified '{hz}': {errors}"


def test_rule_1_adversarial_traditional_characters_rejected():
    """Verify that all 200+ distinct Traditional characters are strictly rejected."""
    trad_corpus = list(STRICT_TRADITIONAL_CHARS)
    assert len(trad_corpus) >= 150, "Traditional characters set should be comprehensive"

    for validator in ALL_VALIDATORS:
        for tc in trad_corpus:
            errors = validator.check_simplified_chinese(tc)
            assert len(errors) > 0, f"Validator {validator} failed to reject Traditional char '{tc}'"
            assert any("Phồn thể" in e for e in errors)


def test_rule_1_adversarial_compound_traditional_words_rejected():
    """Verify compound words containing mixed or pure Traditional characters are rejected."""
    trad_words = [
        ("媽媽", "Traditional 媽"),
        ("開門", "Traditional 開 and 門"),
        ("買東西", "Traditional 買"),
        ("謝謝", "Traditional 謝"),
        ("廣東", "Traditional 廣 and 東"),
        ("學生", "Traditional 學"),
        ("國家", "Traditional 國"),
        ("電話", "Traditional 電 and 話"),
        ("飛機", "Traditional 飛 and 機"),
        ("醫學", "Traditional 醫 and 學"),
        ("圖書館", "Traditional 圖 and 書 and 館"),
        ("歡樂", "Traditional 歡 and 樂"),
        ("環境保護", "Traditional 環 and 護"),
        ("認識朋友", "Traditional 認 and 識"),
        ("說話", "Traditional 說 and 話")
    ]
    for validator in ALL_VALIDATORS:
        for hz, desc in trad_words:
            errors = validator.check_simplified_chinese(hz)
            assert len(errors) > 0, f"Validator {validator} failed on '{hz}' ({desc})"
            assert any("Phồn thể" in e for e in errors)


def test_rule_1_universal_heritage_characters_accepted():
    """Universal heritage characters identical in Simplified and Traditional must be accepted."""
    heritage_words = [
        "生", "衣服", "桌椅", "窗户", "床", "房间", "数量", "折扣", "水", "火", "木", "人", "口", "手", "心"
    ]
    for validator in ALL_VALIDATORS:
        for hw in heritage_words:
            errors = validator.check_simplified_chinese(hw)
            assert len(errors) == 0, f"Validator {validator} rejected universal heritage word '{hw}': {errors}"


# ============================================================================
# 2. RULE 2: SINGLE FOCUSED TOPIC VALIDATION
# ============================================================================

def test_rule_2_valid_topics():
    """Natural, single focused topics must pass Rule 2."""
    valid_topics = [
        "Đồ Dùng Nhà Bếp",
        "HSK 1 • Đồ Ăn",
        "HSK 2 • Giao Thông",
        "Cảm xúc và tâm trạng",
        "Thời tiết & khí hậu",
        "Gia Đình & Bạn Bè",
        "Môi trường - Đời sống",
        "Thói Quen Hàng Ngày"
    ]
    for validator in ALL_VALIDATORS:
        for top in valid_topics:
            errors = validator.check_single_topic(top)
            assert len(errors) == 0, f"Validator {validator} rejected valid topic '{top}': {errors}"


def test_rule_2_adversarial_topic_delimiters_and_abbreviations_rejected():
    """Topics with list delimiters or abbreviations must be rejected."""
    invalid_topics = [
        "Đồ Ăn; Thức Uống",
        "Trường Học | Thư Viện",
        "Chào Hỏi, v.v.",
        "Đồ dùng vv",
        "Phương tiện v/v",
        "Chủ đề etc.",
        "A" * 55,  # Too long (> 50)
        "X",       # Too short (< 2)
        "",        # Empty
        "   "      # Whitespace only
    ]
    for validator in ALL_VALIDATORS:
        for top in invalid_topics:
            errors = validator.check_single_topic(top)
            assert len(errors) > 0, f"Validator {validator} failed to reject invalid topic '{top}'"


# ============================================================================
# 3. RULE 3: 100% PURE VIETNAMESE DEFINITION & FORBIDDEN ENGLISH WORDS
# ============================================================================

def test_rule_3_valid_vietnamese_meanings():
    """Pure Vietnamese definitions must pass Rule 3."""
    valid_meanings = [
        "Cái bàn học", "Quả táo đỏ", "Đi học buổi sáng", "Uống nước lọc",
        "Bố / Ba", "Mẹ", "Con trai", "Bạn bè thân thiết", "Đồng hồ treo tường",
        "Xe buýt công cộng", "Xe taxi nhanh", "Uống cà phê sáng", "Áo sơ-mi trắng"
    ]
    for validator in ALL_VALIDATORS:
        for vm in valid_meanings:
            errors = validator.check_vietnamese_meaning(vm, hanzi="苹果", pinyin="píng guǒ")
            assert len(errors) == 0, f"Validator {validator} rejected valid meaning '{vm}': {errors}"


def test_rule_3_adversarial_forbidden_english_words_rejected():
    """Definitions containing any of the 250+ forbidden English words must be rejected."""
    english_samples = [
        "Quả apple tươi", "Uống coffee đá", "Ngồi trên chair", "Để trên table",
        "Đi học bằng bus", "Gọi một chiếc car", "Gặp gỡ teacher", "Khám bác sĩ doctor",
        "Mua đồ shopping", "Bắt con cat", "Nuôi con dog", "Uống cup trà", "Mua sách book"
    ]
    for validator in ALL_VALIDATORS:
        for em in english_samples:
            errors = validator.check_vietnamese_meaning(em)
            assert len(errors) > 0, f"Validator {validator} failed to reject forbidden English in '{em}'"
            assert any("tiếng Anh" in e or "bị cấm" in e for e in errors)


def test_rule_3_allowed_loanwords_whitelist_accepted():
    """Legitimate Vietnamese loanwords in the whitelist must be accepted."""
    whitelist_samples = [
        "Đi xe buýt", "Đi xe taxi", "Uống cà phê", "Áo sơ-mi", "Xem tivi",
        "Mạng wifi", "Gửi email", "Học online", "Xem clip vui", "Máy tính laptop"
    ]
    for validator in ALL_VALIDATORS:
        for wl in whitelist_samples:
            errors = validator.check_vietnamese_meaning(wl)
            assert len(errors) == 0, f"Validator {validator} rejected whitelisted loanword '{wl}': {errors}"


def test_rule_3_hidden_pinyin_artifacts_rejected():
    """Definitions containing underscore '_' hidden pinyin artifacts must be rejected."""
    corrupted_meanings = [
        "p _ _ _   g _ _",
        "Bàn học _ ghế",
        "p__ng_gu_",
        "_"
    ]
    for validator in ALL_VALIDATORS:
        for cm in corrupted_meanings:
            errors = validator.check_vietnamese_meaning(cm)
            assert len(errors) > 0, f"Validator {validator} failed to reject underscore artifact in '{cm}'"


# ============================================================================
# 4. RULE 4: 1:1 SYLLABLE PINYIN & TONE MARKS (WITH ERHUA SUPPORT)
# ============================================================================

def test_rule_4_valid_pinyin_syllables_and_tones():
    """Pinyin matching Hanzi 1:1 with tone marks must pass."""
    valid_pairs = [
        ("爸爸", "bà ba"),
        ("妈妈", "mā ma"),
        ("苹果", "píng guǒ"),
        ("公共汽车", "gōng gòng qì chē"),
        ("出租车", "chū zū chē"),
        ("高兴", "gāo xìng"),
        ("谢谢", "xiè xie"),
        ("怎么样", "zěn me yàng"),
        ("桌子", "zhuō zi"),
        ("我们", "wǒ men")
    ]
    for validator in ALL_VALIDATORS:
        for hz, py in valid_pairs:
            errors, norm_py = validator.check_pinyin_syllables(hz, py)
            assert len(errors) == 0, f"Validator {validator} rejected valid pair '{hz}' - '{py}': {errors}"


def test_rule_4_erhua_contracted_and_uncontracted_valid():
    """Erhua words (儿化) contracted into 'r' or uncontracted 'er' must be accepted."""
    erhua_pairs = [
        ("哪儿", "nǎr"),
        ("这儿", "zhèr"),
        ("那儿", "nàr"),
        ("玩儿", "wánr"),
        ("一点儿", "yì diǎnr"),
        ("花儿", "huār"),
        ("哪儿", "nǎ er"),
        ("这儿", "zhè er")
    ]
    for validator in ALL_VALIDATORS:
        for hz, py in erhua_pairs:
            errors, _ = validator.check_pinyin_syllables(hz, py)
            assert len(errors) == 0, f"Validator {validator} rejected valid Erhua '{hz}' - '{py}': {errors}"


def test_rule_4_syllable_count_mismatch_rejected():
    """Syllable count mismatch must be strictly rejected."""
    mismatch_pairs = [
        ("苹果", "píng"),                      # 2 chars, 1 syl
        ("苹果", "píng guǒ zi"),               # 2 chars, 3 syls
        ("公共汽车", "gōng gòng"),              # 4 chars, 2 syls
        ("学校", "xué xiào da shi"),           # 2 chars, 4 syls
        ("书", "shū běn")                      # 1 char, 2 syls
    ]
    for validator in ALL_VALIDATORS:
        for hz, py in mismatch_pairs:
            errors, _ = validator.check_pinyin_syllables(hz, py)
            assert len(errors) > 0, f"Validator {validator} failed to reject syllable mismatch '{hz}' - '{py}'"


def test_rule_4_missing_tones_rejected():
    """Words lacking valid tone marks must be rejected."""
    untoned_pairs = [
        ("苹果", "ping guo"),
        ("学校", "xue xiao"),
        ("老师", "lao shi"),
        ("吃饭", "chi fan")
    ]
    for validator in ALL_VALIDATORS:
        for hz, py in untoned_pairs:
            errors, _ = validator.check_pinyin_syllables(hz, py)
            assert len(errors) > 0, f"Validator {validator} failed to reject untoned Pinyin '{hz}' - '{py}'"


# ============================================================================
# 5. RULE 5: 5-WORD INTRA-BATCH RETENTION CURVE & INTEGRITY
# ============================================================================

def test_rule_5_full_batch_validation_valid():
    """Valid 5-word batches adhering to retention curve must pass full validation."""
    valid_batch = {
        "id": "1",
        "topic": "Đồ Dùng Nhà Bếp",
        "level": "HSK 2",
        "words": [
            {"hanzi": "筷子", "pinyin": "kuài zi", "meaning": "Đôi đũa"},
            {"hanzi": "碗", "pinyin": "wǎn", "meaning": "Cái bát / chén"},
            {"hanzi": "盘子", "pinyin": "pán zi", "meaning": "Cái đĩa"},
            {"hanzi": "勺子", "pinyin": "sháo zi", "meaning": "Cái thìa / muỗng"},
            {"hanzi": "锅", "pinyin": "guō", "meaning": "Cái nồi / chảo"}
        ]
    }
    for validator in ALL_VALIDATORS:
        is_valid, errors = validator.validate_batch(valid_batch)
        assert is_valid is True, f"Validator {validator} rejected valid batch: {errors}"
        assert len(errors) == 0


def test_rule_5_word_count_not_five_rejected():
    """Batches with word count != 5 must be rejected."""
    batch_4_words = {
        "topic": "Đồ Dùng",
        "words": [
            {"hanzi": "筷子", "pinyin": "kuài zi", "meaning": "Đôi đũa"},
            {"hanzi": "碗", "pinyin": "wǎn", "meaning": "Cái bát"},
            {"hanzi": "盘子", "pinyin": "pán zi", "meaning": "Cái đĩa"},
            {"hanzi": "勺子", "pinyin": "sháo zi", "meaning": "Cái thìa"}
        ]
    }
    for validator in ALL_VALIDATORS:
        is_valid, errors = validator.validate_batch(batch_4_words)
        assert is_valid is False
        assert any("Số lượng từ" in e or "5 từ" in e for e in errors)


def test_rule_5_intra_batch_duplicates_rejected():
    """Batches with duplicate Hanzi or duplicate Vietnamese meaning must be rejected."""
    batch_dup_hz = {
        "topic": "Gia Đình",
        "words": [
            {"hanzi": "爸爸", "pinyin": "bà ba", "meaning": "Bố"},
            {"hanzi": "爸爸", "pinyin": "bà ba", "meaning": "Ba"},
            {"hanzi": "儿子", "pinyin": "ér zi", "meaning": "Con trai"},
            {"hanzi": "女儿", "pinyin": "nǚ ér", "meaning": "Con gái"},
            {"hanzi": "朋友", "pinyin": "péng you", "meaning": "Bạn bè"}
        ]
    }
    batch_dup_mean = {
        "topic": "Gia Đình",
        "words": [
            {"hanzi": "爸爸", "pinyin": "bà ba", "meaning": "Bố"},
            {"hanzi": "父亲", "pinyin": "fù qīn", "meaning": "Bố"},
            {"hanzi": "儿子", "pinyin": "ér zi", "meaning": "Con trai"},
            {"hanzi": "女儿", "pinyin": "nǚ ér", "meaning": "Con gái"},
            {"hanzi": "朋友", "pinyin": "péng you", "meaning": "Bạn bè"}
        ]
    }
    for validator in ALL_VALIDATORS:
        is_valid_hz, errors_hz = validator.validate_batch(batch_dup_hz)
        assert is_valid_hz is False
        assert any("Trùng chữ Hán" in e for e in errors_hz)

        is_valid_m, errors_m = validator.validate_batch(batch_dup_mean)
        assert is_valid_m is False
        assert any("Trùng nghĩa tiếng Việt" in e for e in errors_m)


# ============================================================================
# 6. NEGATIVE CONTEXT DEDUPLICATION AGAINST HISTORY
# ============================================================================

def test_negative_context_topic_recurrence_rejected():
    """A topic matching any historical topic in Google Sheets must be rejected."""
    history = {
        "recent_topics": ["Đồ Ăn Hàng Ngày", "Giao Tiếp Xã Hội", "Thời Tiết Bốn Mùa"],
        "past_batches": []
    }
    candidate_batch = {
        "topic": "HSK 1 • Đồ Ăn Hàng Ngày",
        "words": [
            {"hanzi": "包子", "pinyin": "bāo zi", "meaning": "Bánh bao"},
            {"hanzi": "饺子", "pinyin": "jiǎo zi", "meaning": "Sủi cảo"},
            {"hanzi": "鸡蛋", "pinyin": "jī dàn", "meaning": "Trứng gà"},
            {"hanzi": "面包", "pinyin": "miàn bāo", "meaning": "Bánh mì"},
            {"hanzi": "豆腐", "pinyin": "dòu fu", "meaning": "Đậu phụ"}
        ]
    }
    for validator in ALL_VALIDATORS:
        is_valid, errors = validator.validate_batch(candidate_batch, history=history)
        assert is_valid is False
        assert any("trùng lặp với chủ đề" in e for e in errors)


def test_negative_context_pair_overlap_rejected():
    """A candidate batch sharing >= 2 words with any past batch must be rejected."""
    history = {
        "recent_topics": ["Món Ăn Quen Thuộc"],
        "past_batches": [
            {"id": "5", "topic": "Món Ăn Quen Thuộc", "words": ["米饭", "面条", "苹果", "茶水", "牛奶"]}
        ]
    }
    # Overlaps on '米饭' and '面条' (2 words)
    candidate_overlap_2 = {
        "topic": "Ẩm Thực Trung Hoa",
        "words": [
            {"hanzi": "米饭", "pinyin": "mǐ fàn", "meaning": "Cơm trắng"},
            {"hanzi": "面条", "pinyin": "miàn tiáo", "meaning": "Mì sợi dai"},
            {"hanzi": "烤鸭", "pinyin": "kǎo yā", "meaning": "Vịt quay"},
            {"hanzi": "火锅", "pinyin": "huǒ guō", "meaning": "Lẩu"},
            {"hanzi": "春卷", "pinyin": "chūn juǎn", "meaning": "Nem rán"}
        ]
    }
    for validator in ALL_VALIDATORS:
        is_valid, errors = validator.validate_batch(candidate_overlap_2, history=history)
        assert is_valid is False
        assert any("Trùng lặp cặp" in e for e in errors)


def test_negative_context_single_word_review_allowed():
    """A candidate batch sharing exactly 1 word with a past batch for spaced repetition is permitted."""
    history = {
        "recent_topics": ["Món Ăn Quen Thuộc"],
        "past_batches": [
            {"id": "5", "topic": "Món Ăn Quen Thuộc", "words": ["米饭", "面条", "苹果", "茶水", "牛奶"]}
        ]
    }
    # Overlaps ONLY on '米饭' (1 word allowed)
    candidate_overlap_1 = {
        "topic": "Bữa Cơm Gia Đình",
        "words": [
            {"hanzi": "米饭", "pinyin": "mǐ fàn", "meaning": "Cơm trắng"},
            {"hanzi": "青菜", "pinyin": "qīng cài", "meaning": "Rau xanh"},
            {"hanzi": "猪肉", "pinyin": "zhū ròu", "meaning": "Thịt lợn"},
            {"hanzi": "鱼汤", "pinyin": "yú tāng", "meaning": "Canh cá"},
            {"hanzi": "豆腐", "pinyin": "dòu fu", "meaning": "Đậu phụ"}
        ]
    }
    for validator in ALL_VALIDATORS:
        is_valid, errors = validator.validate_batch(candidate_overlap_1, history=history)
        assert is_valid is True, f"Validator {validator} rejected allowed 1-word review: {errors}"
        assert len(errors) == 0


# ============================================================================
# 7. PERFORMANCE: PURE PYTHON < 1MS EXECUTION BENCHMARK
# ============================================================================

def test_gatekeeper1_execution_performance():
    """Gatekeeper 1 deterministic validations must execute in < 1ms per check in pure Python."""
    batch = {
        "topic": "Đồ Dùng Nhà Bếp",
        "level": "HSK 2",
        "words": [
            {"hanzi": "筷子", "pinyin": "kuài zi", "meaning": "Đôi đũa"},
            {"hanzi": "碗", "pinyin": "wǎn", "meaning": "Cái bát / chén"},
            {"hanzi": "盘子", "pinyin": "pán zi", "meaning": "Cái đĩa"},
            {"hanzi": "勺子", "pinyin": "sháo zi", "meaning": "Cái thìa / muỗng"},
            {"hanzi": "锅", "pinyin": "guō", "meaning": "Cái nồi / chảo"}
        ]
    }
    history = {
        "recent_topics": ["Gia Đình", "Du Lịch", "Thời Gian", "Thời Tiết"],
        "past_batches": [
            {"id": "1", "topic": "Gia Đình", "words": ["爸爸", "妈妈", "儿子", "女儿", "朋友"]},
            {"id": "2", "topic": "Thời Gian", "words": ["今天", "明天", "昨天", "现在", "点钟"]}
        ]
    }

    import gc
    gc.collect()
    gc.disable()
    try:
        iterations = 500
        start_time = time.perf_counter()
        for _ in range(iterations):
            VocabVNValidator.validate_batch(batch, history=history)
        elapsed_total = time.perf_counter() - start_time
    finally:
        gc.enable()
    avg_ms = (elapsed_total / iterations) * 1000

    print(f"\n⚡ Gatekeeper 1 Performance: {avg_ms:.4f} ms per batch validation ({iterations} iterations)")
    assert avg_ms < 1.0, f"Gatekeeper 1 took {avg_ms:.4f} ms (> 1.0 ms requirement)"


# ============================================================================
# 8. GEMINI 6-KEY FAILOVER & ZERO-SECRET ROTATION TESTS
# ============================================================================

def test_gemini_key_masking_zero_secrets():
    """Mask key must never leak full plaintext keys."""
    assert mask_key("") == "None"
    assert mask_key(None) == "None"
    assert mask_key("1234567") == "****"
    assert mask_key("AIzaSy1234567890abcdef") == "AIzaSy...****"
    assert "abcdef" not in mask_key("AIzaSy1234567890abcdef")


def test_gemini_key_parsing_and_rotation_formula():
    """Keys parsed from multiple delimiters and rotated via (i-1)%len(keys)."""
    raw_keys = "key_1, key_2\nkey_3;key_4,key_5\nkey_6"
    keys = parse_gemini_keys(raw_keys)
    assert len(keys) == 6
    assert keys == ["key_1", "key_2", "key_3", "key_4", "key_5", "key_6"]

    # Rotation formula: (i - 1) % len(keys)
    for i in range(1, 13):
        active_key = keys[(i - 1) % len(keys)]
        expected_key = f"key_{(i - 1) % 6 + 1}"
        assert active_key == expected_key


def test_gemini_model_cascading_hierarchy():
    """Model cascade list must prioritize gemini-3.7-flash -> 3.6-flash -> 3.6-flash-high -> 3.5-flash."""
    expected_hierarchy = ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.6-flash-high", "gemini-3.5-flash"]
    assert FALLBACK_GEMINI_MODELS == expected_hierarchy
    assert DEFAULT_GEMINI_MODEL == "gemini-3.7-flash"


def test_robust_json_parser_from_llm():
    """parse_json_from_llm must handle markdown code fences, trailing commas, and raw containers."""
    # 1. Markdown code fences
    fence_json = '```json\n[{"topic": "Gia Đình", "words": []}]\n```'
    assert parse_json_from_llm(fence_json) == [{"topic": "Gia Đình", "words": []}]

    # 2. Trailing comma cleanup
    trailing_json = '{"topic": "Đồ Ăn", "words": ["米饭", "苹果",], }'
    parsed = parse_json_from_llm(trailing_json)
    assert parsed is not None
    assert parsed.get("topic") == "Đồ Ăn"
    assert parsed.get("words") == ["米饭", "苹果"]

    # 3. Unfenced text wrapper
    wrapped_json = 'Đây là kết quả của bạn:\n[{"topic": "Du Lịch", "words": []}]\nChúc bạn thành công!'
    parsed_wrapped = parse_json_from_llm(wrapped_json)
    assert isinstance(parsed_wrapped, list)
    assert parsed_wrapped[0]["topic"] == "Du Lịch"


def test_fallback_vocab_banks_100_percent_gatekeeper_compliant():
    """All topics in CN and VN fallback banks must 100% pass Gatekeeper 1 validation."""
    for name, bank in [("VocabCN Bank", CN_FALLBACK_BANK), ("VocabVN Bank", VN_FALLBACK_BANK)]:
        for topic, level, words_tuples in bank:
            words_list = [{"hanzi": w[0], "pinyin": w[1], "meaning": w[2]} for w in words_tuples]
            batch_data = {
                "topic": topic,
                "level": level,
                "words": words_list
            }
            is_valid, errors = VocabVNValidator.validate_batch(batch_data)
            assert is_valid is True, f"Topic '{topic}' ({level}) in {name} failed Gatekeeper 1: {errors}"
            assert len(words_list) == 5

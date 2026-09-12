#!/usr/bin/env python3
"""
Comprehensive Test Suite for Gatekeeper 1 & Negative Context Validation (Milestone 3 / Requirement R3).
Tests all 5 Linguistic Rules and Negative Context Deduplication against Google Sheets tab 'vocabCN'.
"""

import os
import sys
import pytest
from typing import Dict, Any, List

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from src.pre_render_validator import (
    PreRenderValidator,
    normalize_topic_string,
    STRICT_TRADITIONAL_CHARS,
    ENGLISH_FORBIDDEN_WORDS,
    VALID_NEUTRAL_SYLLABLES
)
from src.gsheet_manager import GSheetManager


# ============================================================================
# 1. RULE 1: 100% SIMPLIFIED CHINESE (TRADITIONAL HANZI REJECTION)
# ============================================================================

def test_rule_1_simplified_chinese_valid():
    """Valid Simplified Chinese characters must pass Rule 1."""
    valid_words = [
        "妈妈", "爸爸", "学校", "大门", "中国", "谢谢", "买东西",
        "书包", "铅笔", "苹果", "公共汽车", "出租车", "高兴"
    ]
    for hz in valid_words:
        errors = PreRenderValidator.check_simplified_chinese(hz)
        assert len(errors) == 0, f"Expected '{hz}' to pass Simplified Chinese check, got errors: {errors}"


def test_rule_1_traditional_chinese_single_char_rejected():
    """Traditional Chinese single characters (國, 學, 門, 媽, etc.) must be rejected."""
    trad_chars = ["國", "學", "門", "媽", "體", "書", "買", "點", "開", "關", "車", "愛", "話"]
    for tc in trad_chars:
        errors = PreRenderValidator.check_simplified_chinese(tc)
        assert len(errors) > 0, f"Expected Traditional char '{tc}' to be rejected"
        assert any("Phồn thể" in err for err in errors), f"Error message should mention 'Phồn thể': {errors}"


def test_rule_1_traditional_chinese_multi_char_words_rejected():
    """Words containing Traditional Chinese characters must be rejected."""
    test_cases = [
        ("媽媽", "Traditional 媽"),
        ("開門", "Traditional 開 and 門"),
        ("買東西", "Traditional 買"),
        ("謝謝", "Traditional 謝"),
        ("廣東", "Traditional 廣 and 東"),
        ("學生", "Traditional 學"),
        ("國家", "Traditional 國"),
        ("電話", "Traditional 電 and 話"),
        ("飛機", "Traditional 飛 and 機")
    ]
    for hz, desc in test_cases:
        errors = PreRenderValidator.check_simplified_chinese(hz)
        assert len(errors) > 0, f"Expected '{hz}' ({desc}) to be rejected"
        assert any("Phồn thể" in err for err in errors)


# ============================================================================
# 2. RULE 2: SINGLE FOCUSED TOPIC VALIDATION
# ============================================================================

def test_rule_2_single_topic_valid():
    """Valid natural single topics must pass Rule 2."""
    valid_topics = [
        "Đồ Dùng Nhà Bếp",
        "HSK 1 • Đồ Ăn",
        "HSK 2 • Giao Thông",
        "Cảm xúc và tâm trạng",
        "Thời tiết bốn mùa",
        "Gia Đình & Bạn Bè"
    ]
    for top in valid_topics:
        errors = PreRenderValidator.check_single_topic(top)
        assert len(errors) == 0, f"Expected topic '{top}' to pass, got: {errors}"


def test_rule_2_topic_delimiters_rejected():
    """Topics with list delimiters (; or |) must be rejected."""
    invalid_topics = [
        "Đồ Ăn; Thức Uống",
        "Gia Đình | Nhà Trường",
        "Mua Sắm; Quần Áo; Giày Dép",
        "Thời Tiết | Khí Hậu"
    ]
    for top in invalid_topics:
        errors = PreRenderValidator.check_single_topic(top)
        assert len(errors) > 0, f"Expected topic '{top}' to be rejected"
        assert any("phân tách danh sách" in err for err in errors)


def test_rule_2_topic_abbreviations_rejected():
    """Topics containing enumeration markers (etc, v.v., v/v) must be rejected."""
    invalid_topics = [
        "Đồ dùng học tập, v.v.",
        "Các loại hoa quả v/v",
        "Phương tiện giao thông etc.",
        "Đồ ăn vv"
    ]
    for top in invalid_topics:
        errors = PreRenderValidator.check_single_topic(top)
        assert len(errors) > 0, f"Expected topic '{top}' to be rejected"
        assert any("liệt kê" in err for err in errors)


def test_rule_2_topic_length_limits_rejected():
    """Empty, too short (<2 chars), or too long (>50 chars) topics must be rejected."""
    # Empty
    assert len(PreRenderValidator.check_single_topic("")) > 0
    assert len(PreRenderValidator.check_single_topic("   ")) > 0
    # Too short
    assert len(PreRenderValidator.check_single_topic("A")) > 0
    # Too long (> 50 chars)
    long_topic = "Chủ đề học tiếng Trung siêu cấp vô cùng dài vượt quá năm mươi ký tự cho phép"
    assert len(long_topic) > 50
    errors = PreRenderValidator.check_single_topic(long_topic)
    assert len(errors) > 0
    assert any("quá dài" in err for err in errors)


# ============================================================================
# 3. RULE 3: 100% VIETNAMESE DEFINITIONS (ZERO ENGLISH WORDS)
# ============================================================================

def test_rule_3_vietnamese_meaning_valid():
    """Valid Vietnamese definitions (including standard loanwords) must pass Rule 3."""
    valid_meanings = [
        "Bát / Chén",
        "Cái đĩa",
        "Cái thìa / Muỗng",
        "Xe buýt",
        "Cà phê",
        "Tivi",
        "Bố / Ba",
        "Mẹ",
        "Cặp sách",
        "Bút chì",
        "Uống nước hoa quả tươi"
    ]
    for mean in valid_meanings:
        errors = PreRenderValidator.check_vietnamese_meaning(mean, hanzi="碗", pinyin="wǎn")
        assert len(errors) == 0, f"Expected meaning '{mean}' to pass, got: {errors}"


def test_rule_3_forbidden_english_words_rejected():
    """Meanings containing forbidden English words must be rejected."""
    forbidden_samples = [
        ("Quả apple", "apple"),
        ("Cái chair", "chair"),
        ("Trường school", "school"),
        ("Xe car", "car"),
        ("Cái table", "table"),
        ("Uống milk", "milk"),
        ("Bác sĩ doctor", "doctor"),
        ("Cửa sổ window", "window"),
        ("Thầy teacher", "teacher"),
        ("Cái bookshelf", "bookshelf"),
        ("Con cat", "cat"),
        ("Con dog", "dog"),
        ("Mua đồ shopping", "shopping"),
        ("Đi taxi", "taxi")
    ]
    for mean, word in forbidden_samples:
        errors = PreRenderValidator.check_vietnamese_meaning(mean, hanzi="测试", pinyin="cè shì")
        assert len(errors) > 0, f"Expected meaning '{mean}' (containing '{word}') to be rejected"
        assert any("tiếng Anh" in err or "ngoại ngữ" in err for err in errors)


def test_rule_3_meaning_with_underscores_rejected():
    """Meanings with hidden pinyin underscore artifacts must be rejected."""
    corrupt_meanings = [
        "c_i b_t",
        "b_n t_i",
        "____",
        "Cái đĩa _ đĩa ăn"
    ]
    for mean in corrupt_meanings:
        errors = PreRenderValidator.check_vietnamese_meaning(mean, hanzi="碗", pinyin="wǎn")
        assert len(errors) > 0, f"Expected meaning '{mean}' with underscores to be rejected"
        assert any("gạch dưới" in err for err in errors)


def test_rule_3_meaning_matching_pinyin_or_hanzi_rejected():
    """Meanings that mistakenly copy Pinyin or Hanzi must be rejected."""
    assert len(PreRenderValidator.check_vietnamese_meaning("wǎn", hanzi="碗", pinyin="wǎn")) > 0
    assert len(PreRenderValidator.check_vietnamese_meaning("碗", hanzi="碗", pinyin="wǎn")) > 0


# ============================================================================
# 4. RULE 4: 1:1 SYLLABLE PINYIN WITH VALID TONE MARKS
# ============================================================================

def test_rule_4_pinyin_syllables_match_valid():
    """Pinyin with 1:1 syllable count and tone marks must pass."""
    test_cases = [
        ("碗", "wǎn"),
        ("盘子", "pán zi"),
        ("公共汽车", "gōng gòng qì chē"),
        ("妈妈", "mā ma"),
        ("爸爸", "bà ba"),
        ("桌子", "zhuō zi"),
        ("我们", "wǒ men"),
        ("怎么样", "zěn me yàng"),
        ("打折", "dǎ zhé")
    ]
    for hz, py in test_cases:
        errors, norm_py = PreRenderValidator.check_pinyin_syllables(hz, py)
        assert len(errors) == 0, f"Expected '{hz}' ({py}) to pass pinyin check, got errors: {errors}"
        assert norm_py != ""


def test_rule_4_pinyin_erhua_valid():
    """Erhua words ending with 儿 must be accepted with 1-syllable contraction or 2-syllable form."""
    erhua_cases = [
        ("哪儿", "nǎr"),
        ("哪儿", "nǎ er"),
        ("这儿", "zhèr"),
        ("那儿", "nàr"),
        ("玩儿", "wánr"),
        ("花儿", "huār"),
        ("一点儿", "yì diǎnr")
    ]
    for hz, py in erhua_cases:
        errors, norm_py = PreRenderValidator.check_pinyin_syllables(hz, py)
        assert len(errors) == 0, f"Expected Erhua '{hz}' ({py}) to pass, got errors: {errors}"


def test_rule_4_pinyin_erhua_corrupted_rejected():
    """Corrupted Erhua pinyin (e.g. '哪儿' with 'nǎr zi') must be strictly rejected."""
    corrupted_cases = [
        ("哪儿", "nǎr zi"),
        ("这儿", "zhè er zi"),
        ("玩儿", "wán")
    ]
    for hz, py in corrupted_cases:
        errors, _ = PreRenderValidator.check_pinyin_syllables(hz, py)
        assert len(errors) > 0, f"Expected corrupted Erhua '{hz}' ({py}) to be rejected"


def test_rule_4_standard_hsk_neutral_tones():
    """Standard HSK words with neutral tones (多少, 便宜, 聪明, 胡萝卜, 客气) must pass tone validation."""
    neutral_cases = [
        ("多少", "duō shao"),
        ("便宜", "pián yi"),
        ("聪明", "cōng ming"),
        ("胡萝卜", "hú luó bo"),
        ("客气", "kè qi"),
        ("事情", "shì qing"),
        ("姑娘", "gū niang"),
        ("告诉", "gào su"),
        ("耳朵", "ěr duo"),
        ("眼睛", "yǎn jing")
    ]
    for hz, py in neutral_cases:
        errors, norm_py = PreRenderValidator.check_pinyin_syllables(hz, py)
        assert len(errors) == 0, f"Expected neutral tone word '{hz}' ({py}) to pass, got errors: {errors}"


def test_rule_4_pinyin_syllable_count_mismatch_rejected():
    """Mismatch between Hanzi char count and Pinyin syllable count must be rejected."""
    mismatches = [
        ("碗", "wǎn zi", 1, 2),
        ("筷子", "kuài", 2, 1),
        ("公共汽车", "gōng gòng qì", 4, 3),
        ("苹果", "píng guǒ zi", 2, 3),
        ("书包", "shū", 2, 1)
    ]
    for hz, py, h_count, p_count in mismatches:
        errors, _ = PreRenderValidator.check_pinyin_syllables(hz, py)
        assert len(errors) > 0, f"Expected syllable mismatch for '{hz}' ({py}) [{h_count} vs {p_count}]"
        assert any("không khớp 1:1" in err for err in errors)


def test_rule_4_pinyin_missing_tone_rejected():
    """Pinyin missing valid tone marks on non-neutral syllables must be rejected."""
    missing_tones = [
        ("碗", "wan"),
        ("苹果", "ping guo"),
        ("学校", "xue xiao"),
        ("盘子", "pan zi"),  # 'pan' has no tone
        ("电脑", "dian nao")
    ]
    for hz, py in missing_tones:
        errors, _ = PreRenderValidator.check_pinyin_syllables(hz, py)
        assert len(errors) > 0, f"Expected missing tone rejection for '{hz}' ({py})"
        assert any("thanh điệu" in err for err in errors)


# ============================================================================
# 5. RULE 5: 5-WORD RETENTION CURVE & INTRA-BATCH DUPLICATES
# ============================================================================

def test_rule_5_word_count_rejected():
    """Batch with != 5 words must be rejected."""
    # 4 words
    batch_4 = {
        "topic": "Đồ Ăn",
        "words": [
            {"hanzi": "米饭", "pinyin": "mǐ fàn", "meaning": "Cơm"},
            {"hanzi": "面条", "pinyin": "miàn tiáo", "meaning": "Mì sợi"},
            {"hanzi": "苹果", "pinyin": "píng guǒ", "meaning": "Quả táo"},
            {"hanzi": "面包", "pinyin": "miàn bāo", "meaning": "Bánh mì"}
        ]
    }
    is_valid, errors = PreRenderValidator.validate_batch(batch_4)
    assert not is_valid
    assert any("5 từ" in err for err in errors)

    # 6 words
    batch_6 = {
        "topic": "Đồ Ăn",
        "words": batch_4["words"] + [
            {"hanzi": "鸡蛋", "pinyin": "jī dàn", "meaning": "Trứng gà"},
            {"hanzi": "包子", "pinyin": "bāo zi", "meaning": "Bánh bao"}
        ]
    }
    is_valid, errors = PreRenderValidator.validate_batch(batch_6)
    assert not is_valid
    assert any("5 từ" in err for err in errors)


def test_rule_5_intra_batch_duplicate_hanzi_rejected():
    """Batch containing duplicate Hanzi must be rejected."""
    batch_dup_hz = {
        "topic": "Đồ Dùng Nhà Bếp",
        "words": [
            {"hanzi": "碗", "pinyin": "wǎn", "meaning": "Bát / Chén"},
            {"hanzi": "碗", "pinyin": "wǎn", "meaning": "Cái bát nhỏ"},
            {"hanzi": "盘子", "pinyin": "pán zi", "meaning": "Cái đĩa"},
            {"hanzi": "筷子", "pinyin": "kuài zi", "meaning": "Đôi đũa"},
            {"hanzi": "勺子", "pinyin": "sháo zi", "meaning": "Cái thìa"}
        ]
    }
    is_valid, errors = PreRenderValidator.validate_batch(batch_dup_hz)
    assert not is_valid
    assert any("Trùng chữ Hán '碗'" in err for err in errors)


def test_rule_5_intra_batch_duplicate_meaning_rejected():
    """Batch containing duplicate Vietnamese definitions must be rejected."""
    batch_dup_mean = {
        "topic": "Đồ Dùng Nhà Bếp",
        "words": [
            {"hanzi": "碗", "pinyin": "wǎn", "meaning": "Cái bát"},
            {"hanzi": "大碗", "pinyin": "dà wǎn", "meaning": "Cái bát"},
            {"hanzi": "盘子", "pinyin": "pán zi", "meaning": "Cái đĩa"},
            {"hanzi": "筷子", "pinyin": "kuài zi", "meaning": "Đôi đũa"},
            {"hanzi": "勺子", "pinyin": "sháo zi", "meaning": "Cái thìa"}
        ]
    }
    is_valid, errors = PreRenderValidator.validate_batch(batch_dup_mean)
    assert not is_valid
    assert any("Trùng nghĩa tiếng Việt" in err for err in errors)


# ============================================================================
# 6. NEGATIVE CONTEXT DEDUPLICATION AGAINST HISTORY
# ============================================================================

@pytest.fixture
def mock_vocabcn_history():
    """Standard Google Sheets tab 'vocabCN' history mock."""
    return {
        "recent_topics": [
            "Gia Đình Thân Yêu",
            "Đồ Dùng Học Tập"
        ],
        "past_batches": [
            {
                "id": "2",
                "topic": "Gia Đình Thân Yêu",
                "words": ["爸爸", "妈妈", "儿子", "女儿", "朋友"]
            },
            {
                "id": "3",
                "topic": "Đồ Dùng Học Tập",
                "words": ["书包", "铅笔", "本子", "尺子", "橡皮"]
            }
        ]
    }


def test_negative_context_duplicate_topic_rejection(mock_vocabcn_history):
    """Candidate topic matching any existing sheet topic must be rejected."""
    # Exact match
    candidate_1 = {
        "topic": "Gia Đình Thân Yêu",
        "words": [
            {"hanzi": "爷爷", "pinyin": "yé ye", "meaning": "Ông nội"},
            {"hanzi": "奶奶", "pinyin": "nǎi nai", "meaning": "Bà nội"},
            {"hanzi": "叔叔", "pinyin": "shū shu", "meaning": "Chú / Bác"},
            {"hanzi": "阿姨", "pinyin": "ā yí", "meaning": "Dì / Cô"},
            {"hanzi": "邻居", "pinyin": "lín jū", "meaning": "Hàng xóm"}
        ]
    }
    errors_1 = PreRenderValidator.validate_against_history(candidate_1, history=mock_vocabcn_history)
    assert len(errors_1) > 0, "Expected duplicate topic 'Gia Đình Thân Yêu' to be rejected"
    assert any("trùng lặp với chủ đề đã có trong lịch sử" in err for err in errors_1)

    # Prefix variation: 'HSK 1 • Gia Đình Thân Yêu'
    candidate_2 = dict(candidate_1)
    candidate_2["topic"] = "HSK 1 • Gia Đình Thân Yêu"
    errors_2 = PreRenderValidator.validate_against_history(candidate_2, history=mock_vocabcn_history)
    assert len(errors_2) > 0, "Expected prefix variation 'HSK 1 • Gia Đình Thân Yêu' to be rejected"

    # Match row 3 topic: 'Đồ Dùng Học Tập'
    candidate_3 = dict(candidate_1)
    candidate_3["topic"] = "hsk 1 - đồ dùng học tập"
    errors_3 = PreRenderValidator.validate_against_history(candidate_3, history=mock_vocabcn_history)
    assert len(errors_3) > 0, "Expected match with row 3 topic to be rejected"


def test_negative_context_pair_overlap_rejection(mock_vocabcn_history):
    """Candidate with >= 2 words overlap with any past sheet batch must be rejected."""
    # 2 words overlap with Row 2 (爸爸, 妈妈)
    candidate_overlap_2 = {
        "topic": "Những Người Quen Biết",
        "words": [
            {"hanzi": "爸爸", "pinyin": "bà ba", "meaning": "Bố / Ba"},
            {"hanzi": "妈妈", "pinyin": "mā ma", "meaning": "Mẹ"},
            {"hanzi": "老师", "pinyin": "lǎo shī", "meaning": "Thầy cô giáo"},
            {"hanzi": "学生", "pinyin": "xué sheng", "meaning": "Học sinh"},
            {"hanzi": "医生", "pinyin": "yī shēng", "meaning": "Bác sĩ"}
        ]
    }
    errors = PreRenderValidator.validate_against_history(candidate_overlap_2, history=mock_vocabcn_history)
    assert len(errors) > 0, "Expected >= 2 word overlap with Row 2 to be rejected"
    assert any("Trùng lặp cặp 2 từ" in err and "#2" in err for err in errors)

    # 3 words overlap with Row 3 (书包, 铅笔, 本子)
    candidate_overlap_3 = {
        "topic": "Văn Phòng Phẩm Mới",
        "words": [
            {"hanzi": "书包", "pinyin": "shū bāo", "meaning": "Cặp sách"},
            {"hanzi": "铅笔", "pinyin": "qiān bǐ", "meaning": "Bút chì"},
            {"hanzi": "本子", "pinyin": "běn zi", "meaning": "Quyển vở"},
            {"hanzi": "桌子", "pinyin": "zhuō zi", "meaning": "Cái bàn"},
            {"hanzi": "椅子", "pinyin": "yǐ zi", "meaning": "Cái ghế"}
        ]
    }
    errors_3 = PreRenderValidator.validate_against_history(candidate_overlap_3, history=mock_vocabcn_history)
    assert len(errors_3) > 0, "Expected >= 2 word overlap with Row 3 to be rejected"
    assert any("Trùng lặp cặp 3 từ" in err and "#3" in err for err in errors_3)


def test_negative_context_single_word_reuse_allowed(mock_vocabcn_history):
    """Reusing at most 1 word from a past batch for review is strictly allowed."""
    candidate_single_reuse = {
        "topic": "Người Thân Trong Nhà",
        "words": [
            {"hanzi": "爸爸", "pinyin": "bà ba", "meaning": "Bố / Ba"},  # 1 word from Row 2
            {"hanzi": "爷爷", "pinyin": "yé ye", "meaning": "Ông nội"},
            {"hanzi": "奶奶", "pinyin": "nǎi nai", "meaning": "Bà nội"},
            {"hanzi": "叔叔", "pinyin": "shū shu", "meaning": "Chú / Bác"},
            {"hanzi": "阿姨", "pinyin": "ā yí", "meaning": "Dì / Cô"}
        ]
    }
    errors = PreRenderValidator.validate_against_history(candidate_single_reuse, history=mock_vocabcn_history)
    assert len(errors) == 0, f"Expected 1 word reuse under a fresh topic to be allowed, got errors: {errors}"


# ============================================================================
# 7. LIVE GOOGLE SHEETS TAB 'vocabCN' INTEGRATION
# ============================================================================

@pytest.fixture(scope="module")
def live_vocabcn_history():
    """Module-scoped fixture that caches Google Sheets history to prevent HTTP 429 quota exhaustion."""
    gm = GSheetManager()
    return PreRenderValidator.fetch_vocabcn_history(gsheet_mgr=gm)


def test_live_gsheet_history_loader(live_vocabcn_history):
    """Verify live history loader against Google Sheets tab 'vocabCN'."""
    history = live_vocabcn_history

    assert "recent_topics" in history
    assert "past_batches" in history
    assert len(history["recent_topics"]) >= 2
    assert len(history["past_batches"]) >= 2

    # Check that Row 2 ('Gia Đình Thân Yêu') and Row 3 ('Đồ Dùng Học Tập') are present
    topics = history["recent_topics"]
    assert "Gia Đình Thân Yêu" in topics
    assert "Đồ Dùng Học Tập" in topics

    # Check words from Row 2
    row2_batch = next((b for b in history["past_batches"] if b["id"] == "2" or b["topic"] == "Gia Đình Thân Yêu"), None)
    assert row2_batch is not None
    assert "爸爸" in row2_batch["words"]
    assert "妈妈" in row2_batch["words"]


def test_live_gsheet_negative_context_rejection(live_vocabcn_history):
    """Verify negative context rejection against live sheet data."""
    history = live_vocabcn_history

    # 1. Candidate duplicating Row 2 topic must be rejected
    candidate_dup_topic = {
        "topic": "Gia Đình Thân Yêu",
        "words": [
            {"hanzi": "碗", "pinyin": "wǎn", "meaning": "Bát / Chén"},
            {"hanzi": "盘子", "pinyin": "pán zi", "meaning": "Cái đĩa"},
            {"hanzi": "筷子", "pinyin": "kuài zi", "meaning": "Đôi đũa"},
            {"hanzi": "勺子", "pinyin": "sháo zi", "meaning": "Cái thìa"},
            {"hanzi": "锅", "pinyin": "guō", "meaning": "Cái nồi"}
        ]
    }
    is_valid, errors = PreRenderValidator.validate_batch(candidate_dup_topic, history=history)
    assert not is_valid
    assert any("trùng lặp với chủ đề đã có trong lịch sử" in err for err in errors)

    # 2. Candidate duplicating Row 3 words (书包, 铅笔) must be rejected
    candidate_dup_words = {
        "topic": "Dụng Cụ Làm Việc",
        "words": [
            {"hanzi": "书包", "pinyin": "shū bāo", "meaning": "Cặp sách"},
            {"hanzi": "铅笔", "pinyin": "qiān bǐ", "meaning": "Bút chì"},
            {"hanzi": "碗", "pinyin": "wǎn", "meaning": "Bát / Chén"},
            {"hanzi": "盘子", "pinyin": "pán zi", "meaning": "Cái đĩa"},
            {"hanzi": "锅", "pinyin": "guō", "meaning": "Cái nồi"}
        ]
    }
    is_valid, errors = PreRenderValidator.validate_batch(candidate_dup_words, history=history)
    assert not is_valid
    assert any("Trùng lặp cặp 2 từ" in err for err in errors)


# ============================================================================
# 8. FULL VALID CANDIDATE BATCH APPROVAL
# ============================================================================

def test_full_valid_candidate_approval(mock_vocabcn_history):
    """A completely valid candidate batch with 5 words must pass with 0 errors."""
    valid_batch = {
        "topic": "Đồ Dùng Nhà Bếp",
        "level": "HSK 1",
        "words": [
            {"hanzi": "碗", "pinyin": "wǎn", "meaning": "Bát / Chén"},
            {"hanzi": "盘子", "pinyin": "pán zi", "meaning": "Cái đĩa"},
            {"hanzi": "筷子", "pinyin": "kuài zi", "meaning": "Đôi đũa"},
            {"hanzi": "勺子", "pinyin": "sháo zi", "meaning": "Cái thìa / Muỗng"},
            {"hanzi": "锅", "pinyin": "guō", "meaning": "Cái nồi / Chảo"}
        ]
    }
    is_valid, errors = PreRenderValidator.validate_batch(valid_batch, history=mock_vocabcn_history)
    assert is_valid, f"Expected valid batch to pass, got errors: {errors}"
    assert len(errors) == 0

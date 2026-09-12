#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Empirical Challenger 1: Comprehensive Adversarial Stress Test Suite
Testing:
1. Gatekeeper 1 Linguistic Rules (Rule 1..5) across pinyinquiz, vocabCNquiz, vocabVNquiz
2. Traditional Chinese Homoglyphs & Subtle Variant Characters
3. Malformed Pinyin, Syllables, Invalid Tone Marks, and Erhua Contractions
4. Foreign Consonants (f, j, w, z) & Forbidden English Loanwords vs Vietnamese Collisions
5. Single Topic String Validation & List Delimiters
6. Negative Context Deduplication (Topic recurrence & Pair overlap)
7. Gemini 6-Key Dynamic Rotation, Zero-Secret Masking & 429 Circuit Breaker
8. Cross-Pipeline Validator Harmonization
"""

import os
import sys
import time
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import pinyinquiz.src.pre_render_validator as pinyin_val
import vocabCNquiz.src.pre_render_validator as vocabcn_val
import vocabVNquiz.src.pre_render_validator as vocabvn_val

import pinyinquiz.src.llm_client as pinyin_llm
import vocabCNquiz.src.llm_client as vocabcn_llm
import vocabVNquiz.src.llm_client as vocabvn_llm
from vocabCNquiz.src.llm_client import (
    parse_gemini_keys,
    mask_key,
    parse_json_from_llm,
    call_gemini_api,
    call_openai_compatible_api,
    FALLBACK_GEMINI_MODELS,
    DEFAULT_GEMINI_MODEL
)

VALIDATORS = [
    ("pinyinquiz", pinyin_val.PreRenderValidator),
    ("vocabCNquiz", vocabcn_val.PreRenderValidator),
    ("vocabVNquiz", vocabvn_val.PreRenderValidator)
]


# ============================================================================
# 1. ADVERSARIAL TRADITIONAL CHINESE & HOMOGLYPH REJECTION
# ============================================================================

@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_adversarial_traditional_characters_comprehensive(pipeline_name, validator):
    """Stress test comprehensive traditional Chinese homoglyphs and variant forms."""
    trad_chars = [
        "體", "國", "說", "學", "這", "會", "個", "門", "經", "車", "愛", "書", "買",
        "點", "誰", "麼", "後", "電", "語", "漢", "們", "聽", "開", "關", "讓", "幫",
        "幾", "邊", "錢", "號", "飯", "題", "視", "爲", "為", "樂", "長", "師", "筆",
        "鐘", "飛", "樣", "醫", "難", "機", "歡", "顏", "貓", "藍", "綠", "雞", "畫",
        "雙", "傘", "齒", "麵", "髮", "龍", "媽", "話", "發", "頭", "見", "東", "廣",
        "氣", "兒", "業", "產", "當", "實", "問", "動", "過", "進", "無", "報", "萬",
        "選", "與", "對", "總", "結", "聲", "變", "陽", "陰", "雲", "風", "鳥", "馬",
        "豬", "網", "寫", "讀", "課", "試", "檢", "認", "識", "記", "請", "謝", "賣",
        "貴", "賓", "館", "飲", "飽", "餓", "餃", "餅", "鴨", "鵝", "藥", "療", "診",
        "斷", "傷", "熱", "溫", "涼", "霧", "颱", "輛", "輪", "鐵", "銀", "幣", "帳",
        "單", "費", "稅", "價", "優", "質", "數", "據", "圖", "紙", "腦", "頻", "響",
        "錶", "環", "衛", "廚", "廳", "臥", "臺", "樓", "櫃", "燈", "鏡", "褲", "襪",
        "帶", "鹹", "鮮", "週", "遲", "舊", "圓", "彎", "遠", "處", "親", "鄰", "孫",
        "爺", "侶", "練", "護", "導", "遊", "員", "蘋", "傳", "統", "灣", "習", "節",
        "歲", "曆", "歷", "區", "縣", "鄉", "鎮", "郵", "園", "廠", "庫", "橋", "樹",
        "葉", "雜", "誌", "條", "隻", "塊", "張", "種", "類", "齊", "龜", "豐", "艷",
        "麗", "義", "專", "業", "務", "辦", "協", "參", "緊", "牽", "艱", "嘆", "應",
        "慶", "廢", "莊", "廁", "廂", "廈", "閃", "閉", "閏", "閑", "閔", "閘", "閣",
        "閥", "閱", "閹", "閻", "闊", "闌", "闐", "闔", "闕", "關", "韋", "韌", "韓",
        "韻", "頁", "頂", "頃", "項", "順", "須", "頑", "顧", "頓", "頗", "領", "頡",
        "頤", "飠", "飾", "餡", "餛", "飩", "饅", "饌", "饗", "駕", "駝", "駐", "駿",
        "騎", "騙", "鬆", "鬍", "鬧", "魂", "魘", "魯", "魷", "鮑", "鮫", "鮭", "鯉",
        "鯊", "鯨", "鰓", "鳩", "鳳", "鳴", "鳶", "鴉", "鴦", "鴛", "鴕", "鴿", "鴻",
        "鵑", "鵠", "鵬", "鶴", "鸚", "鵡", "鹵", "麥", "黃", "黨", "黌", "鈔"
    ]
    for tc in trad_chars:
        errors = validator.check_simplified_chinese(tc)
        assert len(errors) > 0, f"[{pipeline_name}] Validator failed to reject Traditional character '{tc}'"


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_adversarial_mixed_traditional_in_sentences(pipeline_name, validator):
    """Stress test compound words and phrases where only 1 character is Traditional."""
    mixed_cases = [
        "这个是學校",  # 學 is traditional
        "买東西",     # 東 is traditional
        "天气很熱",    # 熱 is traditional
        "我的媽媽",    # 媽 is traditional
        "明天過节",    # 過 is traditional
        "身體健康",    # 體 is traditional
        "环境保護",    # 護 is traditional
        "非常感謝",    # 謝 is traditional
        "去圖書館"     # 圖, 館 are traditional
    ]
    for mc in mixed_cases:
        errors = validator.check_simplified_chinese(mc)
        assert len(errors) > 0, f"[{pipeline_name}] Validator failed on mixed traditional string '{mc}'"


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_universal_heritage_chinese_accepted(pipeline_name, validator):
    """Universal heritage characters shared identically between Simplified and Traditional must be accepted."""
    heritage_cases = [
        "水", "火", "木", "人", "口", "手", "心", "生", "床", "衣服",
        "桌椅", "窗户", "房间", "数量", "折扣", "天", "地", "上", "下", "中"
    ]
    for hc in heritage_cases:
        errors = validator.check_simplified_chinese(hc)
        assert len(errors) == 0, f"[{pipeline_name}] Validator falsely rejected universal heritage '{hc}': {errors}"


# ============================================================================
# 2. ADVERSARIAL SINGLE TOPIC VALIDATION
# ============================================================================

@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_adversarial_topic_delimiters_and_abbreviations(pipeline_name, validator):
    """Stress test topic validator with list delimiters (; and |) and abbreviations (v.v., etc.)."""
    invalid_topics = [
        "Đồ Ăn; Thức Uống",
        "Trường Học | Thư Viện",
        "Chào Hỏi, v.v.",
        "Đồ dùng vv",
        "Phương tiện v/v",
        "Chủ đề etc.",
        "Chủ đề etc",
        "A",                   # Length < 2
        "",                    # Empty
        "   ",                 # Whitespace
        "T" * 51,              # Length > 50
        "Đồ Ăn; Uống | Chơi",
        "Từ vựng v.v. hàng ngày"
    ]
    for it in invalid_topics:
        errors = validator.check_single_topic(it)
        assert len(errors) > 0, f"[{pipeline_name}] Validator failed to reject invalid topic '{it}'"


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_valid_natural_topics_with_connectors(pipeline_name, validator):
    """Valid single topics with natural connectors (&, và, -, •) must pass."""
    valid_topics = [
        "Đồ Dùng Nhà Bếp",
        "HSK 1 • Đồ Ăn",
        "HSK 2 - Giao Thông",
        "Cảm xúc và tâm trạng",
        "Thời tiết & khí hậu",
        "Gia Đình & Bạn Bè",
        "Môi trường - Đời sống",
        "Thói Quen Hàng Ngày",
        "Ẩm Thực Đường Phố",
        "Trang Phục Bốn Mùa"
    ]
    for vt in valid_topics:
        errors = validator.check_single_topic(vt)
        assert len(errors) == 0, f"[{pipeline_name}] Validator rejected valid topic '{vt}': {errors}"


# ============================================================================
# 3. ADVERSARIAL PINYIN SYLLABLES, TONE MARKS & ERHUA CONTRACTIONS
# ============================================================================

@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_adversarial_pinyin_tone_marks_and_positions(pipeline_name, validator):
    """Stress test valid pinyin tone vowels and neutral tones."""
    valid_pairs = [
        ("爸爸", "bà ba"),
        ("妈妈", "mā ma"),
        ("苹果", "píng guǒ"),
        ("绿茶", "lǜ chá"),
        ("女儿", "nǚ ér"),
        ("驴子", "lǘ zi"),
        ("行", "xíng"),
        ("月亮", "yuè liang"),
        ("朋友", "péng you"),
        ("桌子", "zhuō zi"),
        ("我们", "wǒ men"),
        ("什么", "shén me"),
        ("怎么", "zěn me")
    ]
    for hz, py in valid_pairs:
        errors, norm_py = validator.check_pinyin_syllables(hz, py)
        assert len(errors) == 0, f"[{pipeline_name}] Rejected valid pinyin '{hz}' - '{py}': {errors}"


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_adversarial_pinyin_untoned_syllable_rejection(pipeline_name, validator):
    """Stress test rejection of un-toned syllables that are not legitimate neutral particles."""
    invalid_pairs = [
        ("学校", "xué xiao"),        # xiao is not neutral
        ("飞机", "fēi ji"),          # ji is not neutral
        ("跑步", "pǎo bu"),          # bu is not neutral
        ("买单", "mǎi dan"),         # dan is not neutral
        ("老师", "lǎo shi_fake"),
        ("苹果", "ping guo")         # completely untoned
    ]
    for hz, py in invalid_pairs:
        errors, _ = validator.check_pinyin_syllables(hz, py)
        assert len(errors) > 0, f"[{pipeline_name}] Failed to reject invalid un-toned pinyin '{hz}' - '{py}'"


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_adversarial_erhua_contractions_and_violations(pipeline_name, validator):
    """Stress test valid Erhua (儿化) vs illegal contractions with trailing 'r'."""
    # Valid Erhua
    valid_erhua = [
        ("哪儿", "nǎr"),
        ("这儿", "zhèr"),
        ("那儿", "nàr"),
        ("玩儿", "wánr"),
        ("一点儿", "yì diǎnr"),
        ("花儿", "huār"),
        ("哪儿", "nǎ er"),
        ("这儿", "zhè er")
    ]
    for hz, py in valid_erhua:
        errors, _ = validator.check_pinyin_syllables(hz, py)
        assert len(errors) == 0, f"[{pipeline_name}] Rejected valid Erhua '{hz}' - '{py}': {errors}"

    # Invalid Erhua: word does NOT end with 儿, but pinyin ends with contracted 'r'
    invalid_erhua = [
        ("爸爸", "bàr"),
        ("苹果", "píngr"),
        ("学校", "xué xiàor"),
        ("大门", "dà ménr")
    ]
    for hz, py in invalid_erhua:
        errors, _ = validator.check_pinyin_syllables(hz, py)
        assert len(errors) > 0, f"[{pipeline_name}] Failed to reject illegal Erhua contraction '{hz}' - '{py}'"


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_adversarial_syllable_count_mismatches(pipeline_name, validator):
    """Stress test 1:1 syllable count enforcement."""
    mismatches = [
        ("苹果", "píng"),                      # 2 chars, 1 syl
        ("苹果", "píng guǒ zi"),               # 2 chars, 3 syls
        ("公共汽车", "gōng gòng"),              # 4 chars, 2 syls
        ("学校", "xué xiào da shi"),           # 2 chars, 4 syls
        ("书", "shū běn"),                     # 1 char, 2 syls
        ("照相机", "zhào xiàng jī zi")          # 3 chars, 4 syls
    ]
    for hz, py in mismatches:
        errors, _ = validator.check_pinyin_syllables(hz, py)
        assert len(errors) > 0, f"[{pipeline_name}] Failed to reject syllable count mismatch '{hz}' - '{py}'"


# ============================================================================
# 4. ADVERSARIAL VIETNAMESE DEFINITIONS & FORBIDDEN ENGLISH LOANWORDS
# ============================================================================

@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_adversarial_forbidden_english_words(pipeline_name, validator):
    """Stress test detection of English words embedded in Vietnamese definitions."""
    english_injections = [
        "Quả apple tươi ngon",
        "Uống cup coffee đá",
        "Ngồi trên chair gỗ",
        "Để sách trên table",
        "Đi học bằng bus",
        "Gọi một chiếc car",
        "Gặp gỡ teacher",
        "Khám bác sĩ doctor",
        "Đi shopping cuối tuần",
        "Bắt con cat",
        "Nuôi con dog",
        "Đọc quyển book",
        "Ăn bánh cake"
    ]
    for mean in english_injections:
        errors = validator.check_vietnamese_meaning(mean)
        assert len(errors) > 0, f"[{pipeline_name}] Failed to reject forbidden English in '{mean}'"


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_adversarial_foreign_consonants_unwhitelisted(pipeline_name, validator):
    """Stress test unwhitelisted words with foreign letters (f, j, w, z)."""
    foreign_cases = [
        "Uống fastfood",
        "Tham gia workshop",
        "Chơi puzzle",
        "Nghe nhạc jazz",
        "Mặc quần jeans",
        "Khu vực zone cấm",
        "Chế độ full màn hình"
    ]
    for fc in foreign_cases:
        errors = validator.check_vietnamese_meaning(fc)
        assert len(errors) > 0, f"[{pipeline_name}] Failed to reject foreign consonant in '{fc}'"


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_whitelisted_vietnamese_loanwords(pipeline_name, validator):
    """Legitimate whitelisted Vietnamese loanwords must be accepted."""
    whitelisted = [
        "Đi xe buýt",
        "Đi xe taxi",
        "Uống cà phê",
        "Áo sơ-mi trắng",
        "Xem tivi",
        "Mạng wifi nhanh",
        "Gửi email",
        "Học online",
        "Xem video vui",
        "Máy tính laptop"
    ]
    for wl in whitelisted:
        errors = validator.check_vietnamese_meaning(wl)
        assert len(errors) == 0, f"[{pipeline_name}] Falsely rejected whitelisted loanword '{wl}': {errors}"


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_whitelisted_vietnamese_homographs(pipeline_name, validator):
    """Legitimate Vietnamese homographs (no, do, say, son, men) must NEVER be falsely rejected."""
    homographs = [
        "Ăn no",
        "No bụng",
        "Tự do",
        "Lý do",
        "Say xe",
        "Say rượu",
        "Say đắm",
        "Thỏi son",
        "Son môi",
        "Men rượu",
        "Men gan"
    ]
    for hg in homographs:
        errors = validator.check_vietnamese_meaning(hg)
        assert len(errors) == 0, f"[{pipeline_name}] Falsely rejected legitimate Vietnamese homograph '{hg}': {errors}"


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_adversarial_hidden_pinyin_and_corruptions(pipeline_name, validator):
    """Stress test rejection of underscore pinyin placeholders and corruptions."""
    corrupted = [
        "p _ _ _   g _ _",
        "Bàn học _ ghế",
        "p__ng_gu_",
        "_",
        "_____"
    ]
    for cr in corrupted:
        errors = validator.check_vietnamese_meaning(cr)
        assert len(errors) > 0, f"[{pipeline_name}] Failed to reject underscore corruption '{cr}'"


# ============================================================================
# 5. ADVERSARIAL FULL BATCH INTEGRITY & INTRA-BATCH DUPLICATES
# ============================================================================

@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_adversarial_batch_word_count_boundaries(pipeline_name, validator):
    """Batches with count != 5 must be rejected."""
    # 0 words
    b0 = {"topic": "Đồ Dùng", "words": []}
    v0, err0 = validator.validate_batch(b0)
    assert v0 is False

    # 4 words
    b4 = {
        "topic": "Đồ Dùng",
        "words": [
            {"hanzi": "筷子", "pinyin": "kuài zi", "meaning": "Đôi đũa"},
            {"hanzi": "碗", "pinyin": "wǎn", "meaning": "Cái bát"},
            {"hanzi": "盘子", "pinyin": "pán zi", "meaning": "Cái đĩa"},
            {"hanzi": "勺子", "pinyin": "sháo zi", "meaning": "Cái thìa"}
        ]
    }
    v4, err4 = validator.validate_batch(b4)
    assert v4 is False

    # 6 words
    b6 = {
        "topic": "Đồ Dùng",
        "words": [
            {"hanzi": "筷子", "pinyin": "kuài zi", "meaning": "Đôi đũa"},
            {"hanzi": "碗", "pinyin": "wǎn", "meaning": "Cái bát"},
            {"hanzi": "盘子", "pinyin": "pán zi", "meaning": "Cái đĩa"},
            {"hanzi": "勺子", "pinyin": "sháo zi", "meaning": "Cái thìa"},
            {"hanzi": "锅", "pinyin": "guō", "meaning": "Cái nồi"},
            {"hanzi": "杯子", "pinyin": "bēi zi", "meaning": "Cái cốc"}
        ]
    }
    v6, err6 = validator.validate_batch(b6)
    assert v6 is False


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_adversarial_intra_batch_duplicates(pipeline_name, validator):
    """Stress test intra-batch duplicates (same Hanzi or same Vietnamese meaning)."""
    batch_dup_hz = {
        "topic": "Gia Đình",
        "words": [
            {"hanzi": "爸爸", "pinyin": "bà ba", "meaning": "Bố"},
            {"hanzi": "爸爸", "pinyin": "bà ba", "meaning": "Ba ruột"},
            {"hanzi": "儿子", "pinyin": "ér zi", "meaning": "Con trai"},
            {"hanzi": "女儿", "pinyin": "nǚ ér", "meaning": "Con gái"},
            {"hanzi": "朋友", "pinyin": "péng you", "meaning": "Bạn bè"}
        ]
    }
    v_hz, err_hz = validator.validate_batch(batch_dup_hz)
    assert v_hz is False
    assert any("Trùng chữ Hán" in e for e in err_hz)

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
    v_m, err_m = validator.validate_batch(batch_dup_mean)
    assert v_m is False
    assert any("Trùng nghĩa tiếng Việt" in e for e in err_m)


# ============================================================================
# 6. NEGATIVE CONTEXT DEDUPLICATION STRESS TESTS
# ============================================================================

@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_negative_context_topic_normalization_and_recurrence(pipeline_name, validator):
    """Stress test topic recurrence deduplication across diverse prefix formatting."""
    history = {
        "recent_topics": [
            "Đồ Ăn Hàng Ngày",
            "Giao Tiếp Xã Hội",
            "Thời Tiết Bốn Mùa"
        ],
        "past_batches": []
    }
    # Topics that normalize to 'đồ ăn hàng ngày'
    recurring_candidates = [
        "HSK 1 • Đồ Ăn Hàng Ngày",
        "hsk 2 - đồ ăn hàng ngày",
        "HSK 3 : ĐỒ ĂN HÀNG NGÀY",
        "Đồ Ăn Hàng Ngày",
        "  đồ ăn hàng ngày  "
    ]
    for top in recurring_candidates:
        cand = {
            "topic": top,
            "words": [
                {"hanzi": "米饭", "pinyin": "mǐ fàn", "meaning": "Cơm trắng"},
                {"hanzi": "面条", "pinyin": "miàn tiáo", "meaning": "Mì sợi"},
                {"hanzi": "包子", "pinyin": "bāo zi", "meaning": "Bánh bao"},
                {"hanzi": "饺子", "pinyin": "jiǎo zi", "meaning": "Sủi cảo"},
                {"hanzi": "鸡蛋", "pinyin": "jī dàn", "meaning": "Trứng gà"}
            ]
        }
        is_valid, errors = validator.validate_batch(cand, history=history)
        assert is_valid is False, f"[{pipeline_name}] Failed to reject recurring topic '{top}'"
        assert any("trùng lặp với chủ đề" in e for e in errors)


@pytest.mark.parametrize("pipeline_name,validator", VALIDATORS)
def test_negative_context_pair_overlap_boundary(pipeline_name, validator):
    """
    Assert exact boundary:
    - 0 words overlap: PASS
    - 1 word overlap: PASS (spaced repetition review)
    - 2 words overlap: FAIL
    - 3+ words overlap: FAIL
    """
    history = {
        "recent_topics": ["Món Ăn Quen Thuộc"],
        "past_batches": [
            {"id": "10", "topic": "Món Ăn Quen Thuộc", "words": ["米饭", "面条", "苹果", "牛奶", "面包"]}
        ]
    }

    # 0 words overlap
    c0 = {
        "topic": "Động Vật",
        "words": [
            {"hanzi": "猫", "pinyin": "māo", "meaning": "Con mèo"},
            {"hanzi": "狗", "pinyin": "gǒu", "meaning": "Con chó"},
            {"hanzi": "鸟", "pinyin": "niǎo", "meaning": "Con chim"},
            {"hanzi": "鱼", "pinyin": "yú", "meaning": "Con cá"},
            {"hanzi": "马", "pinyin": "mǎ", "meaning": "Con ngựa"}
        ]
    }
    v0, e0 = validator.validate_batch(c0, history=history)
    assert v0 is True, f"0-overlap failed: {e0}"

    # 1 word overlap (米饭) -> Allowed
    c1 = {
        "topic": "Bữa Cơm Tối",
        "words": [
            {"hanzi": "米饭", "pinyin": "mǐ fàn", "meaning": "Cơm trắng"},
            {"hanzi": "青菜", "pinyin": "qīng cài", "meaning": "Rau xanh"},
            {"hanzi": "猪肉", "pinyin": "zhū ròu", "meaning": "Thịt lợn"},
            {"hanzi": "鱼汤", "pinyin": "yú tāng", "meaning": "Canh cá"},
            {"hanzi": "豆腐", "pinyin": "dòu fu", "meaning": "Đậu phụ"}
        ]
    }
    v1, e1 = validator.validate_batch(c1, history=history)
    assert v1 is True, f"1-overlap failed: {e1}"

    # 2 words overlap (米饭, 面条) -> REJECTED
    c2 = {
        "topic": "Ẩm Thực Quê Hương",
        "words": [
            {"hanzi": "米饭", "pinyin": "mǐ fàn", "meaning": "Cơm trắng"},
            {"hanzi": "面条", "pinyin": "miàn tiáo", "meaning": "Mì sợi"},
            {"hanzi": "青菜", "pinyin": "qīng cài", "meaning": "Rau xanh"},
            {"hanzi": "猪肉", "pinyin": "zhū ròu", "meaning": "Thịt lợn"},
            {"hanzi": "豆腐", "pinyin": "dòu fu", "meaning": "Đậu phụ"}
        ]
    }
    v2, e2 = validator.validate_batch(c2, history=history)
    assert v2 is False
    assert any("Trùng lặp cặp" in e for e in e2)


# ============================================================================
# 7. GEMINI 6-KEY DYNAMIC ROTATION, ZERO-SECRETS & CIRCUIT BREAKER
# ============================================================================

def test_gemini_key_masking_comprehensive():
    """Verify mask_key on edge-case inputs."""
    assert mask_key(None) == "None"
    assert mask_key("") == "None"
    assert mask_key("1") == "****"
    assert mask_key("12345678") == "****"
    assert mask_key("AIzaSy123456789") == "AIzaSy...****"
    assert mask_key("AQ.Ab8x9Y2z3W4v5U") == "AQ.Ab8...****"
    assert "9Y2z3W4v5U" not in mask_key("AQ.Ab8x9Y2z3W4v5U")


def test_gemini_key_parsing_delimiters_and_duplicates():
    """Verify key parsing handles tricky mixed delimiters, newlines, and duplicate tokens."""
    mixed_raw = "key_alpha, key_beta; key_gamma\nkey_delta,key_alpha\n\nkey_epsilon;key_zeta"
    keys = parse_gemini_keys(mixed_raw)
    assert len(keys) == 6
    assert keys == ["key_alpha", "key_beta", "key_gamma", "key_delta", "key_epsilon", "key_zeta"]


@patch("vocabCNquiz.src.llm_client.requests.post")
@patch("vocabCNquiz.src.llm_client.time.sleep")
def test_circuit_breaker_429_recovery_cooldown_execution(mock_sleep, mock_post):
    """Verify circuit breaker 429 quota exhaustion initiates 60s cooldown recovery loop in vocabCN."""
    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_post.return_value = mock_resp_429

    keys = ["key1_alpha", "key2_beta", "key3_gamma"]
    res = vocabcn_llm.call_gemini_api(prompt="Test Prompt", api_keys=keys, max_recovery_cycles=1)

    assert res is None
    # Verify cooldown was called with 60s
    mock_sleep.assert_called_with(60)


@patch("pinyinquiz.src.llm_client.requests.post")
@patch("pinyinquiz.src.llm_client.time.sleep")
def test_pinyinquiz_circuit_breaker_429_recovery_cooldown_execution(mock_sleep, mock_post):
    """Verify circuit breaker 429 quota exhaustion initiates 60s cooldown in pinyinquiz (no NameError)."""
    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_post.return_value = mock_resp_429

    keys = ["key1_alpha", "key2_beta"]
    res = pinyin_llm.call_gemini_api(prompt="Test Prompt", api_keys=keys, max_recovery_cycles=1)

    assert res is None
    mock_sleep.assert_called_with(60)


@patch("vocabVNquiz.src.llm_client.requests.post")
@patch("vocabVNquiz.src.llm_client.time.sleep")
def test_vocabvnquiz_circuit_breaker_429_recovery_cooldown_execution(mock_sleep, mock_post):
    """Verify circuit breaker 429 quota exhaustion initiates 60s cooldown in vocabVN."""
    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_post.return_value = mock_resp_429

    keys = ["key1_alpha", "key2_beta"]
    res = vocabvn_llm.call_gemini_api(prompt="Test Prompt", api_keys=keys, max_recovery_cycles=1)

    assert res is None
    mock_sleep.assert_called_with(60)


@patch("vocabCNquiz.src.llm_client.requests.post")
def test_gemini_key_rotation_failover_success_on_second_key(mock_post):
    """Verify that when Key 1 fails with 429, Key 2 immediately succeeds."""
    mock_429 = MagicMock()
    mock_429.status_code = 429

    mock_200 = MagicMock()
    mock_200.status_code = 200
    mock_200.json.return_value = {
        "candidates": [{
            "content": {"parts": [{"text": '[{"topic": "Thành Công", "words": []}]'}]}
        }]
    }

    mock_post.side_effect = [mock_429, mock_200]

    keys = ["key1_broken", "key2_working"]
    result = vocabcn_llm.call_gemini_api(prompt="Generate batch", api_keys=keys, max_recovery_cycles=0)

    assert result is not None
    assert "Thành Công" in result


def test_parse_json_from_llm_extreme_robustness_across_all_pipelines():
    """Verify LLM JSON parser against tricky wrappers, trailing commas, and fences across all 3 modules."""
    modules = [
        ("pinyinquiz", pinyin_llm),
        ("vocabCNquiz", vocabcn_llm),
        ("vocabVNquiz", vocabvn_llm)
    ]
    for mod_name, mod in modules:
        # 1. Trailing commas in object & array
        j1 = '{"topic": "Du Lịch", "words": ["北京", "上海",], }'
        p1 = mod.parse_json_from_llm(j1)
        assert p1 == {"topic": "Du Lịch", "words": ["北京", "上海"]}, f"[{mod_name}] Failed on trailing commas dict"

        # 2. Markdown json code block
        j2 = '```json\n[{"id": 1, "topic": "Gia Đình"}]\n```'
        p2 = mod.parse_json_from_llm(j2)
        assert p2 == [{"id": 1, "topic": "Gia Đình"}], f"[{mod_name}] Failed on markdown fence"

        # 3. Conversational preamble with raw array
        j3 = 'Here is your generated response:\n[{"id": 5, "topic": "Ẩm Thực"}]\nHope you enjoy it!'
        p3 = mod.parse_json_from_llm(j3)
        assert p3 == [{"id": 5, "topic": "Ẩm Thực"}], f"[{mod_name}] Failed on preamble"

        # 4. Invalid input
        assert mod.parse_json_from_llm("") is None, f"[{mod_name}] Empty string should be None"
        assert mod.parse_json_from_llm(None) is None, f"[{mod_name}] None should be None"
        assert mod.parse_json_from_llm("Random text without any json brackets") is None, f"[{mod_name}] Random text should be None"

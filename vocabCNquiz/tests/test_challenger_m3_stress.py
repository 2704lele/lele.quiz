#!/usr/bin/env python3
"""
Adversarial Stress Test Suite for Gatekeeper 1 & Negative Context Validation (Milestone 3 / Requirement R3).
Authored by challenger_m3 (Empirical Challenger).

Tests:
1. Adversarial Traditional Chinese characters (妈妈 vs 媽媽, 开门 vs 開門, 广东 vs 廣東, 国 vs 國, and 100+ others).
2. English words and foreign injection inside Vietnamese definitions ("Quả apple", "Cái chair", "Đi taxi", "Học ở school", etc.).
3. Syllable count mismatches and Erhua corner cases.
4. Missing tone marks and invalid neutral tone syllables ("dian nao", "ping guo", etc.).
5. Negative context topic deduplication and >= 2 word overlap rejection against live/mocked sheet history.
6. Full valid candidate batches approval ("Đồ Dùng Nhà Bếp", "Rau Củ Quả", etc.) with 0 errors.
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


# ============================================================================
# 1. TRADITIONAL CHINESE ADVERSARIAL STRESS TESTS
# ============================================================================

def test_stress_traditional_pairs():
    """Verify that paired Traditional variants are rejected while Simplified variants pass."""
    pairs = [
        ("媽媽", "妈妈"),
        ("開門", "开门"),
        ("廣東", "广东"),
        ("國家", "国家"),
        ("學生", "学生"),
        ("買東西", "买东西"),
        ("謝謝", "谢谢"),
        ("電話", "电话"),
        ("飛機", "飞机"),
        ("體育", "体育"),
        ("說話", "说话"),
        ("車站", "车站"),
        ("歡樂", "欢乐"),
        ("藍色", "蓝色"),
        ("麵包", "面包"),
        ("龍蝦", "龙虾"),
        ("魚肉", "鱼肉"),
        ("馬車", "马车"),
        ("寫字", "写字"),
        ("讀書", "读书"),
        ("蘋果", "苹果"),
        ("傳統", "传统"),
        ("臺灣", "台湾"),
        ("熱水", "热水"),
        ("學習", "学习")
    ]
    for trad, simp in pairs:
        # Traditional MUST fail
        trad_errs = PreRenderValidator.check_simplified_chinese(trad)
        assert len(trad_errs) > 0, f"Traditional '{trad}' was incorrectly accepted!"
        assert any("Phồn thể" in e for e in trad_errs), f"Error for '{trad}' should mention 'Phồn thể': {trad_errs}"

        # Simplified MUST pass
        simp_errs = PreRenderValidator.check_simplified_chinese(simp)
        assert len(simp_errs) == 0, f"Simplified '{simp}' was incorrectly rejected with: {simp_errs}"


def test_stress_all_traditional_char_set():
    """All individual characters in STRICT_TRADITIONAL_CHARS must be rejected."""
    sample_chars = list(STRICT_TRADITIONAL_CHARS)[:50]  # Test first 50 chars from the set
    for ch in sample_chars:
        errs = PreRenderValidator.check_simplified_chinese(ch)
        assert len(errs) > 0, f"Traditional char '{ch}' failed to trigger rejection!"


# ============================================================================
# 2. VIETNAMESE MEANING & ENGLISH INJECTION STRESS TESTS
# ============================================================================

def test_stress_english_injections():
    """Verify that English words injected into Vietnamese definitions are deterministically caught."""
    injections = [
        ("Quả apple ngọt", "apple"),
        ("Cái chair màu nâu", "chair"),
        ("Trường school của em", "school"),
        ("Con dog đang sủa", "dog"),
        ("Con cat đáng yêu", "cat"),
        ("Cái table bằng gỗ", "table"),
        ("Bác sĩ doctor ở bệnh viện", "doctor"),
        ("Uống milk mỗi sáng", "milk"),
        ("Cửa sổ window mở to", "window"),
        ("Mua đồ shopping cuối tuần", "shopping"),
        ("Ăn bánh cake sinh nhật", "cake"),
        ("Học sinh student chăm chỉ", "student"),
        ("Thầy teacher giảng bài", "teacher"),
        ("Quyển book dày cộp", "book"),
        ("Bút pen viết chữ", "pen"),
        ("Cái bookshelf đựng sách", "bookshelf"),
        ("Cái mirror soi gương", "mirror")
    ]
    for sentence, word in injections:
        errs = PreRenderValidator.check_vietnamese_meaning(sentence, hanzi="测试", pinyin="cè shì")
        assert len(errs) > 0, f"Injection '{sentence}' containing '{word}' was not rejected!"
        assert any("tiếng Anh" in e or "ngoại ngữ" in e for e in errs)


def test_stress_vietnamese_accepted_loanwords():
    """Verify standard accepted Vietnamese loanwords pass without false positives."""
    loanwords = [
        "Xem tivi buổi tối",
        "Ti-vi màn hình phẳng",
        "Uống cà phê sáng",
        "Cafe sữa đá",
        "Đi xe buýt đến trường",
        "Kết nối mạng internet tốc độ cao",
        "Mạng wifi rất mạnh",
        "Gửi qua email công việc",
        "Học online tại nhà",
        "Trang website thông tin",
        "Tải ứng dụng app mới",
        "Xem video clip vui",
        "Cái ly nước cam",
        "Chiếc laptop học tập",
        "Chơi game giải trí"
    ]
    for phrase in loanwords:
        errs = PreRenderValidator.check_vietnamese_meaning(phrase, hanzi="词汇", pinyin="cí huì")
        assert len(errs) == 0, f"Accepted Vietnamese phrase '{phrase}' was falsely rejected with: {errs}"


def test_stress_foreign_character_rejections():
    """Definitions containing unwhitelisted foreign letters (f, j, w, z) must be rejected."""
    foreign_cases = [
        "Đồ vật xz",
        "Loại quà fix",
        "Trò chơi wow",
        "Món ăn fast",
        "Dụng cụ jazz"
    ]
    for case in foreign_cases:
        errs = PreRenderValidator.check_vietnamese_meaning(case, hanzi="测试", pinyin="cè shì")
        assert len(errs) > 0, f"Foreign word case '{case}' was not rejected!"


# ============================================================================
# 3. PINYIN SYLLABLE COUNT & ERHUA CORNER CASES
# ============================================================================

def test_stress_pinyin_syllable_mismatches():
    """Various Hanzi vs Pinyin syllable mismatches must be rejected."""
    mismatches = [
        ("碗", "wǎn zi", 1, 2),
        ("筷子", "kuài", 2, 1),
        ("公共汽车", "gōng gòng qì", 4, 3),
        ("公共汽车", "gōng gòng qì chē chē", 4, 5),
        ("苹果", "píng guǒ zi", 2, 3),
        ("书包", "shū", 2, 1),
        ("中国", "zhōng guó rén", 2, 3),
        ("老师", "lǎo", 2, 1)
    ]
    for hz, py, h_c, p_c in mismatches:
        errs, _ = PreRenderValidator.check_pinyin_syllables(hz, py)
        assert len(errs) > 0, f"Mismatch '{hz}' ({py}) [{h_c} vs {p_c}] was not rejected!"
        assert any("không khớp 1:1" in e for e in errs)


def test_stress_pinyin_erhua_variations():
    """All valid Erhua representations must pass, while invalid forms must fail."""
    valid_erhua = [
        ("哪儿", "nǎr"),
        ("哪儿", "nǎ er"),
        ("这儿", "zhèr"),
        ("这儿", "zhè er"),
        ("那儿", "nàr"),
        ("那儿", "nà er"),
        ("玩儿", "wánr"),
        ("玩儿", "wán er"),
        ("花儿", "huār"),
        ("花儿", "huā er"),
        ("一点儿", "yì diǎnr"),
        ("一点儿", "yì diǎn er")
    ]
    for hz, py in valid_erhua:
        errs, norm = PreRenderValidator.check_pinyin_syllables(hz, py)
        assert len(errs) == 0, f"Valid Erhua '{hz}' ({py}) failed: {errs}"

    # Invalid Erhua (e.g. 3 syllables for 2-char Erhua word)
    invalid_erhua = [
        ("哪儿", "nǎr zi"),
        ("这儿", "zhè er zi"),
        ("玩儿", "wán")
    ]
    for hz, py in invalid_erhua:
        errs, _ = PreRenderValidator.check_pinyin_syllables(hz, py)
        assert len(errs) > 0, f"Invalid Erhua '{hz}' ({py}) was unexpectedly accepted!"


# ============================================================================
# 4. PINYIN TONE MARKS & NEUTRAL TONE STRESS TESTS
# ============================================================================

def test_stress_pinyin_missing_tone_marks():
    """Multi-syllable and single content words missing tone marks must be rejected."""
    un_toned_samples = [
        ("电脑", "dian nao"),
        ("苹果", "ping guo"),
        ("水果", "shui guo"),
        ("飞机", "fei ji"),
        ("火车站", "huo che zhan"),
        ("碗", "wan"),
        ("吃", "chi"),
        ("喝", "he")
    ]
    for hz, py in un_toned_samples:
        errs, _ = PreRenderValidator.check_pinyin_syllables(hz, py)
        assert len(errs) > 0, f"Untoned Pinyin '{hz}' ({py}) was not rejected!"
        assert any("thanh điệu" in e for e in errs)


def test_stress_pinyin_valid_neutral_tones():
    """Valid standard neutral tones on particles and suffixes must be accepted."""
    valid_neutral_cases = [
        ("妈妈", "mā ma"),
        ("爸爸", "bà ba"),
        ("爷爷", "yé ye"),
        ("奶奶", "nǎi nai"),
        ("哥哥", "gē ge"),
        ("姐姐", "jiě jie"),
        ("弟弟", "dì di"),
        ("妹妹", "mèi mei"),
        ("桌子", "zhuō zi"),
        ("椅子", "yǐ zi"),
        ("杯子", "bēi zi"),
        ("盘子", "pán zi"),
        ("勺子", "sháo zi"),
        ("我们", "wǒ men"),
        ("你们", "nǐ men"),
        ("他们", "tā men"),
        ("怎么样", "zěn me yàng"),
        ("什么", "shén me"),
        ("朋友", "péng you"),
        ("东西", "dōng xi"),
        ("暖和", "nuǎn huo")
    ]
    for hz, py in valid_neutral_cases:
        errs, norm = PreRenderValidator.check_pinyin_syllables(hz, py)
        assert len(errs) == 0, f"Standard neutral tone '{hz}' ({py}) was falsely rejected: {errs}"


# ============================================================================
# 5. NEGATIVE CONTEXT DEDUPLICATION & OVERLAP STRESS TESTS
# ============================================================================

@pytest.fixture
def sheet_history():
    return {
        "recent_topics": [
            "Gia Đình Thân Yêu",
            "Đồ Dùng Học Tập",
            "Phương Tiện Giao Thông",
            "Thời Tiết Bốn Mùa"
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
            },
            {
                "id": "4",
                "topic": "Phương Tiện Giao Thông",
                "words": ["飞机", "火车", "出租车", "公共汽车", "自行车"]
            }
        ]
    }


def test_stress_topic_duplicate_variations(sheet_history):
    """Normalized variations of past topics must be strictly rejected."""
    duplicate_topic_variations = [
        "Gia Đình Thân Yêu",
        "gia đình thân yêu",
        "HSK 1 • Gia Đình Thân Yêu",
        "HSK 1 - Gia Đình Thân Yêu",
        "HSK 1: Gia Đình Thân Yêu",
        "HSK 2 / Gia Đình Thân Yêu",
        "Đồ Dùng Học Tập",
        "HSK 1 • Đồ Dùng Học Tập",
        "Phương Tiện Giao Thông",
        "hsk 2 • phương tiện giao thông"
    ]
    for top in duplicate_topic_variations:
        candidate = {
            "topic": top,
            "words": [
                {"hanzi": "碗", "pinyin": "wǎn", "meaning": "Bát / Chén"},
                {"hanzi": "盘子", "pinyin": "pán zi", "meaning": "Cái đĩa"},
                {"hanzi": "筷子", "pinyin": "kuài zi", "meaning": "Đôi đũa"},
                {"hanzi": "勺子", "pinyin": "sháo zi", "meaning": "Cái thìa"},
                {"hanzi": "锅", "pinyin": "guō", "meaning": "Cái nồi"}
            ]
        }
        errs = PreRenderValidator.validate_against_history(candidate, history=sheet_history)
        assert len(errs) > 0, f"Topic variation '{top}' was not rejected against history!"
        assert any("trùng lặp với chủ đề đã có" in e for e in errs)


def test_stress_word_overlap_thresholds(sheet_history):
    """Verify >= 2 word overlap is rejected and <= 1 word overlap is approved."""
    # 2 words overlap with Row 2 ("爸爸", "妈妈")
    cand_2_overlap = {
        "topic": "Những Người Quen",
        "words": [
            {"hanzi": "爸爸", "pinyin": "bà ba", "meaning": "Bố / Ba"},
            {"hanzi": "妈妈", "pinyin": "mā ma", "meaning": "Mẹ"},
            {"hanzi": "老师", "pinyin": "lǎo shī", "meaning": "Thầy giáo"},
            {"hanzi": "学生", "pinyin": "xué sheng", "meaning": "Học sinh"},
            {"hanzi": "医生", "pinyin": "yī shēng", "meaning": "Bác sĩ"}
        ]
    }
    errs_2 = PreRenderValidator.validate_against_history(cand_2_overlap, history=sheet_history)
    assert len(errs_2) > 0, "2-word overlap with Row 2 was not rejected!"
    assert any("Trùng lặp cặp 2 từ" in e and "#2" in e for e in errs_2)

    # 3 words overlap with Row 4 ("飞机", "火车", "出租车")
    cand_3_overlap = {
        "topic": "Đi Du Lịch Xa",
        "words": [
            {"hanzi": "飞机", "pinyin": "fēi jī", "meaning": "Máy bay"},
            {"hanzi": "火车", "pinyin": "huǒ chē", "meaning": "Tàu hỏa"},
            {"hanzi": "出租车", "pinyin": "chū zū chē", "meaning": "Xe taxi"},
            {"hanzi": "宾馆", "pinyin": "bīn guǎn", "meaning": "Khách sạn"},
            {"hanzi": "行李", "pinyin": "xíng li", "meaning": "Hành lý"}
        ]
    }
    errs_3 = PreRenderValidator.validate_against_history(cand_3_overlap, history=sheet_history)
    assert len(errs_3) > 0, "3-word overlap with Row 4 was not rejected!"
    assert any("Trùng lặp cặp 3 từ" in e and "#4" in e for e in errs_3)

    # 1 word overlap with Row 2 ("爸爸" only, review word) under a new topic
    cand_1_overlap = {
        "topic": "Người Thân Trong Gia Đình Lớn",
        "words": [
            {"hanzi": "爸爸", "pinyin": "bà ba", "meaning": "Bố / Ba"},  # 1 overlap
            {"hanzi": "爷爷", "pinyin": "yé ye", "meaning": "Ông nội"},
            {"hanzi": "奶奶", "pinyin": "nǎi nai", "meaning": "Bà nội"},
            {"hanzi": "叔叔", "pinyin": "shū shu", "meaning": "Chú / Bác"},
            {"hanzi": "阿姨", "pinyin": "ā yí", "meaning": "Dì / Cô"}
        ]
    }
    errs_1 = PreRenderValidator.validate_against_history(cand_1_overlap, history=sheet_history)
    assert len(errs_1) == 0, f"1-word reuse was unexpectedly rejected: {errs_1}"


# ============================================================================
# 6. FULL VALID FRESH HSK CANDIDATES APPROVAL TESTS
# ============================================================================

def test_full_valid_candidates_approved(sheet_history):
    """Fresh candidate batches with clean Simplified Hanzi, Pinyin tones, and Vietnamese meanings must pass with 0 errors."""
    valid_batches = [
        {
            "topic": "Đồ Dùng Nhà Bếp",
            "level": "HSK 1",
            "words": [
                {"hanzi": "碗", "pinyin": "wǎn", "meaning": "Bát / Chén"},
                {"hanzi": "盘子", "pinyin": "pán zi", "meaning": "Cái đĩa"},
                {"hanzi": "筷子", "pinyin": "kuài zi", "meaning": "Đôi đũa"},
                {"hanzi": "勺子", "pinyin": "sháo zi", "meaning": "Cái thìa / Muỗng"},
                {"hanzi": "锅", "pinyin": "guō", "meaning": "Cái nồi / Chảo"}
            ]
        },
        {
            "topic": "Rau Củ Quả Tươi",
            "level": "HSK 2",
            "words": [
                {"hanzi": "黄瓜", "pinyin": "huáng guā", "meaning": "Dưa chuột / Dưa leo"},
                {"hanzi": "西红柿", "pinyin": "xī hóng shì", "meaning": "Cà chua"},
                {"hanzi": "土豆", "pinyin": "tǔ dòu", "meaning": "Khoai tây"},
                {"hanzi": "胡萝卜", "pinyin": "hú luó bo", "meaning": "Cà rốt"},
                {"hanzi": "白菜", "pinyin": "bái cài", "meaning": "Rau cải thảo"}
            ]
        },
        {
            "topic": "Động Vật Quanh Ta",
            "level": "HSK 1",
            "words": [
                {"hanzi": "小狗", "pinyin": "xiǎo gǒu", "meaning": "Chó con"},
                {"hanzi": "小猫", "pinyin": "xiǎo māo", "meaning": "Mèo con"},
                {"hanzi": "小鸟", "pinyin": "xiǎo niǎo", "meaning": "Chim non"},
                {"hanzi": "兔子", "pinyin": "tù zi", "meaning": "Con thỏ"},
                {"hanzi": "小鱼", "pinyin": "xiǎo yú", "meaning": "Cá nhỏ"}
            ]
        },
        {
            "topic": "Cảm Xúc & Tâm Trạng",
            "level": "HSK 2",
            "words": [
                {"hanzi": "高兴", "pinyin": "gāo xìng", "meaning": "Vui mừng"},
                {"hanzi": "难过", "pinyin": "nán guò", "meaning": "Buồn bã"},
                {"hanzi": "生气", "pinyin": "shēng qì", "meaning": "Tức giận"},
                {"hanzi": "害怕", "pinyin": "hài pà", "meaning": "Sợ hãi"},
                {"hanzi": "担心", "pinyin": "dān xīn", "meaning": "Lo lắng"}
            ]
        }
    ]

    for batch in valid_batches:
        is_valid, errors = PreRenderValidator.validate_batch(batch, history=sheet_history)
        assert is_valid, f"Expected batch '{batch['topic']}' to pass, got errors: {errors}"
        assert len(errors) == 0

import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from multilevelsquiz.src.pre_render_validator import PreRenderValidator

@pytest.fixture
def validator():
    return PreRenderValidator()

def test_valid_multilevels_batch(validator):
    valid_batch = {
        "topic_id": "QUIZ_HSK_001",
        "concept_name_vi": "Tức giận / Nổi cáu",
        "hook_title": "5 cấp độ 'Tức Giận' trong tiếng Trung - Bạn ở HSK mấy?",
        "levels": [
            {
                "level": 1,
                "time_range": "00:00 - 00:05",
                "hanzi": "不高兴",
                "pinyin": "bù gāo xìng",
                "han_viet": "Bất cao hứng",
                "meaning_vi": "Không vui / Khó chịu",
                "nuance_note": "Mức độ nhẹ nhất, thể hiện sự không bằng lòng.",
                "visual_action": "Mặt phụng phịu, khoanh tay."
            },
            {
                "level": 2,
                "time_range": "00:05 - 00:10",
                "hanzi": "生气",
                "pinyin": "shēng qì",
                "han_viet": "Sinh khí",
                "meaning_vi": "Giận dỗi / Tức giận",
                "nuance_note": "Từ phổ biến nhất trong giao tiếp hằng ngày.",
                "visual_action": "Chống nạnh, lông mày nhíu lại."
            },
            {
                "level": 3,
                "time_range": "00:10 - 00:15",
                "hanzi": "发脾气",
                "pinyin": "fā pí qi",
                "han_viet": "Phát tì khí",
                "meaning_vi": "Nổi nóng / Cáu gắt",
                "nuance_note": "Hành động bộc phát cơn giận ra ngoài.",
                "visual_action": "Gõ bàn hoặc vung tay thể hiện sự mất bình tĩnh."
            },
            {
                "level": 4,
                "time_range": "00:15 - 00:20",
                "hanzi": "愤怒",
                "pinyin": "fèn nù",
                "han_viet": "Phẫn nộ",
                "meaning_vi": "Phẫn nộ / Giận dữ",
                "nuance_note": "Sắc thái mạnh, thường dùng khi bị xúc phạm hoặc bất công.",
                "visual_action": "Nghiến răng, mắt trừng to, hiệu ứng viền lửa đỏ quanh người."
            },
            {
                "level": 5,
                "time_range": "00:20 - 00:25",
                "hanzi": "大发雷霆",
                "pinyin": "dà fā léi tíng",
                "han_viet": "Đại phát lôi đình",
                "meaning_vi": "Nổi trận lôi đình",
                "nuance_note": "Thành ngữ biểu thị cơn thịnh nộ cực điểm.",
                "visual_action": "Biểu cảm thảng thốt/uy quyền, chèn hiệu ứng sấm sét chớp nháy."
            }
        ],
        "cta_text": "Từ HSK 5 bạn có biết không? Comment mốc điểm bạn vượt qua nhé!"
    }

    valid, errors = validator.validate_batch(valid_batch)
    assert valid is True, f"Validation failed with errors: {errors}"
    assert len(errors) == 0

def test_negative_context_deduplication(validator):
    existing_concepts = [
        "Tức giận / Nổi cáu",
        "Buồn bã / Thất vọng",
        "Vui mừng / Phấn khởi"
    ]

    duplicate_batch = {
        "concept_name_vi": "Tức giận / Nổi cáu",
        "levels": [
            {"level": 1, "hanzi": "不高兴", "pinyin": "bù gāo xìng", "han_viet": "Bất cao hứng", "meaning_vi": "Không vui"},
            {"level": 2, "hanzi": "生气", "pinyin": "shēng qì", "han_viet": "Sinh khí", "meaning_vi": "Tức giận"},
            {"level": 3, "hanzi": "发脾气", "pinyin": "fā pí qi", "han_viet": "Phát tì khí", "meaning_vi": "Nổi nóng"},
            {"level": 4, "hanzi": "愤怒", "pinyin": "fèn nù", "han_viet": "Phẫn nộ", "meaning_vi": "Phẫn nộ"},
            {"level": 5, "hanzi": "大发雷霆", "pinyin": "dà fā léi tíng", "han_viet": "Đại phát lôi đình", "meaning_vi": "Nổi trận lôi đình"}
        ]
    }

    valid, errors = validator.validate_batch(duplicate_batch, existing_concepts=existing_concepts)
    assert valid is False
    assert any("trùng lặp" in e for e in errors)

def test_reject_overly_long_vietnamese_meaning(validator):
    long_meaning_batch = {
        "concept_name_vi": "Lo lắng",
        "levels": [
            {"level": 1, "hanzi": "担心", "pinyin": "dān xīn", "han_viet": "Đan tâm", "meaning_vi": "Cảm thấy rất lo lắng bồn chồn không yên một chút nào cả vì sợ trễ giờ"},
            {"level": 2, "hanzi": "发愁", "pinyin": "fā chóu", "han_viet": "Phát sầu", "meaning_vi": "Rầu rĩ lo âu"},
            {"level": 3, "hanzi": "焦虑", "pinyin": "jiāo lǜ", "han_viet": "Tiêu lự", "meaning_vi": "Lo âu sốt ruột"},
            {"level": 4, "hanzi": "惶恐", "pinyin": "huáng kǒng", "han_viet": "Hoàng khủng", "meaning_vi": "Hoang mang lo sợ"},
            {"level": 5, "hanzi": "提心吊胆", "pinyin": "tí xīn diào dǎn", "han_viet": "Đề tâm điếu đảm", "meaning_vi": "Thấp thỏm lo âu"}
        ]
    }
    valid, errors = validator.validate_batch(long_meaning_batch)
    assert valid is False
    assert any("quá dài" in e or "quá nhiều từ" in e for e in errors)

def test_reject_traditional_chinese(validator):
    trad_batch = {
        "concept_name_vi": "Nói chuyện",
        "levels": [
            {"level": 1, "hanzi": "說話", "pinyin": "shuō huà", "han_viet": "Thuyết thoại", "meaning_vi": "Nói chuyện"},
            {"level": 2, "hanzi": "聊天", "pinyin": "liáo tiān", "han_viet": "Liêu thiên", "meaning_vi": "Tán gẫu"},
            {"level": 3, "hanzi": "讨论", "pinyin": "tǎo lùn", "han_viet": "Thảo luận", "meaning_vi": "Thảo luận"},
            {"level": 4, "hanzi": "交谈", "pinyin": "jiāo tán", "han_viet": "Giao đàm", "meaning_vi": "Trò chuyện"},
            {"level": 5, "hanzi": "高谈阔论", "pinyin": "gāo tán kuò lùn", "han_viet": "Cao đàm khoát luận", "meaning_vi": "Bàn luận sôi nổi"}
        ]
    }
    valid, errors = validator.validate_batch(trad_batch)
    assert valid is False
    assert any("phồn thể" in e for e in errors)

def test_reject_forbidden_english(validator):
    eng_batch = {
        "concept_name_vi": "Đồ ăn",
        "levels": [
            {"level": 1, "hanzi": "米饭", "pinyin": "mǐ fàn", "han_viet": "Mễ phạn", "meaning_vi": "eat rice"},
            {"level": 2, "hanzi": "面条", "pinyin": "miàn tiáo", "han_viet": "Diện điều", "meaning_vi": "Mì sợi"},
            {"level": 3, "hanzi": "面包", "pinyin": "miàn bāo", "han_viet": "Diện bao", "meaning_vi": "Bánh mì"},
            {"level": 4, "hanzi": "佳肴", "pinyin": "jiā yáo", "han_viet": "Giai hào", "meaning_vi": "Món ngon"},
            {"level": 5, "hanzi": "珍馐美馔", "pinyin": "zhēn xiū měi zhuàn", "han_viet": "Trân tu mỹ soạn", "meaning_vi": "Sơn hào hải vị"}
        ]
    }
    valid, errors = validator.validate_batch(eng_batch)
    assert valid is False
    assert any("tiếng Anh bị cấm" in e for e in errors)

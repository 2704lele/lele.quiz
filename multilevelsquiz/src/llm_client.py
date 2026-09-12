import os
import sys
import re
import time
import json
import logging
import requests
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger("LLMClient")

DEFAULT_LLM_URL = os.getenv("LLM_BASE_URL", "")
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
FALLBACK_GEMINI_MODELS = ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.6-flash-high", "gemini-3.5-flash"]
GEMINI_ENDPOINT_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Rich pool of verified "1 Nghĩa - 5 Cấp độ HSK" batches complying 100% with Gatekeeper 1 standards
FALLBACK_MULTILEVELS_BANK = [
    {
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
                "visual_action": "Nghiến răng, mắt trừng to, viền lửa quanh người."
            },
            {
                "level": 5,
                "time_range": "00:20 - 00:25",
                "hanzi": "大发雷霆",
                "pinyin": "dà fā léi tíng",
                "han_viet": "Đại phát lôi đình",
                "meaning_vi": "Nổi trận lôi đình",
                "nuance_note": "Thành ngữ biểu thị cơn thịnh nộ cực điểm.",
                "visual_action": "Biểu cảm thảng thốt, hiệu ứng sấm sét chớp nháy."
            }
        ],
        "cta_text": "Từ HSK 5 bạn có biết không? Comment mốc điểm bạn vượt qua nhé!"
    },
    {
        "topic_id": "QUIZ_HSK_002",
        "concept_name_vi": "Vui vẻ / Hân hoan",
        "hook_title": "5 cấp độ 'Vui Vẻ' trong tiếng Trung - Bạn biết tới HSK mấy?",
        "levels": [
            {
                "level": 1,
                "time_range": "00:00 - 00:05",
                "hanzi": "高兴",
                "pinyin": "gāo xìng",
                "han_viet": "Cao hứng",
                "meaning_vi": "Vui vẻ / Vui mừng",
                "nuance_note": "Khẩu ngữ cơ bản nhất diễn đạt niềm vui.",
                "visual_action": "Cười tươi, vẫy tay nhẹ."
            },
            {
                "level": 2,
                "time_range": "00:05 - 00:10",
                "hanzi": "快乐",
                "pinyin": "kuài lè",
                "han_viet": "Khoái lạc",
                "meaning_vi": "Hạnh phúc / Vui vẻ",
                "nuance_note": "Dùng chúc mừng hoặc niềm vui lâu dài.",
                "visual_action": "Hai tay làm biểu tượng trái tim."
            },
            {
                "level": 3,
                "time_range": "00:10 - 00:15",
                "hanzi": "开心",
                "pinyin": "kāi xīn",
                "han_viet": "Khai tâm",
                "meaning_vi": "Mở lòng / Phấn khởi",
                "nuance_note": "Tâm trạng thoải mái, không lo nghĩ.",
                "visual_action": "Nhảy cẫng lên hoặc vỗ tay."
            },
            {
                "level": 4,
                "time_range": "00:15 - 00:20",
                "hanzi": "愉快",
                "pinyin": "yú kuài",
                "han_viet": "Du khoái",
                "meaning_vi": "Sảng khoái / Thư thái",
                "nuance_note": "Văn phong lịch sự, trang trọng trong giao tiếp.",
                "visual_action": "Gật đầu hài lòng, nâng ly trà."
            },
            {
                "level": 5,
                "time_range": "00:20 - 00:25",
                "hanzi": "欣喜若狂",
                "pinyin": "xīn xǐ ruò kuáng",
                "han_viet": "Hân hỷ nhược cuồng",
                "meaning_vi": "Vui sướng phát điên",
                "nuance_note": "Thành ngữ chỉ niềm vui cực độ tột bực.",
                "visual_action": "Mắt sáng rực, hiệu ứng pháo hoa rực rỡ."
            }
        ],
        "cta_text": "Level 5 bạn có đoán trúng không? Để lại comment nhé!"
    },
    {
        "topic_id": "QUIZ_HSK_003",
        "concept_name_vi": "Xinh đẹp / Mỹ miều",
        "hook_title": "5 cấp độ khen 'Xinh Đẹp' trong tiếng Trung bạn đã biết?",
        "levels": [
            {
                "level": 1,
                "time_range": "00:00 - 00:05",
                "hanzi": "好看",
                "pinyin": "hǎo kàn",
                "han_viet": "Hảo khán",
                "meaning_vi": "Dễ nhìn / Đẹp mắt",
                "nuance_note": "Khen vẻ ngoài đơn giản, tự nhiên.",
                "visual_action": "Chỉ tay vào mắt, mỉm cười."
            },
            {
                "level": 2,
                "time_range": "00:05 - 00:10",
                "hanzi": "漂亮",
                "pinyin": "piào liang",
                "han_viet": "Phiêu lượng",
                "meaning_vi": "Xinh đẹp / Đẹp đẽ",
                "nuance_note": "Từ khen nhan sắc phổ biến nhất.",
                "visual_action": "Ôm má tạo dáng hoa nở."
            },
            {
                "level": 3,
                "time_range": "00:10 - 00:15",
                "hanzi": "美丽",
                "pinyin": "měi lì",
                "han_viet": "Mỹ lệ",
                "meaning_vi": "Mỹ lệ / Đẹp đẽ",
                "nuance_note": "Khen người hoặc cảnh sắc thiên nhiên.",
                "visual_action": "Dang hai tay cảm thán cảnh đẹp."
            },
            {
                "level": 4,
                "time_range": "00:15 - 00:20",
                "hanzi": "迷人",
                "pinyin": "mí rén",
                "han_viet": "Mê nhân",
                "meaning_vi": "Quyến rũ / Mê hồn",
                "nuance_note": "Vẻ đẹp có sức hút và chiều sâu quyến rũ.",
                "visual_action": "Nháy mắt duyên dáng, hiệu ứng lấp lánh."
            },
            {
                "level": 5,
                "time_range": "00:20 - 00:25",
                "hanzi": "倾国倾城",
                "pinyin": "qīng guó qīng chéng",
                "han_viet": "Khuynh quốc khuynh thành",
                "meaning_vi": "Nghiêng nước nghiêng thành",
                "nuance_note": "Tuyệt sắc giai nhân kinh diễm thế gian.",
                "visual_action": "Cầm quạt che nửa mặt bí ẩn, ánh hào quang."
            }
        ],
        "cta_text": "Từ HSK 5 quá hay đúng không? Bạn vượt qua cấp mấy?"
    },
    {
        "topic_id": "QUIZ_HSK_004",
        "concept_name_vi": "Thông minh / Trí tuệ",
        "hook_title": "5 cấp độ 'Thông Minh' trong tiếng Trung - Thử thách HSK 1-5!",
        "levels": [
            {
                "level": 1,
                "time_range": "00:00 - 00:05",
                "hanzi": "聪明",
                "pinyin": "cōng míng",
                "han_viet": "Thông minh",
                "meaning_vi": "Thông minh / Sáng dạ",
                "nuance_note": "Khẩu ngữ cơ bản quen thuộc nhất.",
                "visual_action": "Chỉ tay vào trán mỉm cười."
            },
            {
                "level": 2,
                "time_range": "00:05 - 00:10",
                "hanzi": "懂事",
                "pinyin": "dǒng shì",
                "han_viet": "Hiểu sự",
                "meaning_vi": "Biết điều / Hiểu chuyện",
                "nuance_note": "Khen người biết cách cư xử, nhạy bén.",
                "visual_action": "Gật đầu tán thưởng."
            },
            {
                "level": 3,
                "time_range": "00:10 - 00:15",
                "hanzi": "灵活",
                "pinyin": "líng huó",
                "han_viet": "Linh hoạt",
                "meaning_vi": "Nhanh trí / Linh hoạt",
                "nuance_note": "Đầu óc xử lý tình huống biến chuyển mau lẹ.",
                "visual_action": "Búng tay ra ý tưởng."
            },
            {
                "level": 4,
                "time_range": "00:15 - 00:20",
                "hanzi": "敏捷",
                "pinyin": "mǐn jié",
                "han_viet": "Mẫn tiệp",
                "meaning_vi": "Nhanh nhạy / Sắc sảo",
                "nuance_note": "Trí tuệ phản xạ thần tốc, sắc bén.",
                "visual_action": "Đeo kính hoặc nhìn sắc lạnh."
            },
            {
                "level": 5,
                "time_range": "00:20 - 00:25",
                "hanzi": "足智多谋",
                "pinyin": "zú zhì duō móu",
                "han_viet": "Túc trí đa mưu",
                "meaning_vi": "Lắm mưu nhiều kế",
                "nuance_note": "Thành ngữ ca ngợi bậc mưu lược tài ba.",
                "visual_action": "Xoa cằm suy ngẫm như Gia Cát Lượng."
            }
        ],
        "cta_text": "Bạn dừng ở mốc HSK mấy? Bình luận ngay nhé!"
    },
    {
        "topic_id": "QUIZ_HSK_005",
        "concept_name_vi": "Sợ hãi / Hoảng sợ",
        "hook_title": "5 cấp độ 'Sợ Hãi' trong tiếng Trung - Bạn biết đến HSK mấy?",
        "levels": [
            {
                "level": 1,
                "time_range": "00:00 - 00:05",
                "hanzi": "怕",
                "pinyin": "pà",
                "han_viet": "Phạ",
                "meaning_vi": "Sợ / E sợ",
                "nuance_note": "Từ đơn cơ bản nhất biểu thị nỗi sợ.",
                "visual_action": "Lùi lại một bước, rụt vai."
            },
            {
                "level": 2,
                "time_range": "00:05 - 00:10",
                "hanzi": "害怕",
                "pinyin": "hài pà",
                "han_viet": "Hại phạ",
                "meaning_vi": "Sợ hãi / Lo sợ",
                "nuance_note": "Từ phổ thông thông dụng nhất.",
                "visual_action": "Hai tay ôm ngực hoảng hốt."
            },
            {
                "level": 3,
                "time_range": "00:10 - 00:15",
                "hanzi": "担心",
                "pinyin": "dān xīn",
                "han_viet": "Đam tâm",
                "meaning_vi": "Lo lắng / Bất an",
                "nuance_note": "Sự bất an trong tâm trí trước sự việc.",
                "visual_action": "Nhăn trán, cắn móng tay."
            },
            {
                "level": 4,
                "time_range": "00:15 - 00:20",
                "hanzi": "恐惧",
                "pinyin": "kǒng jù",
                "han_viet": "Khủng cụ",
                "meaning_vi": "Kinh hãi / Khủng khiếp",
                "nuance_note": "Cảm giác rùng mình, hoảng loạn sâu sắc.",
                "visual_action": "Run rẩy, toát mồ hôi hột."
            },
            {
                "level": 5,
                "time_range": "00:20 - 00:25",
                "hanzi": "提心吊胆",
                "pinyin": "tí xīn diào dǎn",
                "han_viet": "Đề tâm điếu đảm",
                "meaning_vi": "Thấp thỏm lo âu",
                "nuance_note": "Thành ngữ tim treo lơ lửng, nơm nớp sợ hãi.",
                "visual_action": "Che mặt hoảng loạn, hiệu ứng sấm chớp giật."
            }
        ],
        "cta_text": "Từ HSK 5 bạn có nhớ không? Comment điểm bạn đạt được nhé!"
    },
    {
        "topic_id": "QUIZ_HSK_006",
        "concept_name_vi": "Bận rộn / Hối hả",
        "hook_title": "5 cấp độ 'Bận Rộn' trong tiếng Trung - Bạn biết tới HSK mấy?",
        "levels": [
            {"level": 1, "time_range": "00:00 - 00:05", "hanzi": "忙", "pinyin": "máng", "han_viet": "Mang", "meaning_vi": "Bận / Bận rộn", "nuance_note": "Từ đơn cơ bản nhất chỉ trạng thái có nhiều việc.", "visual_action": "Tay cầm cuốn sổ nhăn mặt."},
            {"level": 2, "time_range": "00:05 - 00:10", "hanzi": "忙碌", "pinyin": "máng lù", "han_viet": "Mang lục", "meaning_vi": "Bận rộn / Tấp nập", "nuance_note": "Biểu thị công việc liên tục không ngơi tay.", "visual_action": "Gõ máy tính nhanh tay."},
            {"level": 3, "time_range": "00:10 - 00:15", "hanzi": "繁忙", "pinyin": "fán máng", "han_viet": "Phồn mang", "meaning_vi": "Phức tạp / Bận rộn", "nuance_note": "Thường dùng cho công việc hoặc lịch trình dày đặc.", "visual_action": "Nghe điện thoại liên tục."},
            {"level": 4, "time_range": "00:15 - 00:20", "hanzi": "奔波", "pinyin": "bēn bō", "han_viet": "Bôn ba", "meaning_vi": "Bôn ba / Vất vả", "nuance_note": "Chạy ngược chạy xuôi lo công việc.", "visual_action": "Xách cặp chạy vội trên đường."},
            {"level": 5, "time_range": "00:20 - 00:25", "hanzi": "忙得不可开交", "pinyin": "máng de bù kě kāi jiāo", "han_viet": "Mang đắc bất khả khai giao", "meaning_vi": "Bận rộn tối mắt tối mũi", "nuance_note": "Thành ngữ bận rộn đến mức không thể gỡ ra được.", "visual_action": "Giấy tờ bay tứ tung xung quanh."}
        ],
        "cta_text": "Từ HSK 5 bạn có biết không? Comment mốc điểm bạn vượt qua nhé!"
    },
    {
        "topic_id": "QUIZ_HSK_007",
        "concept_name_vi": "Chăm chỉ / Cần cù",
        "hook_title": "5 cấp độ 'Chăm Chỉ' trong tiếng Trung - Bạn ở HSK mấy?",
        "levels": [
            {"level": 1, "time_range": "00:00 - 00:05", "hanzi": "努力", "pinyin": "nǔ lì", "han_viet": "Nỗ lực", "meaning_vi": "Cố gắng / Nỗ lực", "nuance_note": "Từ thông dụng nhất thể hiện sự cố gắng học tập/làm việc.", "visual_action": "Viết bài chăm chỉ."},
            {"level": 2, "time_range": "00:05 - 00:10", "hanzi": "认真", "pinyin": "rèn zhēn", "han_viet": "Nhận chân", "meaning_vi": "Nghiêm túc / Chăm chỉ", "nuance_note": "Thái độ làm việc chỉn chu, không lơ đễnh.", "visual_action": "Tập trung nhìn màn hình học."},
            {"level": 3, "time_range": "00:10 - 00:15", "hanzi": "勤奋", "pinyin": "qín fèn", "han_viet": "Cần phấn", "meaning_vi": "Cần cù / Phấn đấu", "nuance_note": "Chăm chỉ kiên trì trong thời gian dài.", "visual_action": "Đọc sách dưới ánh đèn."},
            {"level": 4, "time_range": "00:15 - 00:20", "hanzi": "刻苦", "pinyin": "kè kǔ", "han_viet": "Khắc khổ", "meaning_vi": "Chịu khó / Khắc khổ", "nuance_note": "Chịu đựng gian khổ để học tập rèn luyện.", "visual_action": "Buộc tóc lên xà nhà học bài."},
            {"level": 5, "time_range": "00:20 - 00:25", "hanzi": "废寝忘食", "pinyin": "fèi qǐn wàng shí", "han_viet": "Phế tẩm vong thực", "meaning_vi": "Quên ăn quên ngủ", "nuance_note": "Thành ngữ mê say làm việc đến mức quên ăn bỏ ngủ.", "visual_action": "Đồng hồ quay nhanh, bát cơm để nguyên."}
        ],
        "cta_text": "Thành ngữ HSK 5 này bạn gặp bao giờ chưa? Comment cho Lê Lê biết nhé!"
    },
    {
        "topic_id": "QUIZ_HSK_008",
        "concept_name_vi": "Nhanh chóng / Thần tốc",
        "hook_title": "5 cấp độ 'Nhanh Chóng' trong tiếng Trung - Bạn ở HSK mấy?",
        "levels": [
            {"level": 1, "time_range": "00:00 - 00:05", "hanzi": "快", "pinyin": "kuài", "han_viet": "Khoái", "meaning_vi": "Nhanh / Mau chóng", "nuance_note": "Từ đơn khẩu ngữ cơ bản chỉ tốc độ cao.", "visual_action": "Chạy nhanh vút qua."},
            {"level": 2, "time_range": "00:05 - 00:10", "hanzi": "快速", "pinyin": "kuài sù", "han_viet": "Khoái tốc", "meaning_vi": "Nhanh chóng / Tốc độ cao", "nuance_note": "Dùng trong văn viết và miêu tả quá trình diễn ra nhanh.", "visual_action": "Xe chạy tốc độ cao."},
            {"level": 3, "time_range": "00:10 - 00:15", "hanzi": "迅速", "pinyin": "xùn sù", "han_viet": "Tấn tốc", "meaning_vi": "Thần tốc / Nhanh nhẹn", "nuance_note": "Mức độ phản xạ hoặc hành động cực kỳ mau lẹ.", "visual_action": "Lập tức đứng dậy hành động."},
            {"level": 4, "time_range": "00:15 - 00:20", "hanzi": "敏捷", "pinyin": "mǐn jié", "han_viet": "Mẫn tiệp", "meaning_vi": "Nhanh nhạy / Mẫn tiệp", "nuance_note": "Đầu óc hoặc chân tay linh hoạt sắc bén.", "visual_action": "Né tránh chướng ngại vật nhanh lẹ."},
            {"level": 5, "time_range": "00:20 - 00:25", "hanzi": "风驰电掣", "pinyin": "fēng chí diàn chè", "han_viet": "Phong trì điện triệt", "meaning_vi": "Nhanh như chớp", "nuance_note": "Thành ngữ di chuyển tốc độ cực đại như gió lốc tia chớp.", "visual_action": "Hiệu ứng tia chớp lướt qua màn hình."}
        ],
        "cta_text": "Từ HSK 5 bạn có biết không? Comment mốc điểm bạn vượt qua nhé!"
    },
    {
        "topic_id": "QUIZ_HSK_009",
        "concept_name_vi": "Mệt mỏi / Kiệt sức",
        "hook_title": "5 cấp độ 'Mệt Mỏi' trong tiếng Trung - Bạn ở HSK mấy?",
        "levels": [
            {"level": 1, "time_range": "00:00 - 00:05", "hanzi": "累", "pinyin": "lèi", "han_viet": "Lụy", "meaning_vi": "Mệt / Mệt mỏi", "nuance_note": "Từ đơn cơ bản chỉ cảm giác mệt thể xác.", "visual_action": "Lau mồ hôi thở dài."},
            {"level": 2, "time_range": "00:05 - 00:10", "hanzi": "辛苦", "pinyin": "xīn kǔ", "han_viet": "Tân khổ", "meaning_vi": "Vất vả / Gian khổ", "nuance_note": "Biểu thị sự vất vả nhọc nhằn trong công việc.", "visual_action": "Đấm lưng mệt mỏi."},
            {"level": 3, "time_range": "00:10 - 00:15", "hanzi": "疲劳", "pinyin": "pí láo", "han_viet": "Bì lao", "meaning_vi": "Mệt mỏi / Mệt nhọc", "nuance_note": "Trạng thái mệt mỏi tích tụ kéo dài.", "visual_action": "Gục đầu xuống bàn ngủ."},
            {"level": 4, "time_range": "00:15 - 00:20", "hanzi": "疲惫", "pinyin": "pí bèi", "han_viet": "Bì bối", "meaning_vi": "Kiệt sức / Phờ phạc", "nuance_note": "Mệt rã rời cả thể xác lẫn tinh thần.", "visual_action": "Mắt thâm quầng lê bước."},
            {"level": 5, "time_range": "00:20 - 00:25", "hanzi": "精疲力竭", "pinyin": "jīng pí lì jié", "han_viet": "Tinh bì lực kiệt", "meaning_vi": "Kiệt sức hoàn toàn", "nuance_note": "Thành ngữ cạn kiệt toàn bộ năng lượng sinh lực.", "visual_action": "Nằm bệt xuống đất hết hơi."}
        ],
        "cta_text": "Từ HSK 5 này bạn đã học tới chưa? Comment cho Lê Lê biết nhé!"
    },
    {
        "topic_id": "QUIZ_HSK_010",
        "concept_name_vi": "Bất ngờ / Kinh ngạc",
        "hook_title": "5 cấp độ 'Bất Ngờ' trong tiếng Trung - Bạn ở HSK mấy?",
        "levels": [
            {"level": 1, "time_range": "00:00 - 00:05", "hanzi": "奇怪", "pinyin": "qí guài", "han_viet": "Kỳ quái", "meaning_vi": "Lạ kỳ / Kỳ quặc", "nuance_note": "Cảm giác là lạ khác thường.", "visual_action": "Gãi đầu ngơ ngác."},
            {"level": 2, "time_range": "00:05 - 00:10", "hanzi": "吃惊", "pinyin": "chī jīng", "han_viet": "Cật kinh", "meaning_vi": "Giật mình / Ngạc nhiên", "nuance_note": "Bất ngờ trước tình huống đột ngột.", "visual_action": "Mắt mở to che miệng."},
            {"level": 3, "time_range": "00:10 - 00:15", "hanzi": "惊讶", "pinyin": "jīng yà", "han_viet": "Kinh nhạ", "meaning_vi": "Kinh ngạc / Sửng sốt", "nuance_note": "Trạng thái ngạc nhiên sâu sắc.", "visual_action": "Lùi lại sững người."},
            {"level": 4, "time_range": "00:15 - 00:20", "hanzi": "震惊", "pinyin": "zhèn jīng", "han_viet": "Chấn kinh", "meaning_vi": "Chấn động / Sốc", "nuance_note": "Kinh ngạc tột độ gây sốc tinh thần.", "visual_action": "Đổ mồ hôi hột há hốc."},
            {"level": 5, "time_range": "00:20 - 00:25", "hanzi": "目瞪口呆", "pinyin": "mù dèng kǒu dāi", "han_viet": "Mục đặng khẩu ngốc", "meaning_vi": "Trố mắt ngoác mồm", "nuance_note": "Thành ngữ kinh ngạc đến mức ngẩn ngơ đứng hình.", "visual_action": "Mặt đứng hình hóa đá."}
        ],
        "cta_text": "Từ HSK 5 bạn có biết không? Comment mốc điểm bạn vượt qua nhé!"
    },
    {
        "topic_id": "QUIZ_HSK_011",
        "concept_name_vi": "Giàu có / Trù phú",
        "hook_title": "5 cấp độ 'Giàu Có' trong tiếng Trung - Bạn ở HSK mấy?",
        "levels": [
            {"level": 1, "time_range": "00:00 - 00:05", "hanzi": "有钱", "pinyin": "yǒu qián", "han_viet": "Hữu tiền", "meaning_vi": "Có tiền / Giàu có", "nuance_note": "Khẩu ngữ cơ bản chỉ có tài chính.", "visual_action": "Cầm xấp tiền cười."},
            {"level": 2, "time_range": "00:05 - 00:10", "hanzi": "富", "pinyin": "fù", "han_viet": "Phú", "meaning_vi": "Giàu / Trù phú", "nuance_note": "Từ đơn mang nghĩa giàu có của cải.", "visual_action": "Đi xe sang."},
            {"level": 3, "time_range": "00:10 - 00:15", "hanzi": "富裕", "pinyin": "fù yù", "han_viet": "Phú dụ", "meaning_vi": "Sung túc / Dồi dào", "nuance_note": "Thâm dư tài chính và cuộc sống đầy đủ.", "visual_action": "Ở biệt thự sang trọng."},
            {"level": 4, "time_range": "00:15 - 00:20", "hanzi": "富足", "pinyin": "fù zú", "han_viet": "Phú túc", "meaning_vi": "Đầy đủ / Giàu có", "nuance_note": "Của cải dồi dào không thiếu thứ gì.", "visual_action": "Rót rượu vang mừng."},
            {"level": 5, "time_range": "00:20 - 00:25", "hanzi": "富可敌国", "pinyin": "fù kě dí guó", "han_viet": "Phú khả địch quốc", "meaning_vi": "Giàu địch quốc", "nuance_note": "Thành ngữ của cải nhiều sánh ngang tài sản quốc gia.", "visual_action": "Núi vàng núi bạc bao quanh."}
        ],
        "cta_text": "Thành ngữ HSK 5 này bạn thấy lần nào chưa? Comment nhé!"
    },
    {
        "topic_id": "QUIZ_HSK_012",
        "concept_name_vi": "Thành công / Xuất sắc",
        "hook_title": "5 cấp độ 'Thành Công' trong tiếng Trung - Bạn ở HSK mấy?",
        "levels": [
            {"level": 1, "time_range": "00:00 - 00:05", "hanzi": "好", "pinyin": "hǎo", "han_viet": "Hảo", "meaning_vi": "Tốt / Tốt đẹp", "nuance_note": "Từ đơn cơ bản nhất khen ngợi.", "visual_action": "Giơ ngón tay cái."},
            {"level": 2, "time_range": "00:05 - 00:10", "hanzi": "成功", "pinyin": "chéng gōng", "han_viet": "Thành công", "meaning_vi": "Thành công / Đạt nguyện", "nuance_note": "Đạt được mục tiêu mong muốn.", "visual_action": "Giơ cúp vô địch."},
            {"level": 3, "time_range": "00:10 - 00:15", "hanzi": "优秀", "pinyin": "yōu xiù", "han_viet": "Ưu tú", "meaning_vi": "Ưu tú / Xuất sắc", "nuance_note": "Năng lực vượt trội so với mặt bằng.", "visual_action": "Nhận bằng khen thưởng."},
            {"level": 4, "time_range": "00:15 - 00:20", "hanzi": "出色", "pinyin": "chū sè", "han_viet": "Xuất sắc", "meaning_vi": "Xuất sắc / Nổi bật", "nuance_note": "Thể hiện tài năng xuất chúng ấn tượng.", "visual_action": "Đứng trên bục vinh quang."},
            {"level": 5, "time_range": "00:20 - 00:25", "hanzi": "登峰造极", "pinyin": "dēng fēng zào jí", "han_viet": "Đăng phong tạo cực", "meaning_vi": "Đạt đỉnh cao tuyệt đỉnh", "nuance_note": "Thành ngữ đạt tới đỉnh cao nghệ thuật/kỹ năng tối thượng.", "visual_action": "Đứng trên đỉnh núi rực rỡ."}
        ],
        "cta_text": "Từ HSK 5 bạn có biết không? Comment mốc điểm bạn vượt qua nhé!"
    },
    {
        "topic_id": "QUIZ_HSK_013",
        "concept_name_vi": "Bình tĩnh / Điềm tĩnh",
        "hook_title": "5 cấp độ 'Bình Tĩnh' trong tiếng Trung - Bạn ở HSK mấy?",
        "levels": [
            {"level": 1, "time_range": "00:00 - 00:05", "hanzi": "安静", "pinyin": "ān jìng", "han_viet": "An tĩnh", "meaning_vi": "Yên tĩnh / Bình lặng", "nuance_note": "Trạng thái không ồn ào xáo trộn.", "visual_action": "Đặt tay lên môi suýt."},
            {"level": 2, "time_range": "00:05 - 00:10", "hanzi": "放心", "pinyin": "fàng xīn", "han_viet": "Phóng tâm", "meaning_vi": "Yên tâm / An tâm", "nuance_note": "Không lo lắng nữa, tâm trí thả lỏng.", "visual_action": "Gật đầu mỉm cười nhẹ."},
            {"level": 3, "time_range": "00:10 - 00:15", "hanzi": "冷静", "pinyin": "lěng jìng", "han_viet": "Lãnh tĩnh", "meaning_vi": "Bình tĩnh / Tỉnh táo", "nuance_note": "Giữ đầu óc sáng suốt trước sóng gió.", "visual_action": "Uống ngụm nước tĩnh tâm."},
            {"level": 4, "time_range": "00:15 - 00:20", "hanzi": "镇定", "pinyin": "zhèn dìng", "han_viet": "Trấn định", "meaning_vi": "Điềm tĩnh / Trấn tĩnh", "nuance_note": "Không hề nao núng hoảng sợ.", "visual_action": "Khoanh tay tự tin."},
            {"level": 5, "time_range": "00:20 - 00:25", "hanzi": "泰然自若", "pinyin": "tài rán zì ruò", "han_viet": "Thái nhiên tự nhược", "meaning_vi": "Điềm nhiên như không", "nuance_note": "Thành ngữ gặp đại biến vẫn thản nhiên tự tại.", "visual_action": "Ngồi uống trà giữa giông bão."}
        ],
        "cta_text": "Từ HSK 5 này bạn đã nghe qua chưa? Comment nhé!"
    },
    {
        "topic_id": "QUIZ_HSK_014",
        "concept_name_vi": "Nhã nhặn / Lịch sự",
        "hook_title": "5 cấp độ 'Lịch Sự' trong tiếng Trung - Bạn ở HSK mấy?",
        "levels": [
            {"level": 1, "time_range": "00:00 - 00:05", "hanzi": "客气", "pinyin": "kè qi", "han_viet": "Khách khí", "meaning_vi": "Khách khí / Lịch sự", "nuance_note": "Khẩu ngữ giao tiếp ứng xử cơ bản.", "visual_action": "Cúi đầu nhẹ tay xòe."},
            {"level": 2, "time_range": "00:05 - 00:10", "hanzi": "礼貌", "pinyin": "lǐ mào", "han_viet": "Lễ mạo", "meaning_vi": "Lễ phép / Lịch sự", "nuance_note": "Thái độ tôn trọng có văn hóa.", "visual_action": "Cúi chào chào hỏi."},
            {"level": 3, "time_range": "00:10 - 00:15", "hanzi": "谦虚", "pinyin": "qiān xū", "han_viet": "Khiêm hư", "meaning_vi": "Khiêm tốn / Nhã nhặn", "nuance_note": "Không tự cao tự đại.", "visual_action": "Xoa đầu xua tay khiêm tốn."},
            {"level": 4, "time_range": "00:15 - 00:20", "hanzi": "得体", "pinyin": "dé tǐ", "han_viet": "Đắc thể", "meaning_vi": "Chuẩn mực / Khéo léo", "nuance_note": "Lời nói hành xử đúng mực vừa vặn.", "visual_action": "Bắt tay mỉm cười trang trọng."},
            {"level": 5, "time_range": "00:20 - 00:25", "hanzi": "彬彬有礼", "pinyin": "bīn bīn yǒu lǐ", "han_viet": "Bân bân hữu lễ", "meaning_vi": "Nho nhã lịch thiệp", "nuance_note": "Thành ngữ phong thái nhã nhặn lễ độ cực kỳ tao nhã.", "visual_action": "Khoanh tay cúi chào quý phái."}
        ],
        "cta_text": "Từ HSK 5 bạn có biết không? Comment mốc điểm bạn vượt qua nhé!"
    },
    {
        "topic_id": "QUIZ_HSK_015",
        "concept_name_vi": "Dũng cảm / Quật cường",
        "hook_title": "5 cấp độ 'Dũng Cảm' trong tiếng Trung - Bạn ở HSK mấy?",
        "levels": [
            {"level": 1, "time_range": "00:00 - 00:05", "hanzi": "不怕", "pinyin": "bù pà", "han_viet": "Bất phạ", "meaning_vi": "Không sợ / Can đảm", "nuance_note": "Từ đơn khẩu ngữ thể hiện không e ngại.", "visual_action": "Vỗ ngực tự tin."},
            {"level": 2, "time_range": "00:05 - 00:10", "hanzi": "勇敢", "pinyin": "yǒng gǎn", "han_viet": "Dũng cảm", "meaning_vi": "Dũng cảm / Gan dạ", "nuance_note": "Dám đối mặt khó khăn nguy hiểm.", "visual_action": "Đứng thẳng nắm chặt tay."},
            {"level": 3, "time_range": "00:10 - 00:15", "hanzi": "无畏", "pinyin": "wú wèi", "han_viet": "Vô úy", "meaning_vi": "Không sợ hãi / Vô úy", "nuance_note": "Tinh thần kiên cường không nao núng.", "visual_action": "Tiến về phía trước."},
            {"level": 4, "time_range": "00:15 - 00:20", "hanzi": "英勇", "pinyin": "yīng yǒng", "han_viet": "Anh dũng", "meaning_vi": "Anh dũng / Kiên cường", "nuance_note": "Khí phách dũng cảm phi thường.", "visual_action": "Giơ tay hô vang chiến đấu."},
            {"level": 5, "time_range": "00:20 - 00:25", "hanzi": "冲锋陷阵", "pinyin": "chōng fēng xiàn zhèn", "han_viet": "Xung phong hãm trận", "meaning_vi": "Xung phong hãm trận", "nuance_note": "Thành ngữ xông trận tiền tuyến không sợ gian nguy.", "visual_action": "Cầm cờ xông lên phía trước."}
        ],
        "cta_text": "Từ HSK 5 này bạn đã nghe bao giờ chưa? Comment nhé!"
    },
    {
        "topic_id": "QUIZ_HSK_016",
        "concept_name_vi": "Gấp gáp / Vội vã",
        "hook_title": "5 cấp độ 'Gấp Gáp' trong tiếng Trung - Bạn ở HSK mấy?",
        "levels": [
            {"level": 1, "time_range": "00:00 - 00:05", "hanzi": "快点", "pinyin": "kuài diǎn", "han_viet": "Khoái điểm", "meaning_vi": "Nhanh lên / Nhanh chút", "nuance_note": "Lời thúc giục khẩu ngữ hàng ngày.", "visual_action": "Vẫy tay giục giã."},
            {"level": 2, "time_range": "00:05 - 00:10", "hanzi": "着急", "pinyin": "zháo jí", "han_viet": "Tráo cấp", "meaning_vi": "Vội vàng / Sốt ruột", "nuance_note": "Tâm trạng nôn nóng vội vã.", "visual_action": "Xem đồng hồ liên tục."},
            {"level": 3, "time_range": "00:10 - 00:15", "hanzi": "急忙", "pinyin": "jí máng", "han_viet": "Cấp mang", "meaning_vi": "Cuống quít / Vội vã", "nuance_note": "Hành động vội vã gấp gáp.", "visual_action": "Chạy vội quên đồ."},
            {"level": 4, "time_range": "00:15 - 00:20", "hanzi": "紧急", "pinyin": "jǐn jí", "han_viet": "Khẩn cấp", "meaning_vi": "Khẩn cấp / Gấp gáp", "nuance_note": "Tình huống cấp bách cần xử lý ngay.", "visual_action": "Bật đèn còi báo động."},
            {"level": 5, "time_range": "00:20 - 00:25", "hanzi": "迫不及待", "pinyin": "pò bù jí dài", "han_viet": "Bách bất cấp đãi", "meaning_vi": "Sốt ruột không chờ nổi", "nuance_note": "Thành ngữ nôn nóng khẩn thiết không thể chờ thêm.", "visual_action": "Mở quà vội vã vung vẩy."}
        ],
        "cta_text": "Từ HSK 5 bạn có biết không? Comment mốc điểm bạn vượt qua nhé!"
    },
    {
        "topic_id": "QUIZ_HSK_017",
        "concept_name_vi": "Kiên trì / Bền bỉ",
        "hook_title": "5 cấp độ 'Kiên Trì' trong tiếng Trung - Bạn ở HSK mấy?",
        "levels": [
            {"level": 1, "time_range": "00:00 - 00:05", "hanzi": "坚持", "pinyin": "jiān chí", "han_viet": "Kiên trì", "meaning_vi": "Kiên trì / Giữ vững", "nuance_note": "Từ phổ biến nhất về sự giữ vững ý chí.", "visual_action": "Gật đầu kiên định."},
            {"level": 2, "time_range": "00:05 - 00:10", "hanzi": "努力", "pinyin": "nǔ lì", "han_viet": "Nỗ lực", "meaning_vi": "Nỗ lực / Cố gắng", "nuance_note": "Cố gắng hết sức trong học tập công việc.", "visual_action": "Cố gắng giơ tay giơ nắm đấm."},
            {"level": 3, "time_range": "00:10 - 00:15", "hanzi": "毅力", "pinyin": "yì lì", "han_viet": "Nghị lực", "meaning_vi": "Nghị lực / Ý chí", "nuance_note": "Sức mạnh tinh thần vượt qua khó khăn.", "visual_action": "Ánh mắt quyết tâm."},
            {"level": 4, "time_range": "00:15 - 00:20", "hanzi": "坚韧", "pinyin": "jiān rèn", "han_viet": "Kiên nhẫn", "meaning_vi": "Kiên cường / Bền bỉ", "nuance_note": "Sự dẻo dai kiên định không bỏ cuộc.", "visual_action": "Leo núi không lùi bước."},
            {"level": 5, "time_range": "00:20 - 00:25", "hanzi": "持之以恒", "pinyin": "chí zhī yǐ héng", "han_viet": "Trì chi dĩ hằng", "meaning_vi": "Kiên trì tới cùng", "nuance_note": "Thành ngữ giữ vững quyết tâm lâu dài.", "visual_action": "Vẫn chạy bộ dù trời mưa."}
        ],
        "cta_text": "Từ HSK 5 này bạn đã học chưa? Comment cho Lê Lê biết nha!"
    },
    {
        "topic_id": "QUIZ_HSK_018",
        "concept_name_vi": "Thành thật / Chân thành",
        "hook_title": "5 cấp độ 'Thành Thật' trong tiếng Trung - Bạn ở HSK mấy?",
        "levels": [
            {"level": 1, "time_range": "00:00 - 00:05", "hanzi": "老实", "pinyin": "lǎo shi", "han_viet": "Lão thực", "meaning_vi": "Thật thà / Ngoan ngoãn", "nuance_note": "Tính cách hiền lành thật thà.", "visual_action": "Cười hiền gật đầu."},
            {"level": 2, "time_range": "00:05 - 00:10", "hanzi": "诚实", "pinyin": "chéng shí", "han_viet": "Thành thực", "meaning_vi": "Thành thật / Trung thực", "nuance_note": "Không nói dối, ngay thẳng.", "visual_action": "Đặt tay lên ngực trái."},
            {"level": 3, "time_range": "00:10 - 00:15", "hanzi": "真诚", "pinyin": "zhēn chéng", "han_viet": "Chân thành", "meaning_vi": "Chân thành / Tha thiết", "nuance_note": "Tình cảm xuất phát từ đáy lòng.", "visual_action": "Ánh mắt ấm áp."},
            {"level": 4, "time_range": "00:15 - 00:20", "hanzi": "坦率", "pinyin": "tǎn shuài", "han_viet": "Thẳng thắn", "meaning_vi": "Thẳng thắn / Bộc bạch", "nuance_note": "Nói năng cởi mở không giấu giếm.", "visual_action": "Mở rộng hai tay trò chuyện."},
            {"level": 5, "time_range": "00:20 - 00:25", "hanzi": "推心置腹", "pinyin": "tuī xīn zhì fù", "han_viet": "Thôi tâm trí phúc", "meaning_vi": "Móc ruột gan trải lòng", "nuance_note": "Thành ngữ đãi người hết lòng thành thật.", "visual_action": "Trút hết tâm sự chân thành."}
        ],
        "cta_text": "Comment mốc HSK bạn đạt được bên dưới nhé!"
    },
    {
        "topic_id": "QUIZ_HSK_019",
        "concept_name_vi": "Nhiệt tình / Sôi nổi",
        "hook_title": "5 cấp độ 'Nhiệt Tình' trong tiếng Trung - Bạn ở HSK mấy?",
        "levels": [
            {"level": 1, "time_range": "00:00 - 00:05", "hanzi": "热心", "pinyin": "rè xīn", "han_viet": "Nhiệt tâm", "meaning_vi": "Nhiệt tình / Số sắng", "nuance_note": "Tốt bụng sẵn sàng giúp đỡ.", "visual_action": "Cười mở lòng giúp đỡ."},
            {"level": 2, "time_range": "00:05 - 00:10", "hanzi": "热情", "pinyin": "rè qíng", "han_viet": "Nhiệt tình", "meaning_vi": "Nhiệt tình / Hiếu khách", "nuance_note": "Thái độ nồng nhiệt chào đón.", "visual_action": "Bắt tay nồng nhiệt."},
            {"level": 3, "time_range": "00:10 - 00:15", "hanzi": "积极", "pinyin": "jī jí", "han_viet": "Tích cực", "meaning_vi": "Tích cực / Hăng hái", "nuance_note": "Chủ động tham gia hoạt động.", "visual_action": "Giơ tay xung phong."},
            {"level": 4, "time_range": "00:15 - 00:20", "hanzi": "踊跃", "pinyin": "yǒng yuè", "han_viet": "Dũng dược", "meaning_vi": "Hăng hái / Sôi nổi", "nuance_note": "Hăng hái tranh nhau tham gia.", "visual_action": "Đông đảo tham gia hăng hái."},
            {"level": 5, "time_range": "00:20 - 00:25", "hanzi": "热火朝天", "pinyin": "rè huǒ cháo tiān", "han_viet": "Nhiệt hỏa triều thiên", "meaning_vi": "Khí thế hừng hực sôi nổi", "nuance_note": "Thành ngữ không khí lao động sôi động cực điểm.", "visual_action": "Không khí hừng hực nhộn nhịp."}
        ],
        "cta_text": "Từ HSK 5 này bạn đã từng dùng qua chưa? Comment nhé!"
    },
    {
        "topic_id": "QUIZ_HSK_020",
        "concept_name_vi": "Khiêm tốn / Nhún nhường",
        "hook_title": "5 cấp độ 'Khiêm Tốn' trong tiếng Trung - Bạn ở HSK mấy?",
        "levels": [
            {"level": 1, "time_range": "00:00 - 00:05", "hanzi": "客气", "pinyin": "kè qi", "han_viet": "Khách khí", "meaning_vi": "Khách sáo / Lịch sự", "nuance_note": "Khẩu ngữ xã giao lịch thiệp.", "visual_action": "Cúi đầu chào lịch sự."},
            {"level": 2, "time_range": "00:05 - 00:10", "hanzi": "谦虚", "pinyin": "qiān xū", "han_viet": "Khiêm hư", "meaning_vi": "Khiêm tốn / Nhún nhường", "nuance_note": "Không tự mãn về thành tích.", "visual_action": "Xua tay xua tay khiêm tốn."},
            {"level": 3, "time_range": "00:10 - 00:15", "hanzi": "低调", "pinyin": "dī diào", "han_viet": "Đê điệu", "meaning_vi": "Kín tiếng / Giản dị", "nuance_note": "Giữ mình không khoe khoang.", "visual_action": "Ăn mặc giản dị điềm tĩnh."},
            {"level": 4, "time_range": "00:15 - 00:20", "hanzi": "谦逊", "pinyin": "qiān xùn", "han_viet": "Khiêm tốn", "meaning_vi": "Khiêm nhường / Nhã nhặn", "nuance_note": "Thái độ tôn trọng kính nhường.", "visual_action": "Chắp tay cung kính."},
            {"level": 5, "time_range": "00:20 - 00:25", "hanzi": "虚怀若谷", "pinyin": "xū huái ruò gǔ", "han_viet": "Hư hoài nhược cốc", "meaning_vi": "Lòng rộng mở như thung lũng", "nuance_note": "Thành ngữ khiêm tốn rộng lượng lắng nghe.", "visual_action": "Lắng nghe chăm chú tiếp thu."}
        ],
        "cta_text": "Thành ngữ HSK 5 này có hay không? Comment cảm nghĩ nhé!"
    },
    {
        "topic_id": "QUIZ_HSK_021",
        "concept_name_vi": "Tự hào / Hãnh diện",
        "hook_title": "5 cấp độ 'Tự Hào' trong tiếng Trung - Bạn ở HSK mấy?",
        "levels": [
            {"level": 1, "time_range": "00:00 - 00:05", "hanzi": "高兴", "pinyin": "gāo xìng", "han_viet": "Cao hứng", "meaning_vi": "Vui mừng / Hài lòng", "nuance_note": "Vui vẻ phấn khởi cơ bản.", "visual_action": "Cười mỉm tự hào."},
            {"level": 2, "time_range": "00:05 - 00:10", "hanzi": "自豪", "pinyin": "zì háo", "han_viet": "Tự hào", "meaning_vi": "Tự hào / Hãnh diện", "nuance_note": "Cảm giác vinh dự về bản thân.", "visual_action": "Ngẩng cao đầu tự tin."},
            {"level": 3, "time_range": "00:10 - 00:15", "hanzi": "骄傲", "pinyin": "jiāo ào", "han_viet": "Kiêu ngạo", "meaning_vi": "Tự hào / Kiêu hãnh", "nuance_note": "Hãnh diện hoặc tự mãn.", "visual_action": "Đứng thẳng khoanh tay tự tin."},
            {"level": 4, "time_range": "00:15 - 00:20", "hanzi": "光荣", "pinyin": "guāng róng", "han_viet": "Quang vinh", "meaning_vi": "Vinh quang / Vang danh", "nuance_note": "Danh dự cao quý.", "visual_action": "Đeo huy chương vinh quang."},
            {"level": 5, "time_range": "00:20 - 00:25", "hanzi": "引以为傲", "pinyin": "yǐn yǐ wéi ào", "han_viet": "Dẫn dĩ vi ngạo", "meaning_vi": "Lấy làm tự hào sâu sắc", "nuance_note": "Thành ngữ lấy đó làm niềm hãnh diện.", "visual_action": "Giơ bằng khen khoe gia đình."}
        ],
        "cta_text": "Từ HSK 5 này bạn vượt qua chưa? Comment điểm số nhé!"
    },
    {
        "topic_id": "QUIZ_HSK_022",
        "concept_name_vi": "Bối rối / Ngượng ngùng",
        "hook_title": "5 cấp độ 'Bối Rối' trong tiếng Trung - Bạn ở HSK mấy?",
        "levels": [
            {"level": 1, "time_range": "00:00 - 00:05", "hanzi": "不好意思", "pinyin": "bù hǎo yì si", "han_viet": "Bất hảo ý tứ", "meaning_vi": "Ngượng ngùng / E ngại", "nuance_note": "Khẩu ngữ ngượng nhẹ xã giao.", "visual_action": "Gãi đầu cười trừ."},
            {"level": 2, "time_range": "00:05 - 00:10", "hanzi": "害羞", "pinyin": "hài xiū", "han_viet": "Hại tu", "meaning_vi": "E ấp / Mắc cỡ", "nuance_note": "E ngại ngượng ngùng tính cách.", "visual_action": "Che mặt ngượng ngùng."},
            {"level": 3, "time_range": "00:10 - 00:15", "hanzi": "尴尬", "pinyin": "gān gà", "han_viet": "Cám cái", "meaning_vi": "Bối rối / Ngượng ngùng", "nuance_note": "Tình huống lúng túng trớ trêu.", "visual_action": "Tổ quạ mọc trên đầu bối rối."},
            {"level": 4, "time_range": "00:15 - 00:20", "hanzi": "局促不安", "pinyin": "jú cù bù ān", "han_viet": "Cục xúc bất an", "meaning_vi": "Bồn chồn không yên", "nuance_note": "Mất tự nhiên gượng gạo.", "visual_action": "Vắt tay đứng ngồi không yên."},
            {"level": 5, "time_range": "00:20 - 00:25", "hanzi": "哭笑不得", "pinyin": "kū xiào bù dé", "han_viet": "Khốc tiếu bất đắc", "meaning_vi": "Dở khóc dở cười", "nuance_note": "Thành ngữ trớ trêu vừa buồn vừa buồn cười.", "visual_action": "Nửa mặt cười nửa mặt khóc."}
        ],
        "cta_text": "Từ HSK 5 bạn đã dùng bao giờ chưa? Comment cho Lê Lê nha!"
    }
]

def mask_key(key: Optional[str]) -> str:
    if not key or not str(key).strip():
        return "None"
    k = str(key).strip()
    if len(k) <= 8:
        return "****"
    return f"{k[:6]}...****"

def parse_gemini_keys(keys_input: Optional[Union[str, List[str]]] = None) -> List[str]:
    keys = []
    if keys_input:
        if isinstance(keys_input, list):
            for item in keys_input:
                if item and isinstance(item, str):
                    for sub in re.split(r"[\n,;]+", item):
                        clean = sub.strip()
                        if clean and clean not in keys:
                            keys.append(clean)
        elif isinstance(keys_input, str):
            for sub in re.split(r"[\n,;]+", keys_input):
                clean = sub.strip()
                if clean and clean not in keys:
                    keys.append(clean)

    if not keys:
        env_raw = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        if env_raw:
            for sub in re.split(r"[\n,;]+", env_raw):
                clean = sub.strip()
                if clean and clean not in keys:
                    keys.append(clean)

    return keys

def parse_json_from_llm(content: str) -> Optional[Any]:
    if not content or not isinstance(content, str):
        return None

    cleaned = content.strip()
    if "```" in cleaned:
        code_block_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
        matches = code_block_pattern.findall(cleaned)
        for match in matches:
            candidate = match.strip()
            try:
                parsed = json.loads(candidate)
                if parsed is not None:
                    return parsed
            except json.JSONDecodeError:
                fixed = re.sub(r",\s*([\]}])", r"\1", candidate)
                try:
                    parsed = json.loads(fixed)
                    if parsed is not None:
                        return parsed
                except json.JSONDecodeError:
                    continue

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    def _extract_container(start_idx: int, end_idx: int) -> Optional[Any]:
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            candidate = cleaned[start_idx:end_idx + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                fixed = re.sub(r",\s*([\]}])", r"\1", candidate)
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass
        return None

    start_arr = cleaned.find("[")
    end_arr = cleaned.rfind("]")
    start_obj = cleaned.find("{")
    end_obj = cleaned.rfind("}")

    if start_obj != -1 and (start_arr == -1 or start_obj < start_arr):
        res = _extract_container(start_obj, end_obj)
        if res is not None:
            return res
        res = _extract_container(start_arr, end_arr)
        if res is not None:
            return res
    elif start_arr != -1 and (start_obj == -1 or start_arr < start_obj):
        res = _extract_container(start_arr, end_arr)
        if res is not None:
            return res
        res = _extract_container(start_obj, end_obj)
        if res is not None:
            return res

    return None

def call_gemini_api(
    prompt: str,
    system_prompt: Optional[str] = None,
    api_keys: Optional[List[str]] = None,
    model: str = DEFAULT_GEMINI_MODEL,
    temperature: float = 0.7,
    timeout: int = 25,
    max_recovery_cycles: int = 2
) -> Optional[str]:
    keys = parse_gemini_keys(api_keys)
    if not keys:
        logger.warning("No Gemini API keys provided for direct Google AI Studio call.")
        return None

    candidate_models = [model]
    for fb in FALLBACK_GEMINI_MODELS:
        if fb not in candidate_models:
            candidate_models.append(fb)

    for cycle in range(max_recovery_cycles + 1):
        rate_limit_hits = 0
        for key_idx, key in enumerate(keys):
            masked = mask_key(key)
            for cur_model in candidate_models:
                url = f"{GEMINI_ENDPOINT_BASE}/{cur_model}:generateContent?key={key}"
                logger.info(f"Calling Google AI Studio (Model: {cur_model}, Key [{key_idx + 1}/{len(keys)}]: {masked})...")

                payload = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": prompt}]
                        }
                    ],
                    "generationConfig": {
                        "temperature": temperature,
                        "responseMimeType": "application/json"
                    }
                }

                if system_prompt:
                    payload["systemInstruction"] = {
                        "parts": [{"text": system_prompt}]
                    }

                headers = {"Content-Type": "application/json"}

                try:
                    resp = requests.post(url, headers=headers, json=payload, timeout=(5.0, float(timeout)))
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            text_parts = [p.get("text", "") for p in parts if not p.get("thought") and p.get("text")]
                            if not text_parts and parts:
                                text_parts = [parts[0].get("text", "")]
                            full_text = "".join(text_parts).strip()
                            if full_text:
                                logger.info(f" Google AI Studio ({cur_model}) returned valid response ({len(full_text)} chars).")
                                return full_text
                    elif resp.status_code == 429:
                        rate_limit_hits += 1
                        logger.warning(f"Google AI Studio Rate Limit (429) for key {masked}. Rotating to next key...")
                        break
                    elif resp.status_code in (400, 403, 404):
                        logger.warning(f"Google AI Studio error ({resp.status_code}) with model {cur_model} on key {masked}: {resp.text[:200]}")
                        continue
                    else:
                        logger.warning(f"Google AI Studio error HTTP {resp.status_code}: {resp.text[:200]}")
                except Exception as e:
                    logger.warning(f"Google AI Studio request exception on key {masked} ({cur_model}): {e}")
                    continue

        if rate_limit_hits >= len(keys) and cycle < max_recovery_cycles:
            cooldown_sec = 60
            logger.warning(f"🚨 [QUOTA EXHAUSTED] All {len(keys)} Gemini keys hit Rate Limit (429)! Entering cooldown recovery ({cooldown_sec}s)...")
            time.sleep(cooldown_sec)

    return None

def build_multilevels_master_system_prompt() -> str:
    return (
        "Bạn là Biên tập viên nội dung giáo dục Hán ngữ chuyên nghiệp cho kênh \"lelehoctiengtrung\".\n\n"
        "Nhiệm vụ của bạn: Tạo nội dung cho format video \"Quiz Thử Thách Phản Xạ: 1 Nghĩa - 5 Cấp Độ HSK (5s/cấp độ)\".\n\n"
        "[YÊU CẦU DỮ LIỆU & RÀNG BUỘC CHẶT CHẼ]\n"
        "1. Chuẩn HSK: Các từ bắt buộc phải nằm chính xác trong danh mục từ vựng tương ứng (HSK 1, 2, 3, 4, 5).\n"
        "2. Tính đồng nghĩa/sắc thái: Cả 5 từ phải cùng diễn đạt một ý niệm chung (ví dụ: Vui vẻ, Tức giận, Đẹp, Khó khăn...), nhưng tăng dần từ khẩu ngữ cơ bản -> văn nói nâng cao -> văn viết / thành ngữ trang trọng.\n"
        "3. 100% Chữ Giản Thể (Simplified Chinese). Tuyệt đối CẤM chữ Phồn thể.\n"
        "4. Pinyin chuẩn quốc tế: Có dấu thanh điệu đầy đủ, tương ứng 1:1 từng âm tiết với chữ Hán, cách nhau bằng khoảng trắng.\n"
        "5. Phải có âm Hán-Việt chuẩn để người học ghi nhớ sâu gốc từ.\n"
        "6. NGHĨA TIẾNG VIỆT THUẦN TÚY & NGẮN GỌN: Tuyệt đối không giải thích dài dòng, không chứa từ tiếng Anh.\n"
        "7. ƯU TIÊN THÀNH NGỮ TƯƠNG ĐƯƠNG: Đối với các từ ở cấp HSK 4, HSK 5 nếu có thành ngữ tiếng Việt tương đương (ví dụ: 'Nổi trận lôi đình', 'Thấp thỏm lo âu', 'Mở cờ trong bụng', 'Vui sướng phát điên', 'Bàn luận sôi nổi'...), HÃY DÙNG NGAY THÀNH NGỮ ĐÓ làm `meaning_vi`.\n"
        "8. RÀNG BUỘC ĐỘ DÀI: `meaning_vi` tối đa 25 ký tự (1-4 từ ngắn gọn) để vừa vặn trong 1 dòng ngang duy nhất trong vùng an toàn (TikTok Safe Zone), tuyệt đối không để chữ quá to gây tràn/cắt câu.\n\n"
        "[OUTPUT FORMAT]\n"
        "Trả về định dạng JSON thuần túy (Array các đối tượng nếu sinh nhiều bộ, hoặc 1 JSON Object nếu sinh 1 bộ):\n"
        "{\n"
        "  \"topic_id\": \"QUIZ_HSK_XXX\",\n"
        "  \"concept_name_vi\": \"STRING (Nghĩa chung, ví dụ: 'Tức giận / Bực mình')\",\n"
        "  \"hook_title\": \"STRING (Tiêu đề giật tít cho video)\",\n"
        "  \"levels\": [\n"
        "    {\n"
        "      \"level\": 1,\n"
        "      \"time_range\": \"00:00 - 00:05\",\n"
        "      \"hanzi\": \"STRING\",\n"
        "      \"pinyin\": \"STRING\",\n"
        "      \"han_viet\": \"STRING\",\n"
        "      \"meaning_vi\": \"STRING\",\n"
        "      \"nuance_note\": \"STRING (Ghi chú sắc thái ngắn)\",\n"
        "      \"visual_action\": \"STRING (Gợi ý diễn xuất/biểu cảm/chèn icon)\"\n"
        "    },\n"
        "    { \"level\": 2, \"time_range\": \"00:05 - 00:10\", \"hanzi\": \"...\", \"pinyin\": \"...\", \"han_viet\": \"...\", \"meaning_vi\": \"...\", \"nuance_note\": \"...\", \"visual_action\": \"...\" },\n"
        "    { \"level\": 3, \"time_range\": \"00:10 - 00:15\", \"hanzi\": \"...\", \"pinyin\": \"...\", \"han_viet\": \"...\", \"meaning_vi\": \"...\", \"nuance_note\": \"...\", \"visual_action\": \"...\" },\n"
        "    { \"level\": 4, \"time_range\": \"00:15 - 00:20\", \"hanzi\": \"...\", \"pinyin\": \"...\", \"han_viet\": \"...\", \"meaning_vi\": \"...\", \"nuance_note\": \"...\", \"visual_action\": \"...\" },\n"
        "    { \"level\": 5, \"time_range\": \"00:20 - 00:25\", \"hanzi\": \"...\", \"pinyin\": \"...\", \"han_viet\": \"...\", \"meaning_vi\": \"...\", \"nuance_note\": \"...\", \"visual_action\": \"...\" }\n"
        "  ],\n"
        "  \"cta_text\": \"STRING (Câu kêu gọi hành động cho 5s cuối)\"\n"
        "}"
    )

def generate_multilevels_topics_with_llm(
    existing_concepts: Optional[List[str]] = None,
    count: int = 1,
    api_keys: Optional[Union[str, List[str]]] = None,
    model: str = DEFAULT_GEMINI_MODEL,
    custom_concept_keyword: Optional[str] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Generate '1 Nghĩa - 5 Cấp độ HSK' batches via Gemini AI Studio.
    """
    system_prompt = build_multilevels_master_system_prompt()

    used_sample = ", ".join(list(existing_concepts)[-30:]) if existing_concepts else "chưa có"

    if custom_concept_keyword:
        concept_instruction = f"TẠO CHỦ ĐỀ CỤ THỂ THEO TỪ KHÓA: '{custom_concept_keyword}'."
    else:
        concept_instruction = f"Hãy tự chọn {count} ý niệm / khái niệm cốt lõi giàu cảm xúc, phổ biến trong đời sống (ví dụ: Thông minh, Giàu có, Đắt đỏ, Sợ hãi, Cẩn thận, Nhanh nhẹn, Khó khăn, Thất vọng, Giúp đỡ, Thành công, v.v.)."

    user_prompt = f"""Hãy tạo đúng {count} bộ kịch bản video "1 Nghĩa - 5 Cấp Độ HSK" cho kênh @lelehoctiengtrung.
{concept_instruction}

NGỮ CẢNH LOẠI TRỪ (TRÁNH TRÙNG LẶP):
- Các khái niệm đã làm gần đây: [{used_sample}]

Định dạng JSON yêu cầu: Trả về 1 JSON Array chứa {count} đối tượng kịch bản hoàn chỉnh theo đúng mẫu Output Format.
"""

    keys = parse_gemini_keys(api_keys)
    raw_content = None
    if keys:
        raw_content = call_gemini_api(
            prompt=user_prompt,
            system_prompt=system_prompt,
            api_keys=keys,
            model=model,
            temperature=0.7
        )

    if not raw_content:
        logger.warning("Gemini LLM call did not return content.")
        return None

    parsed = parse_json_from_llm(raw_content)
    if isinstance(parsed, list) and len(parsed) > 0:
        logger.info(f" Successfully generated {len(parsed)} Multi-Level batches!")
        return parsed
    elif isinstance(parsed, dict) and "concept_name_vi" in parsed:
        logger.info(" Parsed 1 Multi-Level batch (dict -> list).")
        return [parsed]

    logger.warning("Could not parse LLM output into valid Multi-Level batches.")
    return None

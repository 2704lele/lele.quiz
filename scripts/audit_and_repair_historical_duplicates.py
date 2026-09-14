#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/audit_and_repair_historical_duplicates.py
Full Historical Audit & In-Place Deduplication / Repair Engine.

Core Invariants:
1. Complete Historical Scan across all 4 quiz tabs ('pinyin', 'vocabCN', 'vocabVN', 'multilevels').
2. Detects duplicate topic titles (case/symbol normalized) and topics violating quiz spirit (banned phonetic theory).
3. IN-PLACE REPAIR: Never deletes the row. Directly replaces row contents (Cols A-P) at that exact row index.
4. Enforces Gatekeeper 1 QC (strict spaced pinyin, non-dummy words, 2-4 word practical vocabulary spirit).
5. Enforces strict 21px row height invariant across all tabs after repairs.
6. Sends executive audit and repair report to Telegram.
"""

import os
import sys
import json
import re
import time
import argparse
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Set, Optional, Tuple

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

QUIZ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if QUIZ_ROOT not in sys.path:
    sys.path.insert(0, QUIZ_ROOT)

import gspread
from scripts.enforce_row_height_21px import RowHeightEnforcer, SPREADSHEET_ID, get_sheets_service
from scripts.ai_key_rotator import get_ai_rotator
from scripts.linguistic_qc import (
    GlobalHanziFrequencyMatrix,
    PinyinLinguisticValidator,
    MultilevelsEscalationValidator,
    is_dummy_word,
    normalize_pinyin_spacing,
    normalize_topic_string,
    clean_quiz_topic,
    validate_topic_spirit,
)
from scripts.run_ideation_dispatcher import (
    get_gspread_client,
    get_vietnam_now_str,
    validate_and_sanitize_row,
    build_pinyin_metadata,
    build_vocabcn_metadata,
    build_vocabvn_metadata,
    build_multilevels_metadata,
    normalize_tab_name,
    STANDARD_COLUMNS,
    VALID_TABS,
)


def send_telegram_alert(message: str) -> None:
    """Sends audit & repair report to Telegram."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "-1004392602002").strip()
    if not token:
        env_file = os.path.expanduser("~/.cloud-profiles/lelehoctiengtrung/telegram/telegram.env")
        if os.path.exists(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("TELEGRAM_BOT_TOKEN="):
                            token = line.split("=", 1)[1].strip().strip('"').strip("'")
                        elif line.startswith("TELEGRAM_CHAT_ID="):
                            chat_id = line.split("=", 1)[1].strip().strip('"').strip("'")
            except Exception:
                pass

    if not token or not chat_id:
        print("  ⚠ Telegram credentials not found. Skipping Telegram notification.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true"
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"User-Agent": "QuizDedupAuditBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            print("  ✓ Audit report sent to Telegram successfully.")
    except Exception as e:
        print(f"  ⚠ Failed to send Telegram alert: {e}")


def generate_fresh_batch_for_tab(
    tab: str,
    row_idx: int,
    rotator,
    matrix: GlobalHanziFrequencyMatrix,
    max_retries: int = 2
) -> Tuple[Optional[List[str]], str]:
    """
    Generates a single brand new valid batch for a specific tab and row index,
    passing Gatekeeper 1 QC and anti-duplication constraints.
    Returns (sanitized_row_data, provider_used).
    """
    recent_50 = matrix.get_tab_recent_50_tracked(tab, limit=50)
    existing_topics = matrix.get_existing_topics(tab)
    topics_ban_str = ", ".join(f"'{t}'" for t in existing_topics[-35:]) if existing_topics else "không có"

    if tab == "pinyin":
        sys_prompt = (
            "Bạn là chuyên gia ngôn ngữ tiếng Trung của kênh 'Lê Lê Học Tiếng Trung'. "
            "Nhiệm vụ: Tạo 1 bộ câu hỏi trắc nghiệm Pinyin (Pinyin Quiz). "
            "Mỗi câu hỏi có 1 chữ Hán, 1 phiên âm Pinyin chuẩn và nghĩa tiếng Việt ngắn gọn. "
            "QUY TẮC CHỦ ĐỀ (TOPIC): Bắt buộc là danh mục từ vựng đời sống thực tế ngắn gọn 2-4 từ tiếng Việt "
            "(ví dụ: 'Đồ Gia Dụng', 'Rau Củ Quả', 'Nghề Nghiệp', 'Trang Phục', 'Phương Tiện', 'Đồ Ăn', 'Dụng Cụ Học Tập', 'Thời Tiết'). "
            "TUYỆT ĐỐI CẤM: KHÔNG tạo các chủ đề mang tính lý thuyết ngữ âm, luyện phát âm, phân biệt thanh điệu, thanh nhẹ, âm bật hơi, vận mẫu. "
            "Đây là QUIZ TỪ VỰNG NHANH, không phải bài giảng phát âm. "
            "KHÔNG kèm ' (HSK 1)' hay tiền tố 'Chủ đề:' vào trường topic. "
            "Quy tắc Pinyin: Bắt buộc có dấu cách giữa các âm tiết tương ứng từng chữ Hán (ví dụ: 'mǐ fàn', 'píng guǒ', 'fēi jī'). "
            "Output JSON dạng mảng: [{\"topic\": \"Đồ Gia Dụng\", \"level\": \"HSK 2\", "
            "\"words\": [{\"hanzi\": \"苹果\", \"pinyin\": \"píng guǒ\", \"meaning\": \"quả táo\"}]}]"
        )
        user_prompt = (
            f"Hãy tạo 1 chủ đề trắc nghiệm Pinyin hoàn toàn mới lạ (danh mục từ vựng đời sống 2-4 từ, gồm đúng 5 từ vựng HSK 1-3). "
            f"Pinyin phải có dấu cách giữa các âm tiết (ví dụ: 'píng guǒ', 'mǐ fàn'). "
            f"TUYỆT ĐỐI CẤM: Không tạo chủ đề lý thuyết ngữ âm. "
            f"Tuyệt đối KHÔNG tạo lại các chủ đề đã có sau: [{topics_ban_str}]. "
            f"Tuyệt đối KHÔNG trùng lặp các chữ Hán sau: {recent_50}."
        )
    elif tab == "vocabCN":
        sys_prompt = (
            "Bạn là biên tập viên tiếng Trung của kênh 'Lê Lê Học Tiếng Trung'. "
            "Nhiệm vụ: Tạo 1 bộ trắc nghiệm Đoán Nghĩa Tiếng Việt từ chữ Hán (VocabCN Quiz). "
            "QUY TẮC CHỦ ĐỀ (TOPIC): Bắt buộc là danh mục từ vựng đời sống thực tế ngắn gọn 2-4 từ tiếng Việt "
            "(ví dụ: 'Đồ Dùng Nhà Bếp', 'Thời Tiết', 'Địa Điểm Công Cộng', 'Cảm Xúc', 'Động Vật', 'Màu Sắc', 'Cây Cối'). "
            "TUYỆT ĐỐI CẤM: Không tạo chủ đề dài dòng, không tạo lý thuyết ngữ pháp/ngữ âm. Tên chủ đề chỉ 2-4 từ. "
            "KHÔNG kèm ' (HSK 1)' hay tiền tố 'Chủ đề:' vào trường topic. "
            "Quy tắc Pinyin: Bắt buộc có dấu cách giữa các âm tiết tương ứng từng chữ Hán (ví dụ: 'píng guǒ', 'fēi jī'). "
            "Output JSON dạng mảng: [{\"topic\": \"Đồ Dùng Nhà Bếp\", \"level\": \"HSK 2\", "
            "\"words\": [{\"hanzi\": \"苹果\", \"pinyin\": \"píng guǒ\", \"meaning\": \"quả táo\"}]}]"
        )
        user_prompt = (
            f"Hãy tạo 1 chủ đề trắc nghiệm Đoán Nghĩa Tiếng Việt hoàn toàn mới (danh mục từ vựng đời sống 2-4 từ, gồm đúng 5 từ vựng HSK 2-3). "
            f"Pinyin phải có dấu cách giữa các âm tiết (ví dụ: 'píng guǒ', 'mǐ fàn'). "
            f"TUYỆT ĐỐI CẤM: Không tạo chủ đề lý thuyết ngữ âm/ngữ pháp. Tên chủ đề ngắn gọn 2-4 từ. "
            f"Tuyệt đối KHÔNG tạo lại các chủ đề đã có sau: [{topics_ban_str}]. "
            f"Tuyệt đối KHÔNG trùng lặp các chữ Hán sau: {recent_50}."
        )
    elif tab == "vocabVN":
        sys_prompt = (
            "Bạn là biên tập viên tiếng Trung của kênh 'Lê Lê Học Tiếng Trung'. "
            "Nhiệm vụ: Tạo 1 bộ trắc nghiệm Đoán Chữ Hán từ Nghĩa Tiếng Việt (VocabVN Quiz). "
            "QUY TẮC CHỦ ĐỀ (TOPIC): Bắt buộc là danh mục từ vựng đời sống thực tế ngắn gọn 2-4 từ tiếng Việt "
            "(ví dụ: 'Bộ Phận Cơ Thể', 'Gia Vị Nấu Ăn', 'Trái Cây', 'Thiết Bị Điện Tử', 'Tính Cách', 'Văn Phòng Phẩm'). "
            "TUYỆT ĐỐI CẤM: Không tạo chủ đề dài dòng, không tạo lý thuyết ngữ pháp/ngữ âm. Tên chủ đề chỉ 2-4 từ. "
            "KHÔNG kèm ' (HSK 1)' hay tiền tố 'Chủ đề:' vào trường topic. "
            "Quy tắc Pinyin: Bắt buộc có dấu cách giữa các âm tiết tương ứng từng chữ Hán (ví dụ: 'fēi jī', 'píng guǒ'). "
            "Output JSON dạng mảng: [{\"topic\": \"Bộ Phận Cơ Thể\", \"level\": \"HSK 2\", "
            "\"words\": [{\"hanzi\": \"飞机\", \"pinyin\": \"fēi jī\", \"meaning\": \"máy bay\"}]}]"
        )
        user_prompt = (
            f"Hãy tạo 1 chủ đề trắc nghiệm Đoán Chữ Hán hoàn toàn mới (danh mục từ vựng đời sống 2-4 từ, gồm đúng 5 từ vựng HSK 2-3). "
            f"Pinyin phải có dấu cách giữa các âm tiết (ví dụ: 'fēi jī', 'mǐ fàn'). "
            f"TUYỆT ĐỐI CẤM: Không tạo chủ đề lý thuyết ngữ âm/ngữ pháp. Tên chủ đề ngắn gọn 2-4 từ. "
            f"Tuyệt đối KHÔNG tạo lại các chủ đề đã có sau: [{topics_ban_str}]. "
            f"Tuyệt đối KHÔNG trùng lặp các chữ Hán sau: {recent_50}."
        )
    elif tab == "multilevels":
        sys_prompt = (
            "Bạn là chuyên gia ngôn ngữ tiếng Trung của kênh 'Lê Lê Học Tiếng Trung'. "
            "Nhiệm vụ: Tạo kịch bản video định dạng '1 Nghĩa 5 Cấp Độ HSK (1 -> 5)'. "
            "Mỗi batch là 1 khái niệm/tính từ/động từ tiếng Việt ngắn gọn (1-3 từ, ví dụ: 'Tự Tin', 'Mệt Mỏi', 'Xinh Đẹp', 'Thành Công', 'Kiên Trì'), "
            "biểu đạt qua 5 cấp độ từ vựng HSK tăng dần từ HSK 1 đến HSK 5. "
            "QUY TẮC: Khái niệm ngắn gọn, súc tích, không tạo câu dài, không lý thuyết ngữ pháp. "
            "Output JSON dạng mảng: [\n"
            "  {\n"
            "    \"concept_name_vi\": \"Tự Tin\",\n"
            "    \"levels\": [\n"
            "      {\"level\": 1, \"hsk\": \"HSK 1\", \"hanzi\": \"好\", \"pinyin\": \"hǎo\", \"han_viet\": \"Hảo\", \"meaning_vi\": \"Tốt\", \"nuance_note\": \"Cơ bản\", \"visual_action\": \"Gật đầu\"},\n"
            "      {\"level\": 2, \"hsk\": \"HSK 2\", \"hanzi\": \"行\", \"pinyin\": \"xíng\", \"han_viet\": \"Hành\", \"meaning_vi\": \"Được\", \"nuance_note\": \"Khá\", \"visual_action\": \"Cười nhẹ\"},\n"
            "      {\"level\": 3, \"hsk\": \"HSK 3\", \"hanzi\": \"自信\", \"pinyin\": \"zì xìn\", \"han_viet\": \"Tự tin\", \"meaning_vi\": \"Tự tin\", \"nuance_note\": \"Rõ ràng\", \"visual_action\": \"Ưỡn ngực\"},\n"
            "      {\"level\": 4, \"hsk\": \"HSK 4\", \"hanzi\": \"坚信\", \"pinyin\": \"jiān xìn\", \"han_viet\": \"Kiên tín\", \"meaning_vi\": \"Vững tin\", \"nuance_note\": \"Mạnh mẽ\", \"visual_action\": \"Nắm tay\"},\n"
            "      {\"level\": 5, \"hsk\": \"HSK 5\", \"hanzi\": \"昂首阔步\", \"pinyin\": \"áng shǒu kuò bù\", \"han_viet\": \"Ngẩng đầu\", \"meaning_vi\": \"Hiên ngang\", \"nuance_note\": \"Tuyệt đối\", \"visual_action\": \"Sải bước\"}\n"
            "    ]\n"
            "  }\n"
            "]"
        )
        user_prompt = (
            f"Hãy tạo 1 chủ đề '1 Nghĩa 5 Cấp Độ HSK' đặc sắc, sâu sắc hoàn toàn mới (khái niệm 1-3 từ tiếng Việt), biểu đạt sắc thái từ HSK 1 đến HSK 5. "
            f"Tuyệt đối KHÔNG tạo lại các khái niệm đã có sau: [{topics_ban_str}]. "
            f"Tuyệt đối KHÔNG trùng lặp các chữ Hán sau: {recent_50}."
        )
    else:
        raise ValueError(f"Unknown tab: {tab}")

    # Fallback offline bank if AI provider fails or rate-limits
    FALLBACK_BANK = {
        "pinyin": [
            ("Thế Giới Côn Trùng", "HSK 3", [("蝴蝶", "hú dié", "con bướm"), ("蚂蚁", "mǎ yǐ", "con kiến"), ("蜜蜂", "mì fēng", "con ong"), ("蜻蜓", "qīng tíng", "con chuồn chuồn"), ("蚊子", "wén zi", "con muỗi")]),
            ("Đồ Nghề Sửa Chữa", "HSK 3", [("锤子", "chuí zi", "cái búa"), ("螺丝", "luó sī", "ốc vít"), ("胶水", "jiāo shuǐ", "keo dán"), ("剪刀", "jiǎn dāo", "cái kéo"), ("钉子", "dīng zi", "cái đinh")]),
            ("Thời Tiết Khắc Nghiệt", "HSK 3", [("暴雨", "bào yǔ", "mưa bão"), ("台风", "tái fēng", "bão lớn"), ("闪电", "shǎn diàn", "sấm sét"), ("大雾", "dà wù", "sương mù dày"), ("冰雹", "bīng báo", "mưa đá")]),
            ("Nhạc Cụ Âm Nhạc", "HSK 3", [("吉他", "jí tā", "đàn ghi-ta"), ("钢琴", "gāng qín", "đàn piano"), ("笛子", "dí zi", "cây sáo"), ("鼓", "gǔ", "cái trống"), ("小提琴", "xiǎo tí qín", "đàn vĩ cầm")]),
            ("Đồ Dùng Phòng Tắm", "HSK 2", [("毛巾", "máo jīn", "khăn mặt"), ("牙刷", "yá shuā", "bàn chải đánh răng"), ("牙膏", "yá gāo", "kem đánh răng"), ("香皂", "xiāng zào", "bánh xà phòng"), ("镜子", "jìng zi", "cái gương")]),
            ("Rau Củ Vườn Nhà", "HSK 2", [("黄瓜", "huáng guā", "dưa chuột"), ("番茄", "fān qié", "cà chua"), ("土豆", "tǔ dòu", "khoai tây"), ("胡萝卜", "hú luó bo", "cà rốt"), ("白菜", "bái cài", "rau cải trắng")]),
            ("Nghề Nghiệp Xã Hội", "HSK 2", [("警察", "jǐng chá", "cảnh sát"), ("护士", "hù shi", "y tá"), ("司机", "sī jī", "tài xế"), ("厨师", "chú shī", "đầu bếp"), ("记者", "jì zhě", "nhà báo")]),
            ("Đồ Dùng Phòng Khách", "HSK 2", [("沙发", "shā fā", "ghế sô-pha"), ("电视", "diàn shì", "ti vi"), ("茶几", "chá jī", "bàn trà"), ("窗帘", "chuāng lián", "rèm cửa"), ("空调", "kōng tiáo", "máy điều hòa")]),
            ("Động Vật Dưới Nước", "HSK 2", [("螃蟹", "páng xiè", "con cua"), ("龙虾", "lóng xiā", "tôm hùm"), ("乌龟", "wū guī", "con rùa"), ("章鱼", "zhāng yú", "bạch tuộc"), ("海豚", "hǎi tún", "cá heo")]),
            ("Gia Vị Truyền Thống", "HSK 3", [("酱油", "jiàng yóu", "xì dầu"), ("食醋", "shí cù", "giấm ăn"), ("白糖", "bái táng", "đường cát trắng"), ("食盐", "shí yán", "muối ăn"), ("胡椒", "hú jiāo", "hạt tiêu")]),
        ],
        "vocabCN": [
            ("Địa Điểm Mua Sắm", "HSK 2", [("商场", "shāng chǎng", "trung tâm thương mại"), ("超市", "chāo shì", "siêu thị"), ("书店", "shū diàn", "hiệu sách"), ("花店", "huā diàn", "tiệm hoa"), ("药店", "yào diàn", "hiệu thuốc")]),
            ("Trang Phục Mùa Đông", "HSK 2", [("大衣", "dà yī", "áo khoác măng tô"), ("毛衣", "máo yī", "áo len"), ("手套", "shǒu tào", "găng tay"), ("围巾", "wéi jīn", "khăn quàng cổ"), ("皮鞋", "pí xié", "giày da")]),
            ("Động Vật Rừng Xanh", "HSK 2", [("狮子", "shī zi", "sư tử"), ("大象", "dà xiàng", "con voi"), ("猴子", "hóu zi", "con khỉ"), ("长颈鹿", "cháng jǐng lù", "hươu cao cổ"), ("老虎", "lǎo hǔ", "con hổ")]),
            ("Thiết Bị Công Nghệ", "HSK 3", [("手机", "shǒu jī", "điện thoại di động"), ("电脑", "diàn nǎo", "máy vi tính"), ("平板", "píng bǎn", "máy tính bảng"), ("耳机", "ěr jī", "tai nghe"), ("相机", "xiàng jī", "máy ảnh")]),
            ("Môi Trường Trường Học", "HSK 2", [("教室", "jiào shì", "phòng học"), ("操场", "cāo chǎng", "sân thể dục"), ("食堂", "shí táng", "nhà ăn"), ("图书馆", "tú shū guǎn", "thư viện"), ("宿舍", "sù shè", "ký túc xá")]),
            ("Giao Thông Đô Thị", "HSK 2", [("地铁", "dì tiě", "tàu điện ngầm"), ("公交车", "gōng jiāo chē", "xe buýt"), ("轮船", "lún chuán", "tàu thủy"), ("高铁", "gāo tiě", "tàu cao tốc"), ("摩托车", "mó tuō chē", "xe máy")]),
            ("Dụng Cụ Nhà Bếp", "HSK 2", [("筷子", "kuài zi", "đôi đũa"), ("勺子", "sháo zi", "cái thìa"), ("盘子", "pán zi", "cái đĩa"), ("碗", "wǎn", "cái bát"), ("锅", "guō", "cái nồi")]),
            ("Nông Trại & Gia Súc", "HSK 2", [("奶牛", "nǎi niú", "bò sữa"), ("绵羊", "mián yáng", "con cừu"), ("鸭子", "yā zi", "con vịt"), ("鹅", "é", "con ngỗng"), ("兔子", "tù zi", "con thỏ")]),
            ("Đồ Đạc Phòng Ngủ", "HSK 2", [("床单", "chuáng dān", "ga trải giường"), ("被子", "bèi zi", "cái chăn"), ("枕头", "zhěn tou", "cái gối"), ("衣柜", "yī guì", "tủ quần áo"), ("台灯", "tái dēng", "đèn bàn")]),
            ("Hoạt Động Rảnh Rỗi", "HSK 2", [("散步", "sàn bù", "đi dạo"), ("听歌", "tīng gē", "nghe nhạc"), ("看报", "kàn bào", "đọc báo"), ("养花", "yǎng huā", "trồng hoa"), ("钓鱼", "diào yú", "câu cá")]),
            ("Cơ Thể Người", "HSK 2", [("头发", "tóu fa", "mái tóc"), ("眼睛", "yǎn jing", "đôi mắt"), ("鼻子", "bí zi", "cái mũi"), ("嘴巴", "zuǐ ba", "cái miệng"), ("耳朵", "ěr duo", "cái tai")]),
            ("Địa Điểm Du Lịch", "HSK 2", [("海滩", "hǎi tān", "bãi biển"), ("森林", "sēn lín", "khu rừng"), ("瀑布", "pù bù", "thác nước"), ("岛屿", "dǎo yǔ", "hòn đảo"), ("沙漠", "shā mò", "sa mạc")]),
        ],
        "vocabVN": [
            ("Dụng Cụ Học Tập Mới", "HSK 1", [("sách giáo khoa", "kè běn", "课本"), ("bút chì", "qiān bǐ", "铅笔"), ("thước kẻ", "chǐ zi", "尺子"), ("cặp sách", "shū bāo", "书包"), ("cục tẩy", "xiàng pí", "橡皮")]),
            ("Môn Thể Thao Mới", "HSK 2", [("bóng chuyền", "pái qiú", "排球"), ("cầu lông", "yǔ máo qiú", "羽毛球"), ("bóng bàn", "pīng pāng qiú", "乒乓球"), ("trượt băng", "huá bīng", "滑冰"), ("leo núi", "pá shān", "爬山")]),
            ("Đồ Ăn Vặt", "HSK 2", [("bánh quy", "bǐng gān", "饼干"), ("sô-cô-la", "qiǎo kè lì", "巧克力"), ("kẹo ngọt", "táng guǒ", "糖果"), ("khoai tây chiên", "shǔ piàn", "薯片"), ("bỏng ngô", "bào mǐ huā", "爆米花")]),
        ],
        "multilevels": [
            ("Tiết Kiệm", [
                {"level": 1, "hsk": "HSK 1", "hanzi": "少", "pinyin": "shǎo", "han_viet": "Thiểu", "meaning_vi": "Ít", "nuance_note": "Cơ bản", "visual_action": "Giơ ngón tay"},
                {"level": 2, "hsk": "HSK 2", "hanzi": "存", "pinyin": "cún", "han_viet": "Tồn", "meaning_vi": "Cất giữ", "nuance_note": "Tích lũy", "visual_action": "Bỏ vào hộp"},
                {"level": 3, "hsk": "HSK 3", "hanzi": "节约", "pinyin": "jié yuē", "han_viet": "Tiết ước", "meaning_vi": "Tiết kiệm", "nuance_note": "Ý thức", "visual_action": "Tắt đèn"},
                {"level": 4, "hsk": "HSK 4", "hanzi": "节省", "pinyin": "jié shěng", "han_viet": "Tiết tỉnh", "meaning_vi": "Giản tiện", "nuance_note": "Cân nhắc", "visual_action": "Tính toán"},
                {"level": 5, "hsk": "HSK 5", "hanzi": "克勤克俭", "pinyin": "kè qín kè jiǎn", "han_viet": "Khắc cần khắc kiệm", "meaning_vi": "Cần kiệm", "nuance_note": "Tuyệt đối", "visual_action": "Chắp tay"}
            ]),
            ("Cống Hiến", [
                {"level": 1, "hsk": "HSK 1", "hanzi": "多", "pinyin": "duō", "han_viet": "Đa", "meaning_vi": "Nhiều", "nuance_note": "Cơ bản", "visual_action": "Giơ hai tay"},
                {"level": 2, "hsk": "HSK 2", "hanzi": "送", "pinyin": "sòng", "han_viet": "Tống", "meaning_vi": "Tặng", "nuance_note": "Trao tặng", "visual_action": "Đưa hai tay tới"},
                {"level": 3, "hsk": "HSK 3", "hanzi": "愿意", "pinyin": "yuàn yì", "han_viet": "Nguyện ý", "meaning_vi": "Tự nguyện", "nuance_note": "Nhiệt tình", "visual_action": "Gật đầu đồng ý"},
                {"level": 4, "hsk": "HSK 4", "hanzi": "奉献", "pinyin": "fèng xiàn", "han_viet": "Phụng hiến", "meaning_vi": "Cống hiến", "nuance_note": "Tận tụy", "visual_action": "Hai tay nâng cao"},
                {"level": 5, "hsk": "HSK 5", "hanzi": "舍己为人", "pinyin": "shě jǐ wèi rén", "han_viet": "Xả kỷ vị nhân", "meaning_vi": "Quên mình vì người", "nuance_note": "Cao cả", "visual_action": "Đặt tay lên tim"}
            ]),
            ("Quyết Tâm", [
                {"level": 1, "hsk": "HSK 1", "hanzi": "想", "pinyin": "xiǎng", "han_viet": "Tưởng", "meaning_vi": "Muốn", "nuance_note": "Cơ bản", "visual_action": "Suy nghĩ"},
                {"level": 2, "hsk": "HSK 2", "hanzi": "要", "pinyin": "yào", "han_viet": "Yếu", "meaning_vi": "Cần phải", "nuance_note": "Mục tiêu", "visual_action": "Chỉ tay về trước"},
                {"level": 3, "hsk": "HSK 3", "hanzi": "决定", "pinyin": "jué dìng", "han_viet": "Quyết định", "meaning_vi": "Hạ quyết tâm", "nuance_note": "Rõ ràng", "visual_action": "Gật đầu dứt khoát"},
                {"level": 4, "hsk": "HSK 4", "hanzi": "决心", "pinyin": "jué xīn", "han_viet": "Quyết tâm", "meaning_vi": "Ý chí kiên định", "nuance_note": "Mạnh mẽ", "visual_action": "Nắm chặt bàn tay"},
                {"level": 5, "hsk": "HSK 5", "hanzi": "破釜沉舟", "pinyin": "pò fǔ chén zhōu", "han_viet": "Phá phủ trầm chu", "meaning_vi": "Quyết tử một phen", "nuance_note": "Tuyệt đối", "visual_action": "Vung tay mạnh mẽ"}
            ]),
            ("Đoàn Kết", [
                {"level": 1, "hsk": "HSK 1", "hanzi": "和", "pinyin": "hé", "han_viet": "Hòa", "meaning_vi": "Cùng với", "nuance_note": "Cơ bản", "visual_action": "Đứng cạnh nhau"},
                {"level": 2, "hsk": "HSK 2", "hanzi": "同", "pinyin": "tóng", "han_viet": "Đồng", "meaning_vi": "Chung một", "nuance_note": "Gắn kết", "visual_action": "Bắt tay"},
                {"level": 3, "hsk": "HSK 3", "hanzi": "合作", "pinyin": "hé zuò", "han_viet": "Hợp tác", "meaning_vi": "Hợp tác", "nuance_note": "Chủ động", "visual_action": "Khoác vai"},
                {"level": 4, "hsk": "HSK 4", "hanzi": "团结", "pinyin": "tuán jié", "han_viet": "Đoàn kết", "meaning_vi": "Đồng lòng", "nuance_note": "Vững chắc", "visual_action": "Nắm tay đồng đội"},
                {"level": 5, "hsk": "HSK 5", "hanzi": "万众一心", "pinyin": "wàn zhòng yī xīn", "han_viet": "Vạn chúng nhất tâm", "meaning_vi": "Muôn người như một", "nuance_note": "Tuyệt đối", "visual_action": "Giơ cao tay đồng thanh"}
            ]),
            ("Kiên Trì", [
                {"level": 1, "hsk": "HSK 1", "hanzi": "做", "pinyin": "zuò", "han_viet": "Tác", "meaning_vi": "Làm", "nuance_note": "Bắt đầu", "visual_action": "Bắt tay vào làm"},
                {"level": 2, "hsk": "HSK 2", "hanzi": "续", "pinyin": "xù", "han_viet": "Tục", "meaning_vi": "Nối tiếp", "nuance_note": "Không ngừng", "visual_action": "Giơ tay nối"},
                {"level": 3, "hsk": "HSK 3", "hanzi": "坚持", "pinyin": "jiān chí", "han_viet": "Kiên trì", "meaning_vi": "Giữ vững", "nuance_note": "Bền bỉ", "visual_action": "Nắm chặt tay"},
                {"level": 4, "hsk": "HSK 4", "hanzi": "坚韧", "pinyin": "jiān rèn", "han_viet": "Kiên nhẫn", "meaning_vi": "Bền bỉ chịu đựng", "nuance_note": "Dẻo dai", "visual_action": "Đứng vững vàng"},
                {"level": 5, "hsk": "HSK 5", "hanzi": "锲而不舍", "pinyin": "qiè ér bù shě", "han_viet": "Khiết nhi bất xả", "meaning_vi": "Kiên trì không bỏ cuộc", "nuance_note": "Bất khuất", "visual_action": "Bước lên phía trước"}
            ]),
            ("Hy Vọng", [
                {"level": 1, "hsk": "HSK 1", "hanzi": "盼", "pinyin": "pàn", "han_viet": "Phán", "meaning_vi": "Mong", "nuance_note": "Ngóng trông", "visual_action": "Nhìn xa xăm"},
                {"level": 2, "hsk": "HSK 2", "hanzi": "望", "pinyin": "wàng", "han_viet": "Vọng", "meaning_vi": "Trông chờ", "nuance_note": "Hy vọng", "visual_action": "Đưa mắt tìm"},
                {"level": 3, "hsk": "HSK 3", "hanzi": "希望", "pinyin": "xī wàng", "han_viet": "Hy vọng", "meaning_vi": "Mong ước", "nuance_note": "Kỳ vọng", "visual_action": "Đặt tay lên ngực"},
                {"level": 4, "hsk": "HSK 4", "hanzi": "渴望", "pinyin": "kě wàng", "han_viet": "Khát khao", "meaning_vi": "Cháy bỏng", "nuance_note": "Chờ đợi", "visual_action": "Vươn hai tay"},
                {"level": 5, "hsk": "HSK 5", "hanzi": "翘首以盼", "pinyin": "qiáo shǒu yǐ pàn", "han_viet": "Kiều thủ dĩ phán", "meaning_vi": "Đăm đăm ngóng đợi", "nuance_note": "Thiết tha", "visual_action": "Kiễng chân ngóng nhìn"}
            ]),
            ("Thành Công", [
                {"level": 1, "hsk": "HSK 1", "hanzi": "成", "pinyin": "chéng", "han_viet": "Thành", "meaning_vi": "Xong", "nuance_note": "Hoàn thành", "visual_action": "Gật đầu"},
                {"level": 2, "hsk": "HSK 2", "hanzi": "赢", "pinyin": "yíng", "han_viet": "Doanh", "meaning_vi": "Thắng", "nuance_note": "Đạt được", "visual_action": "Mỉm cười"},
                {"level": 3, "hsk": "HSK 3", "hanzi": "成功", "pinyin": "chéng gōng", "han_viet": "Thành công", "meaning_vi": "Đạt mục tiêu", "nuance_note": "Vang dội", "visual_action": "Giơ tay chữ V"},
                {"level": 4, "hsk": "HSK 4", "hanzi": "胜利", "pinyin": "shèng lì", "han_viet": "Thắng lợi", "meaning_vi": "Vượt qua thử thách", "nuance_note": "Vinh quang", "visual_action": "Nắm tay ăn mừng"},
                {"level": 5, "hsk": "HSK 5", "hanzi": "功成名就", "pinyin": "gōng chéng míng jiù", "han_viet": "Công thành danh toại", "meaning_vi": "Đỉnh cao danh vọng", "nuance_note": "Rực rỡ", "visual_action": "Dang rộng hai tay"}
            ]),
            ("Sáng Tạo", [
                {"level": 1, "hsk": "HSK 1", "hanzi": "弄", "pinyin": "nòng", "han_viet": "Lộng", "meaning_vi": "Làm ra", "nuance_note": "Cơ bản", "visual_action": "Đưa tay tạo hình"},
                {"level": 2, "hsk": "HSK 2", "hanzi": "变", "pinyin": "biàn", "han_viet": "Biến", "meaning_vi": "Đổi", "nuance_note": "Đổi mới", "visual_action": "Xoay bàn tay"},
                {"level": 3, "hsk": "HSK 3", "hanzi": "创新", "pinyin": "chuàng xīn", "han_viet": "Đổi mới", "meaning_vi": "Cách tân", "nuance_note": "Tiến bộ", "visual_action": "Mở rộng hai tay"},
                {"level": 4, "hsk": "HSK 4", "hanzi": "创造", "pinyin": "chuàng zào", "han_viet": "Sáng tạo", "meaning_vi": "Kiến tạo", "nuance_note": "Bứt phá", "visual_action": "Đưa tay lên trán"},
                {"level": 5, "hsk": "HSK 5", "hanzi": "独树一帜", "pinyin": "dú shù yī zhì", "han_viet": "Độc thụ nhất xí", "meaning_vi": "Độc nhất vô nhị", "nuance_note": "Phong cách riêng", "visual_action": "Chỉ tay khẳng định"}
            ]),
            ("Khen Ngợi", [
                {"level": 1, "hsk": "HSK 1", "hanzi": "夸", "pinyin": "kuā", "han_viet": "Khoa", "meaning_vi": "Khen", "nuance_note": "Lời khen trực tiếp", "visual_action": "Vỗ tay"},
                {"level": 2, "hsk": "HSK 2", "hanzi": "赞", "pinyin": "zàn", "han_viet": "Tán", "meaning_vi": "Khen ngợi", "nuance_note": "Khen ngợi đơn giản", "visual_action": "Giơ ngón cái"},
                {"level": 3, "hsk": "HSK 3", "hanzi": "表扬", "pinyin": "biǎo yáng", "han_viet": "Biểu dương", "meaning_vi": "Tuyên dương", "nuance_note": "Khen ngợi công khai", "visual_action": "Trao giấy khen"},
                {"level": 4, "hsk": "HSK 4", "hanzi": "赞赏", "pinyin": "zàn shǎng", "han_viet": "Tán thưởng", "meaning_vi": "Đánh giá cao", "nuance_note": "Thưởng thức sâu sắc", "visual_action": "Gật đầu tán thưởng"},
                {"level": 5, "hsk": "HSK 5", "hanzi": "赞不绝口", "pinyin": "zàn bù jué kǒu", "han_viet": "Tán bất tuyệt khẩu", "meaning_vi": "Khen không dứt lời", "nuance_note": "Ca ngợi hết lời", "visual_action": "Hai tay giơ ngón cái liên tục"}
            ]),
            ("Kính Trọng", [
                {"level": 1, "hsk": "HSK 1", "hanzi": "敬", "pinyin": "jìng", "han_viet": "Kính", "meaning_vi": "Kính cẩn", "nuance_note": "Tôn kính cơ bản", "visual_action": "Cúi đầu nhẹ"},
                {"level": 2, "hsk": "HSK 2", "hanzi": "尊", "pinyin": "zūn", "han_viet": "Tôn", "meaning_vi": "Tôn trọng", "nuance_note": "Đặt ở vị trí cao", "visual_action": "Đứng nghiêm"},
                {"level": 3, "hsk": "HSK 3", "hanzi": "尊重", "pinyin": "zūn zhòng", "han_viet": "Tôn trọng", "meaning_vi": "Coi trọng phẩm giá", "nuance_note": "Lắng nghe chăm chú", "visual_action": "Chắp tay nhẹ"},
                {"level": 4, "hsk": "HSK 4", "hanzi": "崇敬", "pinyin": "chóng jìng", "han_viet": "Sùng kính", "meaning_vi": "Tôn sùng ngưỡng mộ", "nuance_note": "Đặt tay lên tim", "visual_action": "Cúi mình kính cẩn"},
                {"level": 5, "hsk": "HSK 5", "hanzi": "肃然起敬", "pinyin": "sù rán qǐ jìng", "han_viet": "Túc nhiên khởi kính", "meaning_vi": "Bỗng sinh lòng tôn kính", "nuance_note": "Cảm phục sâu sắc", "visual_action": "Đứng thẳng chắp tay"}
            ])
        ]
    }

    for attempt in range(max_retries):
        if attempt > 0:
            time.sleep(1.5)
        ai_data, provider = rotator.generate_quiz_ideas(sys_prompt, user_prompt)
        batches = ai_data if isinstance(ai_data, list) else ((ai_data or {}).get("batches") or (ai_data or {}).get("concepts") or (ai_data or {}).get("topics") or [ai_data])
        if not batches or not isinstance(batches[0], dict):
            continue

        b = batches[0]
        if tab == "multilevels":
            raw_concept = b.get("concept_name_vi", "") or b.get("concept", f"Khái niệm #{row_idx}")
            topic_title = clean_quiz_topic(raw_concept, tab="multilevels")
            clean_concept = topic_title.replace("1 Nghĩa 5 Cấp •", "").strip()
            raw_levels = b.get("levels", [])
            if len(raw_levels) < 5:
                continue

            batch_to_val = {"concept_name_vi": clean_concept or raw_concept, "levels": raw_levels}
            is_valid_ml, ml_errs = MultilevelsEscalationValidator.validate_multilevels_batch(batch_to_val)
            if not is_valid_ml:
                continue

            candidate_words = [{"hanzi": l.get("hanzi", "")} for l in raw_levels]
            is_valid_overlap, ratio, overlap_list, reason = matrix.evaluate_candidate_batch(candidate_words, topic=topic_title, tab="multilevels")
            if not is_valid_overlap:
                continue

            norm_levels = []
            for lvl_idx, l in enumerate(raw_levels[:5]):
                lvl_num = lvl_idx + 1
                hz_str = l.get("hanzi", "").strip()
                py_str = normalize_pinyin_spacing(hz_str, l.get("pinyin", "").strip())
                norm_levels.append({
                    "level": lvl_num,
                    "hsk": l.get("hsk", f"HSK {lvl_num}"),
                    "hanzi": hz_str,
                    "pinyin": py_str,
                    "sino_vietnamese": (l.get("han_viet") or l.get("sino_vietnamese") or "").strip(),
                    "meaning": (l.get("meaning_vi") or l.get("meaning") or "").strip(),
                    "nuance": (l.get("nuance_note") or l.get("nuance") or "").strip(),
                    "action": (l.get("visual_action") or l.get("action") or "").strip()
                })

            rid = f"#{row_idx}"
            w_cols = [f"{lvl['hanzi']} | {lvl['pinyin']} | {lvl['sino_vietnamese']} | {lvl['meaning']} | {lvl['nuance']} | {lvl['action']}" for lvl in norm_levels]
            meta_txt = build_multilevels_metadata(str(row_idx), clean_concept or "Khái niệm", norm_levels)
            now_str = get_vietnam_now_str()
            row_data = [rid, topic_title, "HSK 1-5", "Pending"] + w_cols + [meta_txt, "", "", "", "", now_str, f"Tự động tái tạo in-place bởi {provider} ({now_str} GMT+7)"]
            sanitized = validate_and_sanitize_row(row_data, expected_row_idx=row_idx)
            matrix.register_ingested_batch("multilevels", [{"hanzi": l["hanzi"]} for l in norm_levels], topic=topic_title)
            return sanitized, provider

        else:
            raw_topic = b.get("topic", f"Chủ Đề #{row_idx}").strip()
            clean_t = clean_quiz_topic(raw_topic, tab=tab)
            level = b.get("level", "HSK 2")
            raw_words = b.get("words", [])
            if len(raw_words) < 5:
                continue

            candidate_words = []
            has_dummy = False
            for w in raw_words[:5]:
                hz = w.get("hanzi", "").strip()
                py = normalize_pinyin_spacing(hz, w.get("pinyin", "").strip())
                mn = w.get("meaning", "").strip()
                if is_dummy_word(hz, py, mn):
                    has_dummy = True
                    break
                candidate_words.append({"hanzi": hz, "pinyin": py, "meaning": mn})

            if has_dummy or len(candidate_words) < 5:
                continue

            is_valid_overlap, ratio, overlap_list, reason = matrix.evaluate_candidate_batch(candidate_words, topic=clean_t, tab=tab)
            if not is_valid_overlap:
                continue

            pinyin_passed = True
            for w in candidate_words:
                p_valid, p_errs = PinyinLinguisticValidator.validate_pinyin(w["hanzi"], w["pinyin"])
                if not p_valid:
                    pinyin_passed = False
                    break
            if not pinyin_passed:
                continue

            rid = f"#{row_idx}"
            if tab == "vocabVN":
                w_cols = [f"{w['meaning']} | {w['pinyin']} | {w['hanzi']}" for w in candidate_words]
                meta_txt = build_vocabvn_metadata(str(row_idx), clean_t, level, candidate_words)
            elif tab == "vocabCN":
                w_cols = [f"{w['hanzi']} | {w['pinyin']} | {w['meaning']}" for w in candidate_words]
                meta_txt = build_vocabcn_metadata(str(row_idx), clean_t, level, candidate_words)
            else:  # pinyin
                w_cols = [f"{w['hanzi']} | {w['pinyin']} | {w['meaning']}" for w in candidate_words]
                meta_txt = build_pinyin_metadata(str(row_idx), clean_t, level, candidate_words)

            now_str = get_vietnam_now_str()
            row_data = [rid, clean_t, level, "Pending"] + w_cols + [meta_txt, "", "", "", "", now_str, f"Tự động tái tạo in-place bởi {provider} ({now_str} GMT+7)"]
            sanitized = validate_and_sanitize_row(row_data, expected_row_idx=row_idx)
            matrix.register_ingested_batch(tab, candidate_words, topic=clean_t)
            return sanitized, provider

    # Offline Verified Bank Fallback
    print(f"  ⚡ Activating Offline Fallback Bank for tab '{tab}' row #{row_idx}...")
    bank_candidates = FALLBACK_BANK.get(tab, [])
    for cand in bank_candidates:
        if tab == "multilevels":
            concept_name, levels_data = cand
            topic_title = clean_quiz_topic(concept_name, tab="multilevels")
            norm_t = normalize_topic_string(topic_title)
            if norm_t in [normalize_topic_string(t) for t in existing_topics]:
                continue
            cand_words = [{"hanzi": l["hanzi"]} for l in levels_data]
            is_valid_ov, _, _, _ = matrix.evaluate_candidate_batch(cand_words, topic=topic_title, tab="multilevels")
            if not is_valid_ov:
                continue
            rid = f"#{row_idx}"
            w_cols = [f"{l['hanzi']} | {l['pinyin']} | {l['han_viet']} | {l['meaning_vi']} | {l['nuance_note']} | {l['visual_action']}" for l in levels_data]
            meta_txt = build_multilevels_metadata(str(row_idx), concept_name, levels_data)
            now_str = get_vietnam_now_str()
            row_data = [rid, topic_title, "HSK 1-5", "Pending"] + w_cols + [meta_txt, "", "", "", "", now_str, f"Tự động tái tạo in-place bởi Offline Verified Bank ({now_str} GMT+7)"]
            sanitized = validate_and_sanitize_row(row_data, expected_row_idx=row_idx)
            matrix.register_ingested_batch("multilevels", cand_words, topic=topic_title)
            return sanitized, "Offline Verified Bank"
        else:
            cand_topic, cand_level, words_tuples = cand
            clean_t = clean_quiz_topic(cand_topic, tab=tab)
            norm_t = normalize_topic_string(clean_t)
            if norm_t in [normalize_topic_string(t) for t in existing_topics]:
                continue
            if tab == "vocabVN":
                cand_words = [{"meaning": m, "pinyin": p, "hanzi": h} for m, p, h in words_tuples]
            else:
                cand_words = [{"hanzi": h, "pinyin": p, "meaning": m} for h, p, m in words_tuples]
            is_valid_ov, _, _, _ = matrix.evaluate_candidate_batch(cand_words, topic=clean_t, tab=tab)
            if not is_valid_ov:
                continue
            rid = f"#{row_idx}"
            if tab == "vocabVN":
                w_cols = [f"{w['meaning']} | {w['pinyin']} | {w['hanzi']}" for w in cand_words]
                meta_txt = build_vocabvn_metadata(str(row_idx), clean_t, cand_level, cand_words)
            elif tab == "vocabCN":
                w_cols = [f"{w['hanzi']} | {w['pinyin']} | {w['meaning']}" for w in cand_words]
                meta_txt = build_vocabcn_metadata(str(row_idx), clean_t, cand_level, cand_words)
            else:
                w_cols = [f"{w['hanzi']} | {w['pinyin']} | {w['meaning']}" for w in cand_words]
                meta_txt = build_pinyin_metadata(str(row_idx), clean_t, cand_level, cand_words)
            now_str = get_vietnam_now_str()
            row_data = [rid, clean_t, cand_level, "Pending"] + w_cols + [meta_txt, "", "", "", "", now_str, f"Tự động tái tạo in-place bởi Offline Verified Bank ({now_str} GMT+7)"]
            sanitized = validate_and_sanitize_row(row_data, expected_row_idx=row_idx)
            matrix.register_ingested_batch(tab, cand_words, topic=clean_t)
            return sanitized, "Offline Verified Bank"

    return None, "Failed after max retries and fallback bank exhausted"


def audit_and_repair_tab(
    ss: gspread.Spreadsheet,
    tab: str,
    rotator,
    matrix: GlobalHanziFrequencyMatrix,
    dry_run: bool = False,
    fix_spirit: bool = True,
    target_row_indices: Optional[Set[int]] = None
) -> Dict[str, Any]:
    """
    Audits an entire tab history:
    - Finds duplicates (topic matching an earlier row).
    - Finds invalid spirit rows (banned phonetic theory or overly long topic).
    - If dry_run=False, regenerates those rows in-place without deleting rows.
    """
    ws = ss.worksheet(tab)
    rows = ws.get_all_values()
    if not rows or len(rows) < 2:
        return {"tab": tab, "scanned_rows": 0, "duplicates_found": [], "invalid_spirit_found": [], "repaired_rows": []}

    seen_topics: Dict[str, int] = {}
    seen_row_words: List[Dict[str, Any]] = []
    duplicates_found: List[Dict[str, Any]] = []
    invalid_spirit_found: List[Dict[str, Any]] = []
    word_overlap_violations: List[Dict[str, Any]] = []
    rows_to_repair: List[int] = []

    for idx, r in enumerate(rows[1:], start=2):
        if not r or len(r) < 2:
            continue

        row_id = r[0].strip() if len(r) > 0 else f"#{idx}"
        raw_topic = r[1].strip() if len(r) > 1 else ""
        status = r[3].strip() if len(r) > 3 else "Pending"
        norm_t = normalize_topic_string(raw_topic)

        # 1. Topic Duplicate Check
        is_dup = False
        if norm_t:
            if norm_t in seen_topics:
                is_dup = True
                first_seen_row = seen_topics[norm_t]
                duplicates_found.append({
                    "row_idx": idx,
                    "row_id": row_id,
                    "topic": raw_topic,
                    "status": status,
                    "matches_row": first_seen_row,
                })
            else:
                seen_topics[norm_t] = idx

        # 2. Topic Spirit Check
        is_invalid_spirit = False
        if fix_spirit and raw_topic:
            valid_spirit, spirit_errs = validate_topic_spirit(raw_topic, tab)
            if not valid_spirit:
                is_invalid_spirit = True
                invalid_spirit_found.append({
                    "row_idx": idx,
                    "row_id": row_id,
                    "topic": raw_topic,
                    "status": status,
                    "errors": spirit_errs,
                })

        # 3. Pairwise Word Overlap Check (Max allowed duplicate words between any two rows is <= 2)
        is_word_overlap_violation = False
        words_list, _ = matrix._extract_hanzi_and_words_from_row(tab, r)
        current_words = set(words_list)
        if current_words:
            for past_row in seen_row_words:
                shared_w = current_words.intersection(past_row["words"])
                if len(shared_w) >= 3:
                    is_word_overlap_violation = True
                    word_overlap_violations.append({
                        "row_idx": idx,
                        "row_id": row_id,
                        "topic": raw_topic,
                        "status": status,
                        "matches_row": past_row["row_idx"],
                        "matches_id": past_row["row_id"],
                        "matches_topic": past_row["topic"],
                        "overlapping_words": sorted(list(shared_w))
                    })
                    break
            seen_row_words.append({
                "row_idx": idx,
                "row_id": row_id,
                "topic": raw_topic,
                "status": status,
                "words": current_words
            })

        # Check if row should be repaired
        if target_row_indices is not None:
            if idx in target_row_indices:
                rows_to_repair.append(idx)
        else:
            # If it's a duplicate and status is Pending/Ready/Video
            if is_dup and status in ["Pending", "Ready", "Video"]:
                rows_to_repair.append(idx)
            elif is_invalid_spirit and status in ["Pending", "Ready"]:
                # If earlier published video, don't break existing video unless forced
                rows_to_repair.append(idx)
            elif is_word_overlap_violation and status in ["Pending", "Ready", "Video"]:
                # If non-published video shares >= 3 words with any earlier row, repair in-place!
                rows_to_repair.append(idx)

    repaired_rows: List[Dict[str, Any]] = []

    print(f"\n📊 [Tab: {tab}] Scanned {len(rows)-1} rows.")
    print(f"  • Duplicates found: {len(duplicates_found)}")
    print(f"  • Invalid spirit found: {len(invalid_spirit_found)}")
    print(f"  • Word overlap >= 3 violations: {len(word_overlap_violations)}")
    print(f"  • Rows queued for in-place repair: {len(rows_to_repair)}")

    if not dry_run and rows_to_repair:
        print(f"  ⚡ Executing in-place repairs for {len(rows_to_repair)} row(s)...")
        for r_idx in sorted(rows_to_repair):
            old_row = rows[r_idx - 1]
            old_topic = old_row[1] if len(old_row) > 1 else ""
            print(f"    ▶ Repairing Row #{r_idx} (Old Topic: '{old_topic}')...")

            new_row_data, provider = generate_fresh_batch_for_tab(tab, r_idx, rotator, matrix)
            if new_row_data:
                # In-place cell update in worksheet using keyword arguments
                ws.update(range_name=f"A{r_idx}:P{r_idx}", values=[new_row_data])
                new_topic = new_row_data[1]
                repaired_rows.append({
                    "row_idx": r_idx,
                    "old_topic": old_topic,
                    "new_topic": new_topic,
                    "provider": provider
                })
                print(f"    ✓ Row #{r_idx} successfully replaced in-place: '{new_topic}' (via {provider})")
            else:
                print(f"    ❌ Failed to generate valid replacement for Row #{r_idx}")
            time.sleep(1.0)

    return {
        "tab": tab,
        "scanned_rows": len(rows) - 1,
        "duplicates_found": duplicates_found,
        "invalid_spirit_found": invalid_spirit_found,
        "word_overlap_violations": word_overlap_violations,
        "repaired_rows": repaired_rows,
        "dry_run": dry_run
    }


def main():
    parser = argparse.ArgumentParser(description="Audit and Repair Historical Duplicates in Quiz Google Sheet")
    parser.add_argument("--tab", "-t", default="all", help="Target tab ('all', 'pinyin', 'vocabCN', 'vocabVN', 'multilevels')")
    parser.add_argument("--dry-run", action="store_true", help="Audit only without modifying Google Sheet")
    parser.add_argument("--no-fix-spirit", action="store_true", help="Do not fix phonetic theory / spirit issues, only exact duplicate topics")
    parser.add_argument("--rows", "-r", type=str, default="", help="Comma-separated row indices to force repair (e.g. '56,57,58,62')")
    args = parser.parse_args()

    normalized = normalize_tab_name(args.tab)
    target_tabs = VALID_TABS if normalized == "all" else [normalized]

    target_row_set = None
    if args.rows.strip():
        target_row_set = {int(x.strip()) for x in args.rows.split(",") if x.strip().isdigit()}

    mode_str = "[DRY RUN AUDIT]" if args.dry_run else "[LIVE IN-PLACE REPAIR]"
    print(f"🔍 === Starting Quiz Historical Deduplication & In-Place Repair Engine {mode_str} ===")
    print(f"  Target Tabs: {target_tabs}")

    gc = get_gspread_client()
    ss = gc.open_by_key(SPREADSHEET_ID)
    rotator = get_ai_rotator()
    matrix = GlobalHanziFrequencyMatrix(spreadsheet_client=gc, spreadsheet_id=SPREADSHEET_ID)

    all_results = []
    total_repaired = 0

    for t in target_tabs:
        res = audit_and_repair_tab(
            ss=ss,
            tab=t,
            rotator=rotator,
            matrix=matrix,
            dry_run=args.dry_run,
            fix_spirit=not args.no_fix_spirit,
            target_row_indices=target_row_set
        )
        all_results.append(res)
        total_repaired += len(res["repaired_rows"])

    if not args.dry_run and total_repaired > 0:
        print("\n📏 Enforcing strict 21px row height invariant across all tabs after repairs...")
        try:
            enforcer = RowHeightEnforcer()
            enforcer.enforce_all(force=True)
            print("✓ 21px Row Height Invariant successfully enforced.")
        except Exception as e:
            print(f"⚠ Warning: Could not run row height enforcer: {e}")

    # Build Telegram Summary Report
    now_vn = get_vietnam_now_str()
    report_lines = [
        f"<b>🛡️ BÁO CÁO KIỂM TRA TRÙNG LẶP LỊCH SỬ QUIZ</b>",
        f"<i>Thời gian: {now_vn} (GMT+7) | Chế độ: {mode_str}</i>",
        "───────────────────────────────"
    ]

    for r in all_results:
        tab_name = r["tab"]
        dups = r["duplicates_found"]
        spirits = r["invalid_spirit_found"]
        overlaps = r.get("word_overlap_violations", [])
        repaired = r["repaired_rows"]
        report_lines.append(f"<b>📌 Tab: {tab_name}</b> ({r['scanned_rows']} hàng)")
        if dups:
            dup_ids = ", ".join(f"#{d['row_idx']}" for d in dups)
            report_lines.append(f"  • Trùng lặp phát hiện: {len(dups)} hàng ({dup_ids})")
        if spirits:
            spirit_ids = ", ".join(f"#{s['row_idx']}" for s in spirits)
            report_lines.append(f"  • Sai tinh thần quiz/lý thuyết: {len(spirits)} hàng ({spirit_ids})")
        if overlaps:
            overlap_ids = ", ".join(f"#{o['row_idx']}" for o in overlaps)
            report_lines.append(f"  • Trùng từ vựng (≥3 từ): {len(overlaps)} hàng ({overlap_ids})")
        if repaired:
            rep_strs = [f"#{x['row_idx']} ➔ '{x['new_topic']}'" for x in repaired]
            report_lines.append(f"  • <b>Đã tái tạo in-place ({len(repaired)}):</b>\n    " + "\n    ".join(rep_strs))
        if not dups and not spirits and not overlaps:
            report_lines.append(f"  • <i>Hoàn toàn sạch, không trùng lặp!</i>")
        report_lines.append("")

    report_msg = "\n".join(report_lines)
    print("\n" + report_msg)

    if not args.dry_run and total_repaired > 0:
        send_telegram_alert(report_msg)

    print(f"\n🎉 Historical Deduplication Engine Completed Successfully! (Total Repaired: {total_repaired})")


if __name__ == "__main__":
    main()

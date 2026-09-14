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
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "-1004392602002")
    if not token:
        env_file = os.path.expanduser("~/.cloud-profiles/lelehoctiengtrung/telegram/telegram.env")
        if os.path.exists(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("TELEGRAM_BOT_TOKEN="):
                            token = line.split("=", 1)[1].strip()
                        elif line.startswith("TELEGRAM_CHAT_ID="):
                            chat_id = line.split("=", 1)[1].strip()
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
            ("Đồ Nghề Sửa Chữa", "HSK 3", [("锤子", "chuí zi", "cái búa"), ("螺丝", "luó sī", "ốc vít"), ("尺子", "chǐ zi", "cái thước"), ("胶水", "jiāo shuǐ", "keo dán"), ("剪刀", "jiǎn dāo", "cái kéo")]),
            ("Thời Tiết Khắc Nghiệt", "HSK 3", [("暴雨", "bào yǔ", "mưa bão"), ("台风", "tái fēng", "bão lớn"), ("闪电", "shǎn diàn", "sấm sét"), ("大雾", "dà wù", "sương mù dày"), ("冰雹", "bīng báo", "mưa đá")]),
            ("Nhạc Cụ Âm Nhạc", "HSK 3", [("吉他", "jí tā", "đàn ghi-ta"), ("钢琴", "gāng qín", "đàn piano"), ("笛子", "dí zi", "cây sáo"), ("鼓", "gǔ", "cái trống"), ("小提琴", "xiǎo tí qín", "đàn vĩ cầm")]),
        ],
        "vocabCN": [
            ("Địa Điểm Mua Sắm", "HSK 2", [("商场", "shāng chǎng", "trung tâm thương mại"), ("超市", "chāo shì", "siêu thị"), ("书店", "shū diàn", "hiệu sách"), ("花店", "huā diàn", "tiệm hoa"), ("面包店", "miàn bāo diàn", "tiệm bánh mì")]),
            ("Trang Phục Mặc Ngoài", "HSK 2", [("外套", "wài tào", "áo khoác"), ("衬衫", "chèn shān", "áo sơ mi"), ("裙子", "qún zi", "váy liền"), ("裤子", "kù zi", "quần dài"), ("帽子", "mào zi", "mũ nón")]),
            ("Động Vật Rừng Xanh", "HSK 2", [("狮子", "shī zi", "sư tử"), ("大象", "dà xiàng", "con voi"), ("猴子", "hóu zi", "con khỉ"), ("老虎", "lǎo hǔ", "con hổ"), ("熊猫", "xióng māo", "gấu trúc")]),
        ],
        "vocabVN": [
            ("Dụng Cụ Học Tập", "HSK 1", [("sách vở", "shū běn", "书本"), ("bút viết", "bǐ", "笔"), ("thước kẻ", "chǐ zi", "尺子"), ("cặp sách", "shū bāo", "书包"), ("bản đồ", "dì tú", "地图")]),
            ("Màu Sắc Cơ Bản", "HSK 1", [("màu đỏ", "hóng sè", "红色"), ("màu xanh", "lán sè", "蓝色"), ("màu vàng", "huáng sè", "黄色"), ("màu đen", "hēi sè", "黑色"), ("màu trắng", "bái sè", "白色")]),
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
    duplicates_found: List[Dict[str, Any]] = []
    invalid_spirit_found: List[Dict[str, Any]] = []
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

        # Check if row should be repaired
        if target_row_indices is not None:
            if idx in target_row_indices:
                rows_to_repair.append(idx)
        else:
            # If it's a duplicate and status is Pending/Ready, or if it has invalid theory topic
            if is_dup and status in ["Pending", "Ready", "Video"]:
                rows_to_repair.append(idx)
            elif is_invalid_spirit and status in ["Pending", "Ready"]:
                # If earlier published video, don't break existing video unless forced
                rows_to_repair.append(idx)

    repaired_rows: List[Dict[str, Any]] = []

    print(f"\n📊 [Tab: {tab}] Scanned {len(rows)-1} rows.")
    print(f"  • Duplicates found: {len(duplicates_found)}")
    print(f"  • Invalid spirit found: {len(invalid_spirit_found)}")
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
        repaired = r["repaired_rows"]
        report_lines.append(f"<b>📌 Tab: {tab_name}</b> ({r['scanned_rows']} hàng)")
        if dups:
            dup_ids = ", ".join(f"#{d['row_idx']}" for d in dups)
            report_lines.append(f"  • Trùng lặp phát hiện: {len(dups)} hàng ({dup_ids})")
        if spirits:
            spirit_ids = ", ".join(f"#{s['row_idx']}" for s in spirits)
            report_lines.append(f"  • Sai tinh thần quiz/lý thuyết: {len(spirits)} hàng ({spirit_ids})")
        if repaired:
            rep_strs = [f"#{x['row_idx']} ➔ '{x['new_topic']}'" for x in repaired]
            report_lines.append(f"  • <b>Đã tái tạo in-place ({len(repaired)}):</b>\n    " + "\n    ".join(rep_strs))
        if not dups and not spirits:
            report_lines.append(f"  • <i>Hoàn toàn sạch, không trùng lặp!</i>")
        report_lines.append("")

    report_msg = "\n".join(report_lines)
    print("\n" + report_msg)

    if not args.dry_run and total_repaired > 0:
        send_telegram_alert(report_msg)

    print(f"\n🎉 Historical Deduplication Engine Completed Successfully! (Total Repaired: {total_repaired})")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/run_ideation_dispatcher.py
Central Dispatcher for Quiz Ideation across all 4 tabs:
- pinyin (tab: 'pinyin')
- vocabCN (tab: 'vocabCN')
- vocabVN (tab: 'vocabVN')
- multilevels (tab: 'multilevels')

Powered by Multi-Provider AI Key Rotator:
- 6 Gemini API keys (gemini-3.6-flash & gemini-3.7-flash)
- 4 Agnes AI API keys (apihub.agnes-ai.com)
- Strict 16 standard columns & status 'Pending'
- Independent worksheet binding (zero cross-tab leakage)
- Strict 21px row height invariant
"""

import os
import sys
import json
import re
import time
import argparse
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Set, Optional, Tuple

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

QUIZ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if QUIZ_ROOT not in sys.path:
    sys.path.insert(0, QUIZ_ROOT)

import gspread
from google.oauth2.service_account import Credentials
from scripts.enforce_row_height_21px import RowHeightEnforcer
from scripts.ai_key_rotator import get_ai_rotator

SPREADSHEET_ID = "1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0"
STANDARD_COLUMNS = [
    "#", "Topic", "Level", "Status",
    "Word 1", "Word 2", "Word 3", "Word 4", "Word 5",
    "metadata", "Video", "Youtube", "Tiktok", "Facebook",
    "Created At", "Notes"
]


def get_vietnam_now_str() -> str:
    tz_vn = timezone(timedelta(hours=7))
    return datetime.now(tz_vn).strftime("%Y-%m-%d %H:%M:%S")


def get_gspread_client() -> gspread.Client:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    env_json = os.getenv("GCP_SERVICE_ACCOUNT_KEY") or os.getenv("GCP_SERVICE_ACCOUNT_JSON") or os.getenv("SERVICE_ACCOUNT_JSON")
    if env_json and env_json.strip():
        try:
            info = json.loads(env_json)
            creds = Credentials.from_service_account_info(info, scopes=scopes)
            return gspread.authorize(creds)
        except Exception as e:
            print(f"  ⚠ Failed to parse service account from env: {e}")

    candidates = [
        os.path.expanduser("~/.cloud-profiles/lelehoctiengtrung/google_sa/service_account.json"),
        os.path.join(QUIZ_ROOT, "configs", "service_account.json"),
        os.path.expanduser("~/.config/gspread/service_account.json")
    ]
    for p in candidates:
        if os.path.exists(p) and os.path.getsize(p) > 10:
            creds = Credentials.from_service_account_file(p, scopes=scopes)
            return gspread.authorize(creds)

    raise RuntimeError("No valid Google service account credentials found.")


def extract_existing_hanzi(rows: List[List[str]]) -> Set[str]:
    """Extracts all existing Hanzi characters/words to prevent topic/word duplication."""
    existing = set()
    for r in rows[1:]:
        for col_idx in range(4, min(9, len(r))):
            val = r[col_idx] if len(r) > col_idx else ""
            if val and "|" in val:
                parts = [p.strip() for p in val.split("|")]
                for p in parts:
                    for char in p:
                        if "\u4e00" <= char <= "\u9fff":
                            existing.add(char)
            elif val:
                for char in val:
                    if "\u4e00" <= char <= "\u9fff":
                        existing.add(char)
    return existing


# ==============================================================================
# METADATA GENERATORS
# ==============================================================================

def build_pinyin_metadata(batch_id: str, topic: str, level: str, words: List[Dict[str, str]]) -> str:
    word_lines = "\n".join([f"• {w['hanzi']} ({w['pinyin']}): {w['meaning']}" for w in words])
    return f"""📝 METADATA CHO VIDEO: {topic} ({level})
───────────────────────────────────────────────────────────────────

【 1. YOUTUBE SHORTS 】
Tiêu đề (Title):
Thử Thách Phát Âm Pinyin: {topic} ({level}) 🎯 | Lê Lê Học Tiếng Trung #Shorts

Mô tả (Description):
🎯 Thử tài phát âm và nhận diện Pinyin chuẩn xác cùng Lê Lê!
Chủ đề hôm nay: {topic} ({level})

📚 TỪ VỰNG TRONG VIDEO:
{word_lines}

💬 Bạn phát âm đúng bao nhiêu từ? Hãy để lại bình luận nhé! 👇
🔔 Đăng ký kênh @lelehoctiengtrung để học tiếng Trung mỗi ngày!

【 2. TIKTOK 】
Caption & Hashtags:
Thử thách phát âm Pinyin chuẩn cùng Lê Lê! Chủ đề: {topic} ({level}) 🎯 Bạn đúng bao nhiêu từ? 👇 #lelehoctiengtrung #tiengtrung #pinyin #hsk #hoctiengtrung

【 3. FACEBOOK REELS 】
Caption & Hashtags:
Luyện phản xạ Pinyin tiếng Trung mỗi ngày: {topic} ({level})! ✨ Cùng kiểm tra xem bạn phát âm đúng bao nhiêu từ nha! #lelehoctiengtrung #tiengtrung #hsk"""


def build_vocabcn_metadata(batch_id: str, topic: str, level: str, words: List[Dict[str, str]]) -> str:
    word_lines = "\n".join([f"• {w['hanzi']} ({w['pinyin']}) ➔ {w['meaning']}" for w in words])
    return f"""📝 METADATA CHO VIDEO: Đoán Nghĩa Tiếng Việt ({topic})
───────────────────────────────────────────────────────────────────

【 1. YOUTUBE SHORTS 】
Tiêu đề (Title):
Đoán Nghĩa Tiếng Việt Trong 5 Giây: {topic} ({level}) ⚡ | Lê Lê Học Tiếng Trung #Shorts

Mô tả (Description):
⚡ Thử thách phản xạ từ vựng tiếng Trung cấp tốc!
Nhìn chữ Hán và chọn nghĩa tiếng Việt chuẩn xác nhất trong 5 giây!

📚 TỪ VỰNG TRONG VIDEO:
{word_lines}

💬 Bạn đạt bao nhiêu điểm? Comment kết quả bên dưới nhé! 👇
🔔 Đăng ký kênh @lelehoctiengtrung để rèn luyện phản xạ tiếng Trung mỗi ngày!

【 2. TIKTOK 】
Caption & Hashtags:
Đoán nghĩa tiếng Việt trong 5 giây! Chủ đề: {topic} ({level}) 🔥 Bạn đạt bao nhiêu điểm? 👇 #lelehoctiengtrung #tiengtrung #vocabquiz #hsk #learnchinese

【 3. FACEBOOK REELS 】
Caption & Hashtags:
Thử tài đoán nghĩa tiếng Trung cấp tốc: {topic} ({level})! ✨ Bạn đúng bao nhiêu từ? Comment cùng Lê Lê nha! #lelehoctiengtrung #tiengtrung #reelsvn"""


def build_vocabvn_metadata(batch_id: str, topic: str, level: str, words: List[Dict[str, str]]) -> str:
    word_lines = "\n".join([f"• {w['meaning']} ➔ {w['hanzi']} ({w['pinyin']})" for w in words])
    return f"""📝 METADATA CHO VIDEO: Đoán Chữ Hán ({topic})
───────────────────────────────────────────────────────────────────

【 1. YOUTUBE SHORTS 】
Tiêu đề (Title):
Đoán Chữ Hán Trong 5 Giây: {topic} ({level}) 🧠 | Lê Lê Học Tiếng Trung #Shorts

Mô tả (Description):
🧠 Nhìn nghĩa tiếng Việt - Đoán ngay chữ Hán chuẩn xác!
Thử thách phản xạ từ vựng cùng Lê Lê: {topic} ({level})

📚 TỪ VỰNG TRONG VIDEO:
{word_lines}

💬 Bạn nhớ được bao nhiêu chữ Hán? Hãy comment bên dưới nhé! 👇
🔔 Đăng ký kênh @lelehoctiengtrung để nâng cao vốn từ vựng HSK mỗi ngày!

【 2. TIKTOK 】
Caption & Hashtags:
Nhìn nghĩa tiếng Việt đoán chữ Hán! Chủ đề: {topic} ({level}) 🎯 Bạn nhớ bao nhiêu chữ? 👇 #lelehoctiengtrung #tiengtrung #hanzi #hsk #learnchinese

【 3. FACEBOOK REELS 】
Caption & Hashtags:
Thử thách đoán Hán tự: {topic} ({level})! ✨ Bạn đạt điểm tuyệt đối không? Comment kết quả nhé! #lelehoctiengtrung #tiengtrung #hsk"""


def build_multilevels_metadata(batch_id: str, concept: str, levels: List[Dict[str, str]]) -> str:
    level_lines = "\n".join([f"• {l.get('hsk', f'HSK {idx+1}')}: {l.get('hanzi', '')} ({l.get('pinyin', '')}) [{l.get('sino_vietnamese', '')}] ➔ {l.get('meaning', '')} ({l.get('nuance', '')})" for idx, l in enumerate(levels)])
    return f"""📝 METADATA CHO VIDEO: 1 Nghĩa 5 Cấp Độ ({concept})
───────────────────────────────────────────────────────────────────

【 1. YOUTUBE SHORTS 】
Tiêu đề (Title):
5 Cấp Độ Từ Vựng '{concept}' (HSK 1 - 5) - Bạn Ở Cấp Mấy? 🎯 | Lê Lê Học Tiếng Trung #Shorts

Mô tả (Description):
🎯 Thử thách phản xạ từ vựng: 1 NGHĨA - 5 CẤP ĐỘ HSK (Chủ đề: {concept.upper()})!
Cứ mỗi 5 giây độ khó sẽ tăng dần từ HSK 1 đến HSK 5. Bạn dừng lại ở cấp độ mấy?

📚 5 CẤP ĐỘ TỪ VỰNG TRONG VIDEO:
{level_lines}

💬 Từ HSK 5 bạn có biết không? Hãy comment điểm số bên dưới nhé! 👇
🔔 Đừng quên bấm Like và Đăng ký kênh @lelehoctiengtrung để học tiếng Trung mỗi ngày!

【 2. TIKTOK 】
Caption & Hashtags:
5 cấp độ từ vựng '{concept}' từ HSK 1 đến HSK 5! 🔥 Bạn dừng ở cấp mấy? Comment kết quả bên dưới nhé! 👇 #lelehoctiengtrung #hoctiengtrung #tiengtrung #hsk #learnchinese

【 3. FACEBOOK REELS 】
Caption & Hashtags:
Thử tài phản xạ: 1 Nghĩa - 5 Cấp độ HSK (Chủ đề: {concept})! ✨ Bạn chinh phục được từ HSK 5 không? #lelehoctiengtrung #tiengtrung #reelsvn"""


# ==============================================================================
# TAB HANDLERS
# ==============================================================================

def ideate_pinyin(ss: gspread.Spreadsheet, count: int, rotator):
    ws = ss.worksheet("pinyin")
    records = ws.get_all_values()
    next_id = len(records)
    existing_hanzi = extract_existing_hanzi(records)
    print(f"\n▶ [Ideation] Processing Tab 'pinyin' (Target: {count} batches)...")
    print(f"  Current rows: {len(records)-1}, Unique Hanzi tracked: {len(existing_hanzi)}")

    sys_prompt = (
        "Bạn là chuyên gia giáo dục Hán ngữ của kênh 'Lê Lê Học Tiếng Trung'. "
        "Nhiệm vụ: Tạo các bộ câu hỏi trắc nghiệm phát âm Pinyin HSK 1-3 cực kỳ chuẩn xác, hấp dẫn, gần gũi. "
        "Output JSON dạng mảng: [{\"topic\": \"Tên chủ đề tiếng Việt\", \"level\": \"HSK 2\", "
        "\"words\": [{\"hanzi\": \"书\", \"pinyin\": \"shū\", \"meaning\": \"sách\"}]}]"
    )
    user_prompt = (
        f"Hãy tạo {count} chủ đề trắc nghiệm Pinyin khác biệt hoàn toàn, mỗi chủ đề gồm đúng 5 từ vựng HSK 1-3. "
        f"Tuyệt đối KHÔNG trùng lặp các chữ Hán sau: {list(existing_hanzi)[-50:]}."
    )

    ai_data, provider = rotator.generate_quiz_ideas(sys_prompt, user_prompt)
    batches = ai_data if isinstance(ai_data, list) else ((ai_data or {}).get("batches") or (ai_data or {}).get("topics") or [ai_data])

    appended = 0
    for i, b in enumerate(batches[:count]):
        if not isinstance(b, dict):
            continue
        cur_id = next_id + appended
        rid = f"#{cur_id}"
        topic = b.get("topic", f"Chủ Đề Pinyin #{cur_id}")
        level = b.get("level", "HSK 2")
        raw_words = b.get("words", [])
        words = []
        for w in raw_words[:5]:
            words.append({"hanzi": w.get("hanzi", "字"), "pinyin": w.get("pinyin", "zì"), "meaning": w.get("meaning", "nghĩa")})
        while len(words) < 5:
            idx = len(words) + 1
            words.append({"hanzi": f"字{idx}", "pinyin": f"zì{idx}", "meaning": f"từ {idx}"})

        w_cols = [f"{w['hanzi']} | {w['pinyin']} | {w['meaning']}" for w in words]
        meta_txt = build_pinyin_metadata(str(cur_id), topic, level, words)
        now_str = get_vietnam_now_str()
        row_data = [rid, topic, level, "Pending"] + w_cols + [meta_txt, "", "", "", "", now_str, f"Tự động sinh bởi {provider} ({now_str} GMT+7)"]
        ws.append_row(row_data)
        appended += 1
        print(f"  ✓ [{provider}] Appended row {rid}: '{topic}' to tab 'pinyin'")


def ideate_vocabcn(ss: gspread.Spreadsheet, count: int, rotator):
    ws = ss.worksheet("vocabCN")
    records = ws.get_all_values()
    next_id = len(records)
    existing_hanzi = extract_existing_hanzi(records)
    print(f"\n▶ [Ideation] Processing Tab 'vocabCN' (Target: {count} batches)...")
    print(f"  Current rows: {len(records)-1}, Unique Hanzi tracked: {len(existing_hanzi)}")

    sys_prompt = (
        "Bạn là biên tập viên tiếng Trung của kênh 'Lê Lê Học Tiếng Trung'. "
        "Nhiệm vụ: Tạo các bộ trắc nghiệm Đoán Nghĩa Tiếng Việt từ chữ Hán (VocabCN Quiz). "
        "Output JSON dạng mảng: [{\"topic\": \"Tên chủ đề tiếng Việt\", \"level\": \"HSK 2\", "
        "\"words\": [{\"hanzi\": \"苹果\", \"pinyin\": \"píngguǒ\", \"meaning\": \"quả táo\"}]}]"
    )
    user_prompt = (
        f"Hãy tạo {count} chủ đề trắc nghiệm Đoán Nghĩa Tiếng Việt, mỗi chủ đề gồm 5 từ vựng HSK 2-3 hay gặp. "
        f"Không trùng lặp các chữ Hán sau: {list(existing_hanzi)[-50:]}."
    )

    ai_data, provider = rotator.generate_quiz_ideas(sys_prompt, user_prompt)
    batches = ai_data if isinstance(ai_data, list) else ((ai_data or {}).get("batches") or (ai_data or {}).get("topics") or [ai_data])

    appended = 0
    for i, b in enumerate(batches[:count]):
        if not isinstance(b, dict):
            continue
        cur_id = next_id + appended
        rid = f"#{cur_id}"
        topic = b.get("topic", f"Đoán Nghĩa Tiếng Việt #{cur_id}")
        level = b.get("level", "HSK 2")
        raw_words = b.get("words", [])
        words = []
        for w in raw_words[:5]:
            words.append({"hanzi": w.get("hanzi", "词"), "pinyin": w.get("pinyin", "cí"), "meaning": w.get("meaning", "nghĩa")})
        while len(words) < 5:
            idx = len(words) + 1
            words.append({"hanzi": f"词{idx}", "pinyin": f"cí{idx}", "meaning": f"nghĩa {idx}"})

        w_cols = [f"{w['hanzi']} | {w['pinyin']} | {w['meaning']}" for w in words]
        meta_txt = build_vocabcn_metadata(str(cur_id), topic, level, words)
        now_str = get_vietnam_now_str()
        row_data = [rid, topic, level, "Pending"] + w_cols + [meta_txt, "", "", "", "", now_str, f"Tự động sinh bởi {provider} ({now_str} GMT+7)"]
        ws.append_row(row_data)
        appended += 1
        print(f"  ✓ [{provider}] Appended row {rid}: '{topic}' to tab 'vocabCN'")


def ideate_vocabvn(ss: gspread.Spreadsheet, count: int, rotator):
    ws = ss.worksheet("vocabVN")
    records = ws.get_all_values()
    next_id = len(records)
    existing_hanzi = extract_existing_hanzi(records)
    print(f"\n▶ [Ideation] Processing Tab 'vocabVN' (Target: {count} batches)...")
    print(f"  Current rows: {len(records)-1}, Unique Hanzi tracked: {len(existing_hanzi)}")

    sys_prompt = (
        "Bạn là biên tập viên tiếng Trung của kênh 'Lê Lê Học Tiếng Trung'. "
        "Nhiệm vụ: Tạo các bộ trắc nghiệm Đoán Chữ Hán từ Nghĩa Tiếng Việt (VocabVN Quiz). "
        "Output JSON dạng mảng: [{\"topic\": \"Tên chủ đề\", \"level\": \"HSK 2\", "
        "\"words\": [{\"hanzi\": \"飞机\", \"pinyin\": \"fēijī\", \"meaning\": \"máy bay\"}]}]"
    )
    user_prompt = (
        f"Hãy tạo {count} chủ đề trắc nghiệm Đoán Chữ Hán, mỗi chủ đề gồm 5 từ vựng HSK 2-3 thông dụng. "
        f"Không trùng lặp các chữ Hán sau: {list(existing_hanzi)[-50:]}."
    )

    ai_data, provider = rotator.generate_quiz_ideas(sys_prompt, user_prompt)
    batches = ai_data if isinstance(ai_data, list) else ((ai_data or {}).get("batches") or (ai_data or {}).get("topics") or [ai_data])

    appended = 0
    for i, b in enumerate(batches[:count]):
        if not isinstance(b, dict):
            continue
        cur_id = next_id + appended
        rid = f"#{cur_id}"
        topic = b.get("topic", f"Đoán Hán Tự #{cur_id}")
        level = b.get("level", "HSK 2")
        raw_words = b.get("words", [])
        words = []
        for w in raw_words[:5]:
            words.append({"hanzi": w.get("hanzi", "汉"), "pinyin": w.get("pinyin", "hàn"), "meaning": w.get("meaning", "nghĩa")})
        while len(words) < 5:
            idx = len(words) + 1
            words.append({"hanzi": f"汉{idx}", "pinyin": f"hàn{idx}", "meaning": f"nghĩa {idx}"})

        # VocabVN format: Nghĩa | Pinyin | Chữ Hán
        w_cols = [f"{w['meaning']} | {w['pinyin']} | {w['hanzi']}" for w in words]
        meta_txt = build_vocabvn_metadata(str(cur_id), topic, level, words)
        now_str = get_vietnam_now_str()
        row_data = [rid, topic, level, "Pending"] + w_cols + [meta_txt, "", "", "", "", now_str, f"Tự động sinh bởi {provider} ({now_str} GMT+7)"]
        ws.append_row(row_data)
        appended += 1
        print(f"  ✓ [{provider}] Appended row {rid}: '{topic}' to tab 'vocabVN'")


def ideate_multilevels(ss: gspread.Spreadsheet, count: int, rotator):
    ws = ss.worksheet("multilevels")
    records = ws.get_all_values()
    next_id = len(records)
    existing_hanzi = extract_existing_hanzi(records)
    print(f"\n▶ [Ideation] Processing Tab 'multilevels' (Target: {count} batches)...")
    print(f"  Current rows: {len(records)-1}, Unique Hanzi tracked: {len(existing_hanzi)}")

    sys_prompt = (
        "Bạn là chuyên gia ngôn ngữ tiếng Trung của kênh 'Lê Lê Học Tiếng Trung'. "
        "Nhiệm vụ: Tạo kịch bản video định dạng '1 Nghĩa 5 Cấp Độ HSK (1 -> 5)'. "
        "Mỗi batch là 1 khái niệm/tính từ/động từ tiếng Việt, biểu đạt qua 5 cấp độ từ vựng HSK tăng dần. "
        "Output JSON dạng mảng: [\n"
        "  {\n"
        "    \"concept\": \"Tên khái niệm (ví dụ: Tự tin / Kiêu hãnh)\",\n"
        "    \"levels\": [\n"
        "      {\"hsk\": \"HSK 1\", \"hanzi\": \"好\", \"pinyin\": \"hǎo\", \"sino_vietnamese\": \"Hảo\", \"meaning\": \"Tốt\", \"nuance\": \"Cơ bản\", \"action\": \"Gật đầu\"},\n"
        "      {\"hsk\": \"HSK 2\", \"hanzi\": \"行\", \"pinyin\": \"xíng\", \"sino_vietnamese\": \"Hành\", \"meaning\": \"Được\", \"nuance\": \"Khá\", \"action\": \"Cười nhẹ\"},\n"
        "      {\"hsk\": \"HSK 3\", \"hanzi\": \"自信\", \"pinyin\": \"zìxìn\", \"sino_vietnamese\": \"Tự tin\", \"meaning\": \"Tự tin\", \"nuance\": \"Rõ ràng\", \"action\": \"Ưỡn ngực\"},\n"
        "      {\"hsk\": \"HSK 4\", \"hanzi\": \"坚信\", \"pinyin\": \"jiānxìn\", \"sino_vietnamese\": \"Kiên tín\", \"meaning\": \"Vững tin\", \"nuance\": \"Mạnh mẽ\", \"action\": \"Nắm tay\"},\n"
        "      {\"hsk\": \"HSK 5\", \"hanzi\": \"昂首阔步\", \"pinyin\": \"ángshǒukuòbù\", \"sino_vietnamese\": \"Ngẩng đầu sải bước\", \"meaning\": \"Hiên ngang\", \"nuance\": \"Tuyệt đối\", \"action\": \"Sải bước\"}\n"
        "    ]\n"
        "  }\n"
        "]"
    )
    user_prompt = (
        f"Hãy tạo {count} chủ đề '1 Nghĩa 5 Cấp Độ HSK' đặc sắc, sâu sắc, biểu đạt sắc thái từ HSK 1 đến HSK 5. "
        f"Không trùng lặp các chữ Hán sau: {list(existing_hanzi)[-60:]}."
    )

    ai_data, provider = rotator.generate_quiz_ideas(sys_prompt, user_prompt)
    batches = ai_data if isinstance(ai_data, list) else ((ai_data or {}).get("batches") or (ai_data or {}).get("concepts") or (ai_data or {}).get("topics") or [ai_data])

    appended = 0
    for i, b in enumerate(batches[:count]):
        if not isinstance(b, dict):
            continue
        cur_id = next_id + appended
        rid = f"#{cur_id}"
        concept = b.get("concept", f"Khái niệm #{cur_id}")
        raw_levels = b.get("levels", [])
        levels = []
        for lvl_idx, l in enumerate(raw_levels[:5]):
            lvl_num = lvl_idx + 1
            levels.append({
                "hsk": l.get("hsk", f"HSK {lvl_num}"),
                "hanzi": l.get("hanzi", f"词{lvl_num}"),
                "pinyin": l.get("pinyin", f"cí{lvl_num}"),
                "sino_vietnamese": l.get("sino_vietnamese", f"Từ {lvl_num}"),
                "meaning": l.get("meaning", f"Nghĩa cấp {lvl_num}"),
                "nuance": l.get("nuance", f"Sắc thái {lvl_num}"),
                "action": l.get("action", f"Hành động {lvl_num}")
            })
        while len(levels) < 5:
            lvl_num = len(levels) + 1
            levels.append({
                "hsk": f"HSK {lvl_num}", "hanzi": f"词{lvl_num}", "pinyin": f"cí{lvl_num}",
                "sino_vietnamese": f"Từ {lvl_num}", "meaning": f"Nghĩa cấp {lvl_num}",
                "nuance": f"Sắc thái {lvl_num}", "action": f"Hành động {lvl_num}"
            })

        w_cols = [f"{lvl['hanzi']} | {lvl['pinyin']} | {lvl['sino_vietnamese']} | {lvl['meaning']} | {lvl['nuance']} | {lvl['action']}" for lvl in levels]
        meta_txt = build_multilevels_metadata(str(cur_id), concept, levels)
        now_str = get_vietnam_now_str()
        row_data = [rid, f"1 Nghĩa 5 Cấp • {concept}", "HSK 1-5", "Pending"] + w_cols + [meta_txt, "", "", "", "", now_str, f"Tự động sinh bởi {provider} ({now_str} GMT+7)"]
        ws.append_row(row_data)
        appended += 1
        print(f"  ✓ [{provider}] Appended row {rid}: '{concept}' to tab 'multilevels'")


def main():
    parser = argparse.ArgumentParser(description="Quiz Ideation Dispatcher with AI Key Rotation")
    parser.add_argument("--tab", "-t", default="all", choices=["all", "pinyin", "vocabCN", "vocabVN", "multilevels"])
    parser.add_argument("--count", "-c", type=int, default=5)
    args = parser.parse_args()

    gc = get_gspread_client()
    ss = gc.open_by_key(SPREADSHEET_ID)
    rotator = get_ai_rotator()

    target_tabs = ["pinyin", "vocabCN", "vocabVN", "multilevels"] if args.tab == "all" else [args.tab]
    print(f"🚀 === Starting Quiz Ideation Dispatcher (Target Tabs: {target_tabs}, Count per tab: {args.count}) ===")

    for t in target_tabs:
        try:
            if t.lower() in ["pinyin", "pinyinquiz"]:
                ideate_pinyin(ss, args.count, rotator)
            elif t.lower() in ["vocabcn", "vocabcnquiz"]:
                ideate_vocabcn(ss, args.count, rotator)
            elif t.lower() in ["vocabvn", "vocabvnquiz"]:
                ideate_vocabvn(ss, args.count, rotator)
            elif t.lower() in ["multilevels", "multilevelsquiz", "ml"]:
                ideate_multilevels(ss, args.count, rotator)
        except Exception as e:
            print(f"❌ Error ideating tab '{t}': {e}")

    print("\n📏 Enforcing strict 21px row height invariant across all tabs...")
    try:
        enforcer = RowHeightEnforcer()
        enforcer.enforce_all()
        print("✓ 21px Row Height Invariant successfully enforced.")
    except Exception as e:
        print(f"⚠ Warning: Could not run row height enforcer: {e}")

    print("\n🎉 Ideation Dispatcher Completed Successfully!")


if __name__ == "__main__":
    main()

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
from scripts.linguistic_qc import (
    GlobalHanziFrequencyMatrix,
    PinyinLinguisticValidator,
    MultilevelsEscalationValidator,
    is_dummy_word,
    normalize_pinyin_spacing,
)

SPREADSHEET_ID = "1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0"
STANDARD_COLUMNS = [
    "#", "Topic", "Level", "Status",
    "Word 1", "Word 2", "Word 3", "Word 4", "Word 5",
    "metadata", "Video", "Youtube", "Tiktok", "Facebook",
    "Created At", "Notes"
]
VALID_TABS = ["pinyin", "vocabCN", "vocabVN", "multilevels"]


def normalize_tab_name(tab_input: str) -> str:
    """Normalizes various CLI/pipeline alias inputs to canonical tab names."""
    cleaned = tab_input.strip().lower()
    mapping = {
        "all": "all",
        "pinyin": "pinyin",
        "pinyinquiz": "pinyin",
        "vocabcn": "vocabCN",
        "vocabcnquiz": "vocabCN",
        "vocabvn": "vocabVN",
        "vocabvnquiz": "vocabVN",
        "multilevels": "multilevels",
        "multilevelsquiz": "multilevels",
        "ml": "multilevels",
    }
    if cleaned in mapping:
        return mapping[cleaned]
    raise ValueError(
        f"Unknown tab/pipeline '{tab_input}'. Must be one of: 'all', 'pinyin', 'vocabCN', 'vocabVN', 'multilevels'"
    )


def validate_and_sanitize_row(row_data: List[Any], expected_row_idx: int) -> List[str]:
    """
    Enforces strict 16 standard columns schema invariants:
    1. Exactly 16 columns (Col A through Col P).
    2. Col A (#): Must strictly equal f"#{expected_row_idx}".
    3. Col D (Status): Must strictly start in 'Pending'.
    4. Col J (metadata): Must contain structured 3-platform text (YouTube Shorts, TikTok, Facebook Reels)
       and must NOT begin with '=' to prevent Google Sheets formula errors.
    5. All other cells sanitized to prevent leading '=' formula injection.
    """
    if len(row_data) != 16:
        raise ValueError(
            f"Schema violation: expected exactly 16 columns (A-P), got {len(row_data)}: {row_data}"
        )

    # 1. Sanitize all columns against leading '=' formula injection
    sanitized = []
    for col in row_data:
        val_str = str(col) if col is not None else ""
        if val_str.startswith("="):
            val_str = val_str.lstrip("=").strip()
        sanitized.append(val_str)

    # 2. Col A: Row ID parity check
    expected_id = f"#{expected_row_idx}"
    if sanitized[0].strip() != expected_id:
        raise ValueError(
            f"Row-ID parity violation: expected '{expected_id}', got '{sanitized[0]}'"
        )

    # 3. Col D: Status must strictly start in Pending
    if sanitized[3].strip() != "Pending":
        raise ValueError(
            f"Status violation: new row must start in 'Pending', got '{sanitized[3]}'"
        )

    # 4. Col J: metadata must contain 3 platforms and never start with '='
    meta_val = sanitized[9].strip()
    meta_upper = meta_val.upper()
    for platform in ["YOUTUBE SHORTS", "TIKTOK", "FACEBOOK REELS"]:
        if platform not in meta_upper:
            raise ValueError(
                f"Metadata violation: missing platform '{platform}' in Column J: {meta_val[:100]}..."
            )

    return sanitized


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
    txt = f"""📝 METADATA CHO VIDEO: {topic} ({level})
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
    return txt.strip().lstrip("=")


def build_vocabcn_metadata(batch_id: str, topic: str, level: str, words: List[Dict[str, str]]) -> str:
    word_lines = "\n".join([f"• {w['hanzi']} ({w['pinyin']}) ➔ {w['meaning']}" for w in words])
    txt = f"""📝 METADATA CHO VIDEO: Đoán Nghĩa Tiếng Việt ({topic})
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
    return txt.strip().lstrip("=")


def build_vocabvn_metadata(batch_id: str, topic: str, level: str, words: List[Dict[str, str]]) -> str:
    word_lines = "\n".join([f"• {w['meaning']} ➔ {w['hanzi']} ({w['pinyin']})" for w in words])
    txt = f"""📝 METADATA CHO VIDEO: Đoán Chữ Hán ({topic})
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
    return txt.strip().lstrip("=")


def build_multilevels_metadata(batch_id: str, concept: str, levels: List[Dict[str, str]]) -> str:
    level_lines = "\n".join([f"• {l.get('hsk', f'HSK {idx+1}')}: {l.get('hanzi', '')} ({l.get('pinyin', '')}) [{l.get('sino_vietnamese', '')}] ➔ {l.get('meaning', '')} ({l.get('nuance', '')})" for idx, l in enumerate(levels)])
    txt = f"""📝 METADATA CHO VIDEO: 1 Nghĩa 5 Cấp Độ ({concept})
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
    return txt.strip().lstrip("=")


# ==============================================================================
# TAB HANDLERS
# ==============================================================================

def ideate_pinyin(
    ss: gspread.Spreadsheet,
    count: int,
    rotator,
    matrix: Optional[GlobalHanziFrequencyMatrix] = None
) -> int:
    ws = ss.worksheet("pinyin")
    records = ws.get_all_values()
    if not records:
        ws.append_row(STANDARD_COLUMNS)
        records = [STANDARD_COLUMNS]
    next_id = len(records) + 1

    if matrix is None:
        matrix = GlobalHanziFrequencyMatrix(ss)
    recent_50 = matrix.get_recent_50_tracked()

    print(f"\n▶ [Ideation] Processing Tab 'pinyin' (Target: {count} batches)...")
    print(f"  Current rows: {len(records)-1}, Recent 50 tracked: {len(recent_50)} chars")

    sys_prompt = (
        "Bạn là chuyên gia ngôn ngữ tiếng Trung của kênh 'Lê Lê Học Tiếng Trung'. "
        "Nhiệm vụ: Tạo các bộ câu hỏi trắc nghiệm phát âm Pinyin (Pinyin Quiz). "
        "Mỗi câu hỏi có 1 chữ Hán, 1 phiên âm Pinyin chuẩn và nghĩa tiếng Việt ngắn gọn. "
        "Quy tắc Pinyin: Bắt buộc có dấu cách giữa các âm tiết tương ứng từng chữ Hán (ví dụ: 'mǐ fàn', 'píng guǒ', 'fēi jī'). "
        "Output JSON dạng mảng: [{\"topic\": \"Tên chủ đề tiếng Việt\", \"level\": \"HSK 2\", "
        "\"words\": [{\"hanzi\": \"苹果\", \"pinyin\": \"píng guǒ\", \"meaning\": \"quả táo\"}]}]"
    )
    user_prompt = (
        f"Hãy tạo {count} chủ đề trắc nghiệm Pinyin, mỗi chủ đề gồm 5 từ vựng HSK 1-3 thông dụng. "
        f"Pinyin phải có dấu cách giữa các âm tiết (ví dụ: 'píng guǒ', 'mǐ fàn'). "
        f"Tuyệt đối KHÔNG trùng lặp các chữ Hán sau: {recent_50}."
    )

    ai_data, provider = rotator.generate_quiz_ideas(sys_prompt, user_prompt)
    batches = ai_data if isinstance(ai_data, list) else ((ai_data or {}).get("batches") or (ai_data or {}).get("topics") or [ai_data])

    appended = 0
    max_retries = 3

    for i, b in enumerate(batches[:count]):
        if not isinstance(b, dict):
            continue

        current_batch = b
        valid_batch = False
        words = []
        topic = ""
        level = ""

        for attempt in range(max_retries):
            topic = current_batch.get("topic", f"Chủ Đề Pinyin #{next_id + appended}")
            level = current_batch.get("level", "HSK 2")
            raw_words = current_batch.get("words", [])

            if len(raw_words) < 5:
                print(f"  ⚠ [Gatekeeper 1 QC] Batch #{i+1} has {len(raw_words)} words (< 5 required). Retrying...")
                retry_data, retry_provider = rotator.generate_quiz_ideas(
                    sys_prompt,
                    f"Tạo 1 chủ đề Pinyin chuẩn xác gồm đúng 5 từ vựng HSK 1-3 (Pinyin có dấu cách như 'mǐ fàn'). Tránh các chữ: {matrix.get_recent_50_tracked()}."
                )
                if retry_data:
                    ret_list = retry_data if isinstance(retry_data, list) else ((retry_data or {}).get("batches") or (retry_data or {}).get("topics") or [retry_data])
                    if ret_list and isinstance(ret_list[0], dict):
                        current_batch = ret_list[0]
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
                print(f"  ⚠ [Gatekeeper 1 QC] Dummy/placeholder words detected in batch #{i+1}. Retrying...")
                retry_data, retry_provider = rotator.generate_quiz_ideas(
                    sys_prompt,
                    f"Tạo 1 chủ đề Pinyin gồm đúng 5 từ vựng HSK 1-3 không dùng từ mẫu hay placeholder. Tránh các chữ: {matrix.get_recent_50_tracked()}."
                )
                if retry_data:
                    ret_list = retry_data if isinstance(retry_data, list) else ((retry_data or {}).get("batches") or (retry_data or {}).get("topics") or [retry_data])
                    if ret_list and isinstance(ret_list[0], dict):
                        current_batch = ret_list[0]
                continue

            is_valid_overlap, ratio, overlap_list, reason = matrix.evaluate_candidate_batch(candidate_words)
            if not is_valid_overlap:
                print(f"  ⚠ [Gatekeeper 1 QC] Overlap check failed: {reason}. Retrying...")
                retry_data, retry_provider = rotator.generate_quiz_ideas(
                    sys_prompt,
                    f"Tạo 1 chủ đề Pinyin gồm 5 từ vựng HSK 1-3 hoàn toàn mới. Tuyệt đối không dùng: {matrix.get_recent_50_tracked()}."
                )
                if retry_data:
                    ret_list = retry_data if isinstance(retry_data, list) else ((retry_data or {}).get("batches") or (retry_data or {}).get("topics") or [retry_data])
                    if ret_list and isinstance(ret_list[0], dict):
                        current_batch = ret_list[0]
                continue

            pinyin_passed = True
            for w in candidate_words:
                p_valid, p_errs = PinyinLinguisticValidator.validate_pinyin(w["hanzi"], w["pinyin"])
                if not p_valid:
                    print(f"  ⚠ [Gatekeeper 1 QC] Pinyin linguistic check failed for '{w['hanzi']}': {p_errs}. Retrying...")
                    pinyin_passed = False
                    break

            if not pinyin_passed:
                retry_data, retry_provider = rotator.generate_quiz_ideas(
                    sys_prompt,
                    f"Tạo 1 chủ đề Pinyin gồm 5 từ vựng chuẩn chỉnh âm điệu. Tránh các chữ: {matrix.get_recent_50_tracked()}."
                )
                if retry_data:
                    ret_list = retry_data if isinstance(retry_data, list) else ((retry_data or {}).get("batches") or (retry_data or {}).get("topics") or [retry_data])
                    if ret_list and isinstance(ret_list[0], dict):
                        current_batch = ret_list[0]
                continue

            words = candidate_words
            valid_batch = True
            break

        if not valid_batch:
            print(f"  ❌ [Gatekeeper 1 QC] Batch #{i+1} rejected after {max_retries} attempts to maintain spreadsheet purity.")
            continue

        cur_id = next_id + appended
        rid = f"#{cur_id}"
        w_cols = [f"{w['hanzi']} | {w['pinyin']} | {w['meaning']}" for w in words]
        meta_txt = build_pinyin_metadata(str(cur_id), topic, level, words)
        now_str = get_vietnam_now_str()
        row_data = [rid, topic, level, "Pending"] + w_cols + [meta_txt, "", "", "", "", now_str, f"Tự động sinh bởi {provider} ({now_str} GMT+7)"]
        sanitized_row = validate_and_sanitize_row(row_data, expected_row_idx=cur_id)
        ws.append_row(sanitized_row)
        matrix.register_ingested_batch("pinyin", words)
        appended += 1
        print(f"  ✓ [{provider}] Passed Gatekeeper 1 QC & Appended row {rid}: '{topic}' to tab 'pinyin'")
    return appended


def ideate_vocabcn(
    ss: gspread.Spreadsheet,
    count: int,
    rotator,
    matrix: Optional[GlobalHanziFrequencyMatrix] = None
) -> int:
    ws = ss.worksheet("vocabCN")
    records = ws.get_all_values()
    if not records:
        ws.append_row(STANDARD_COLUMNS)
        records = [STANDARD_COLUMNS]
    next_id = len(records) + 1

    if matrix is None:
        matrix = GlobalHanziFrequencyMatrix(ss)
    recent_50 = matrix.get_recent_50_tracked()

    print(f"\n▶ [Ideation] Processing Tab 'vocabCN' (Target: {count} batches)...")
    print(f"  Current rows: {len(records)-1}, Recent 50 tracked: {len(recent_50)} chars")

    sys_prompt = (
        "Bạn là biên tập viên tiếng Trung của kênh 'Lê Lê Học Tiếng Trung'. "
        "Nhiệm vụ: Tạo các bộ trắc nghiệm Đoán Nghĩa Tiếng Việt từ chữ Hán (VocabCN Quiz). "
        "Quy tắc Pinyin: Bắt buộc có dấu cách giữa các âm tiết tương ứng từng chữ Hán (ví dụ: 'píng guǒ', 'fēi jī'). "
        "Output JSON dạng mảng: [{\"topic\": \"Tên chủ đề tiếng Việt\", \"level\": \"HSK 2\", "
        "\"words\": [{\"hanzi\": \"苹果\", \"pinyin\": \"píng guǒ\", \"meaning\": \"quả táo\"}]}]"
    )
    user_prompt = (
        f"Hãy tạo {count} chủ đề trắc nghiệm Đoán Nghĩa Tiếng Việt, mỗi chủ đề gồm 5 từ vựng HSK 2-3 hay gặp. "
        f"Pinyin phải có dấu cách giữa các âm tiết (ví dụ: 'píng guǒ', 'mǐ fàn'). "
        f"Tuyệt đối KHÔNG trùng lặp các chữ Hán sau: {recent_50}."
    )

    ai_data, provider = rotator.generate_quiz_ideas(sys_prompt, user_prompt)
    batches = ai_data if isinstance(ai_data, list) else ((ai_data or {}).get("batches") or (ai_data or {}).get("topics") or [ai_data])

    appended = 0
    max_retries = 3

    for i, b in enumerate(batches[:count]):
        if not isinstance(b, dict):
            continue

        current_batch = b
        valid_batch = False
        words = []
        topic = ""
        level = ""

        for attempt in range(max_retries):
            topic = current_batch.get("topic", f"Đoán Nghĩa Tiếng Việt #{next_id + appended}")
            level = current_batch.get("level", "HSK 2")
            raw_words = current_batch.get("words", [])

            if len(raw_words) < 5:
                print(f"  ⚠ [Gatekeeper 1 QC] Batch #{i+1} has {len(raw_words)} words (< 5 required). Retrying...")
                retry_data, retry_provider = rotator.generate_quiz_ideas(
                    sys_prompt,
                    f"Tạo 1 chủ đề VocabCN gồm đúng 5 từ vựng HSK 2-3 (Pinyin có dấu cách như 'píng guǒ'). Tránh các chữ: {matrix.get_recent_50_tracked()}."
                )
                if retry_data:
                    ret_list = retry_data if isinstance(retry_data, list) else ((retry_data or {}).get("batches") or (retry_data or {}).get("topics") or [retry_data])
                    if ret_list and isinstance(ret_list[0], dict):
                        current_batch = ret_list[0]
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
                print(f"  ⚠ [Gatekeeper 1 QC] Dummy/placeholder words detected in batch #{i+1}. Retrying...")
                retry_data, retry_provider = rotator.generate_quiz_ideas(
                    sys_prompt,
                    f"Tạo 1 chủ đề VocabCN gồm 5 từ vựng HSK 2-3 không dùng từ mẫu. Tránh các chữ: {matrix.get_recent_50_tracked()}."
                )
                if retry_data:
                    ret_list = retry_data if isinstance(retry_data, list) else ((retry_data or {}).get("batches") or (retry_data or {}).get("topics") or [retry_data])
                    if ret_list and isinstance(ret_list[0], dict):
                        current_batch = ret_list[0]
                continue

            is_valid_overlap, ratio, overlap_list, reason = matrix.evaluate_candidate_batch(candidate_words)
            if not is_valid_overlap:
                print(f"  ⚠ [Gatekeeper 1 QC] Overlap check failed: {reason}. Retrying...")
                retry_data, retry_provider = rotator.generate_quiz_ideas(
                    sys_prompt,
                    f"Tạo 1 chủ đề VocabCN gồm 5 từ vựng mới hoàn toàn. Tránh: {matrix.get_recent_50_tracked()}."
                )
                if retry_data:
                    ret_list = retry_data if isinstance(retry_data, list) else ((retry_data or {}).get("batches") or (retry_data or {}).get("topics") or [retry_data])
                    if ret_list and isinstance(ret_list[0], dict):
                        current_batch = ret_list[0]
                continue

            pinyin_passed = True
            for w in candidate_words:
                p_valid, p_errs = PinyinLinguisticValidator.validate_pinyin(w["hanzi"], w["pinyin"])
                if not p_valid:
                    print(f"  ⚠ [Gatekeeper 1 QC] Pinyin linguistic check failed for '{w['hanzi']}': {p_errs}. Retrying...")
                    pinyin_passed = False
                    break

            if not pinyin_passed:
                retry_data, retry_provider = rotator.generate_quiz_ideas(
                    sys_prompt,
                    f"Tạo 1 chủ đề VocabCN gồm 5 từ vựng chuẩn chỉnh âm điệu. Tránh: {matrix.get_recent_50_tracked()}."
                )
                if retry_data:
                    ret_list = retry_data if isinstance(retry_data, list) else ((retry_data or {}).get("batches") or (retry_data or {}).get("topics") or [retry_data])
                    if ret_list and isinstance(ret_list[0], dict):
                        current_batch = ret_list[0]
                continue

            words = candidate_words
            valid_batch = True
            break

        if not valid_batch:
            print(f"  ❌ [Gatekeeper 1 QC] Batch #{i+1} rejected after {max_retries} attempts to maintain spreadsheet purity.")
            continue

        cur_id = next_id + appended
        rid = f"#{cur_id}"
        w_cols = [f"{w['hanzi']} | {w['pinyin']} | {w['meaning']}" for w in words]
        meta_txt = build_vocabcn_metadata(str(cur_id), topic, level, words)
        now_str = get_vietnam_now_str()
        row_data = [rid, topic, level, "Pending"] + w_cols + [meta_txt, "", "", "", "", now_str, f"Tự động sinh bởi {provider} ({now_str} GMT+7)"]
        sanitized_row = validate_and_sanitize_row(row_data, expected_row_idx=cur_id)
        ws.append_row(sanitized_row)
        matrix.register_ingested_batch("vocabCN", words)
        appended += 1
        print(f"  ✓ [{provider}] Passed Gatekeeper 1 QC & Appended row {rid}: '{topic}' to tab 'vocabCN'")
    return appended


def ideate_vocabvn(
    ss: gspread.Spreadsheet,
    count: int,
    rotator,
    matrix: Optional[GlobalHanziFrequencyMatrix] = None
) -> int:
    ws = ss.worksheet("vocabVN")
    records = ws.get_all_values()
    if not records:
        ws.append_row(STANDARD_COLUMNS)
        records = [STANDARD_COLUMNS]
    next_id = len(records) + 1

    if matrix is None:
        matrix = GlobalHanziFrequencyMatrix(ss)
    recent_50 = matrix.get_recent_50_tracked()

    print(f"\n▶ [Ideation] Processing Tab 'vocabVN' (Target: {count} batches)...")
    print(f"  Current rows: {len(records)-1}, Recent 50 tracked: {len(recent_50)} chars")

    sys_prompt = (
        "Bạn là biên tập viên tiếng Trung của kênh 'Lê Lê Học Tiếng Trung'. "
        "Nhiệm vụ: Tạo các bộ trắc nghiệm Đoán Chữ Hán từ Nghĩa Tiếng Việt (VocabVN Quiz). "
        "Quy tắc Pinyin: Bắt buộc có dấu cách giữa các âm tiết tương ứng từng chữ Hán (ví dụ: 'fēi jī', 'píng guǒ'). "
        "Output JSON dạng mảng: [{\"topic\": \"Tên chủ đề\", \"level\": \"HSK 2\", "
        "\"words\": [{\"hanzi\": \"飞机\", \"pinyin\": \"fēi jī\", \"meaning\": \"máy bay\"}]}]"
    )
    user_prompt = (
        f"Hãy tạo {count} chủ đề trắc nghiệm Đoán Chữ Hán, mỗi chủ đề gồm 5 từ vựng HSK 2-3 thông dụng. "
        f"Pinyin phải có dấu cách giữa các âm tiết (ví dụ: 'fēi jī', 'mǐ fàn'). "
        f"Tuyệt đối KHÔNG trùng lặp các chữ Hán sau: {recent_50}."
    )

    ai_data, provider = rotator.generate_quiz_ideas(sys_prompt, user_prompt)
    batches = ai_data if isinstance(ai_data, list) else ((ai_data or {}).get("batches") or (ai_data or {}).get("topics") or [ai_data])

    appended = 0
    max_retries = 3

    for i, b in enumerate(batches[:count]):
        if not isinstance(b, dict):
            continue

        current_batch = b
        valid_batch = False
        words = []
        topic = ""
        level = ""

        for attempt in range(max_retries):
            topic = current_batch.get("topic", f"Đoán Hán Tự #{next_id + appended}")
            level = current_batch.get("level", "HSK 2")
            raw_words = current_batch.get("words", [])

            if len(raw_words) < 5:
                print(f"  ⚠ [Gatekeeper 1 QC] Batch #{i+1} has {len(raw_words)} words (< 5 required). Retrying...")
                retry_data, retry_provider = rotator.generate_quiz_ideas(
                    sys_prompt,
                    f"Tạo 1 chủ đề VocabVN gồm đúng 5 từ vựng HSK 2-3 (Pinyin có dấu cách như 'fēi jī'). Tránh các chữ: {matrix.get_recent_50_tracked()}."
                )
                if retry_data:
                    ret_list = retry_data if isinstance(retry_data, list) else ((retry_data or {}).get("batches") or (retry_data or {}).get("topics") or [retry_data])
                    if ret_list and isinstance(ret_list[0], dict):
                        current_batch = ret_list[0]
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
                print(f"  ⚠ [Gatekeeper 1 QC] Dummy/placeholder words detected in batch #{i+1}. Retrying...")
                retry_data, retry_provider = rotator.generate_quiz_ideas(
                    sys_prompt,
                    f"Tạo 1 chủ đề VocabVN gồm 5 từ vựng HSK 2-3 không dùng từ mẫu. Tránh các chữ: {matrix.get_recent_50_tracked()}."
                )
                if retry_data:
                    ret_list = retry_data if isinstance(retry_data, list) else ((retry_data or {}).get("batches") or (retry_data or {}).get("topics") or [retry_data])
                    if ret_list and isinstance(ret_list[0], dict):
                        current_batch = ret_list[0]
                continue

            is_valid_overlap, ratio, overlap_list, reason = matrix.evaluate_candidate_batch(candidate_words)
            if not is_valid_overlap:
                print(f"  ⚠ [Gatekeeper 1 QC] Overlap check failed: {reason}. Retrying...")
                retry_data, retry_provider = rotator.generate_quiz_ideas(
                    sys_prompt,
                    f"Tạo 1 chủ đề VocabVN gồm 5 từ vựng mới hoàn toàn. Tránh: {matrix.get_recent_50_tracked()}."
                )
                if retry_data:
                    ret_list = retry_data if isinstance(retry_data, list) else ((retry_data or {}).get("batches") or (retry_data or {}).get("topics") or [retry_data])
                    if ret_list and isinstance(ret_list[0], dict):
                        current_batch = ret_list[0]
                continue

            pinyin_passed = True
            for w in candidate_words:
                p_valid, p_errs = PinyinLinguisticValidator.validate_pinyin(w["hanzi"], w["pinyin"])
                if not p_valid:
                    print(f"  ⚠ [Gatekeeper 1 QC] Pinyin linguistic check failed for '{w['hanzi']}': {p_errs}. Retrying...")
                    pinyin_passed = False
                    break

            if not pinyin_passed:
                retry_data, retry_provider = rotator.generate_quiz_ideas(
                    sys_prompt,
                    f"Tạo 1 chủ đề VocabVN gồm 5 từ vựng chuẩn chỉnh âm điệu. Tránh: {matrix.get_recent_50_tracked()}."
                )
                if retry_data:
                    ret_list = retry_data if isinstance(retry_data, list) else ((retry_data or {}).get("batches") or (retry_data or {}).get("topics") or [retry_data])
                    if ret_list and isinstance(ret_list[0], dict):
                        current_batch = ret_list[0]
                continue

            words = candidate_words
            valid_batch = True
            break

        if not valid_batch:
            print(f"  ❌ [Gatekeeper 1 QC] Batch #{i+1} rejected after {max_retries} attempts to maintain spreadsheet purity.")
            continue

        cur_id = next_id + appended
        rid = f"#{cur_id}"
        # VocabVN format: Nghĩa | Pinyin | Chữ Hán
        w_cols = [f"{w['meaning']} | {w['pinyin']} | {w['hanzi']}" for w in words]
        meta_txt = build_vocabvn_metadata(str(cur_id), topic, level, words)
        now_str = get_vietnam_now_str()
        row_data = [rid, topic, level, "Pending"] + w_cols + [meta_txt, "", "", "", "", now_str, f"Tự động sinh bởi {provider} ({now_str} GMT+7)"]
        sanitized_row = validate_and_sanitize_row(row_data, expected_row_idx=cur_id)
        ws.append_row(sanitized_row)
        matrix.register_ingested_batch("vocabVN", words)
        appended += 1
        print(f"  ✓ [{provider}] Appended row {rid}: '{topic}' to tab 'vocabVN'")
    return appended


def ideate_multilevels(
    ss: gspread.Spreadsheet,
    count: int,
    rotator,
    matrix: Optional[GlobalHanziFrequencyMatrix] = None
) -> int:
    ws = ss.worksheet("multilevels")
    records = ws.get_all_values()
    if not records:
        ws.append_row(STANDARD_COLUMNS)
        records = [STANDARD_COLUMNS]
    next_id = len(records) + 1

    if matrix is None:
        matrix = GlobalHanziFrequencyMatrix(ss)
    recent_50 = matrix.get_recent_50_tracked()

    print(f"\n▶ [Ideation] Processing Tab 'multilevels' (Target: {count} batches)...")
    print(f"  Current rows: {len(records)-1}, Recent 50 tracked: {len(recent_50)} chars")

    sys_prompt = (
        "Bạn là chuyên gia ngôn ngữ tiếng Trung của kênh 'Lê Lê Học Tiếng Trung'. "
        "Nhiệm vụ: Tạo kịch bản video định dạng '1 Nghĩa 5 Cấp Độ HSK (1 -> 5)'. "
        "Mỗi batch là 1 khái niệm/tính từ/động từ tiếng Việt, biểu đạt qua 5 cấp độ từ vựng HSK tăng dần. "
        "Output JSON dạng mảng: [\n"
        "  {\n"
        "    \"concept_name_vi\": \"Tự tin / Kiêu hãnh\",\n"
        "    \"levels\": [\n"
        "      {\"level\": 1, \"hsk\": \"HSK 1\", \"hanzi\": \"好\", \"pinyin\": \"hǎo\", \"han_viet\": \"Hảo\", \"meaning_vi\": \"Tốt\", \"nuance_note\": \"Cơ bản\", \"visual_action\": \"Gật đầu\"},\n"
        "      {\"level\": 2, \"hsk\": \"HSK 2\", \"hanzi\": \"行\", \"pinyin\": \"xíng\", \"han_viet\": \"Hành\", \"meaning_vi\": \"Được\", \"nuance_note\": \"Khá\", \"visual_action\": \"Cười nhẹ\"},\n"
        "      {\"level\": 3, \"hsk\": \"HSK 3\", \"hanzi\": \"自信\", \"pinyin\": \"zìxìn\", \"han_viet\": \"Tự tin\", \"meaning_vi\": \"Tự tin\", \"nuance_note\": \"Rõ ràng\", \"visual_action\": \"Ưỡn ngực\"},\n"
        "      {\"level\": 4, \"hsk\": \"HSK 4\", \"hanzi\": \"坚信\", \"pinyin\": \"jiānxìn\", \"han_viet\": \"Kiên tín\", \"meaning_vi\": \"Vững tin\", \"nuance_note\": \"Mạnh mẽ\", \"visual_action\": \"Nắm tay\"},\n"
        "      {\"level\": 5, \"hsk\": \"HSK 5\", \"hanzi\": \"昂首阔步\", \"pinyin\": \"ángshǒukuòbù\", \"han_viet\": \"Ngẩng đầu\", \"meaning_vi\": \"Hiên ngang\", \"nuance_note\": \"Tuyệt đối\", \"visual_action\": \"Sải bước\"}\n"
        "    ]\n"
        "  }\n"
        "]"
    )
    user_prompt = (
        f"Hãy tạo {count} chủ đề '1 Nghĩa 5 Cấp Độ HSK' đặc sắc, sâu sắc, biểu đạt sắc thái từ HSK 1 đến HSK 5. "
        f"Tuyệt đối KHÔNG trùng lặp các chữ Hán sau: {recent_50}."
    )

    ai_data, provider = rotator.generate_quiz_ideas(sys_prompt, user_prompt)
    batches = ai_data if isinstance(ai_data, list) else ((ai_data or {}).get("batches") or (ai_data or {}).get("concepts") or (ai_data or {}).get("topics") or [ai_data])

    appended = 0
    max_retries = 3

    for i, b in enumerate(batches[:count]):
        if not isinstance(b, dict):
            continue

        current_batch = b
        valid_batch = False
        levels = []
        clean_concept = ""
        topic_title = ""

        for attempt in range(max_retries):
            raw_concept = current_batch.get("concept_name_vi", "") or current_batch.get("concept", f"Khái niệm #{next_id + appended}")
            clean_concept = raw_concept.replace("1 Nghĩa 5 Cấp •", "").replace("1 Nghĩa 5 Cấp", "").strip()
            topic_title = f"1 Nghĩa 5 Cấp • {clean_concept}" if clean_concept else raw_concept
            raw_levels = current_batch.get("levels", [])

            if len(raw_levels) < 5:
                print(f"  ⚠ [Gatekeeper 1 QC] Multilevels batch #{i+1} has {len(raw_levels)} levels (< 5 required). Retrying...")
                retry_data, retry_provider = rotator.generate_quiz_ideas(
                    sys_prompt, f"Tạo 1 bộ '1 Nghĩa 5 Cấp Độ HSK' gồm 5 cấp độ HSK 1-5. Tránh: {matrix.get_recent_50_tracked()}."
                )
                if retry_data:
                    ret_list = retry_data if isinstance(retry_data, list) else ((retry_data or {}).get("batches") or (retry_data or {}).get("concepts") or [retry_data])
                    if ret_list and isinstance(ret_list[0], dict):
                        current_batch = ret_list[0]
                continue

            batch_to_validate = {
                "concept_name_vi": clean_concept or raw_concept,
                "levels": raw_levels
            }
            is_valid_ml, ml_errors = MultilevelsEscalationValidator.validate_multilevels_batch(batch_to_validate)
            if not is_valid_ml:
                print(f"  ⚠ [Gatekeeper 1 QC] Multilevels validation failed for batch #{i+1}: {ml_errors}. Retrying...")
                retry_data, retry_provider = rotator.generate_quiz_ideas(
                    sys_prompt, f"Tạo 1 bộ '1 Nghĩa 5 Cấp Độ HSK' chuẩn xác 5 cấp độ HSK 1-5. Tránh: {matrix.get_recent_50_tracked()}."
                )
                if retry_data:
                    ret_list = retry_data if isinstance(retry_data, list) else ((retry_data or {}).get("batches") or (retry_data or {}).get("concepts") or [retry_data])
                    if ret_list and isinstance(ret_list[0], dict):
                        current_batch = ret_list[0]
                continue

            candidate_words = [{"hanzi": l.get("hanzi", "")} for l in raw_levels]
            is_valid_overlap, ratio, overlap_list, reason = matrix.evaluate_candidate_batch(candidate_words)
            if not is_valid_overlap:
                print(f"  ⚠ [Gatekeeper 1 QC] Multilevels overlap check failed: {reason}. Retrying...")
                retry_data, retry_provider = rotator.generate_quiz_ideas(
                    sys_prompt, f"Tạo 1 bộ '1 Nghĩa 5 Cấp Độ HSK' hoàn toàn mới. Tránh: {matrix.get_recent_50_tracked()}."
                )
                if retry_data:
                    ret_list = retry_data if isinstance(retry_data, list) else ((retry_data or {}).get("batches") or (retry_data or {}).get("concepts") or [retry_data])
                    if ret_list and isinstance(ret_list[0], dict):
                        current_batch = ret_list[0]
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

            levels = norm_levels
            valid_batch = True
            break

        if not valid_batch:
            print(f"  ❌ [Gatekeeper 1 QC] Batch #{i+1} rejected after {max_retries} attempts to maintain spreadsheet purity.")
            continue

        cur_id = next_id + appended
        rid = f"#{cur_id}"
        w_cols = [f"{lvl['hanzi']} | {lvl['pinyin']} | {lvl['sino_vietnamese']} | {lvl['meaning']} | {lvl['nuance']} | {lvl['action']}" for lvl in levels]
        meta_txt = build_multilevels_metadata(str(cur_id), clean_concept or "Khái niệm", levels)
        now_str = get_vietnam_now_str()
        row_data = [rid, topic_title, "HSK 1-5", "Pending"] + w_cols + [meta_txt, "", "", "", "", now_str, f"Tự động sinh bởi {provider} ({now_str} GMT+7)"]
        sanitized_row = validate_and_sanitize_row(row_data, expected_row_idx=cur_id)
        ws.append_row(sanitized_row)
        matrix.register_ingested_batch("multilevels", [{"hanzi": l["hanzi"]} for l in levels])
        appended += 1
        print(f"  ✓ [{provider}] Passed Gatekeeper 1 QC & Appended row {rid}: '{topic_title}' to tab 'multilevels'")
    return appended


def dispatch_single_tab(
    tab_name: str,
    count: int,
    rotator,
    ss: Optional[gspread.Spreadsheet] = None,
    client: Optional[gspread.Client] = None,
    matrix: Optional[GlobalHanziFrequencyMatrix] = None,
) -> int:
    """
    Dispatches ideation strictly isolated to a single tab with Gatekeeper 1 QC.
    Binds directly to dedicated Worksheet instance without cross-tab contamination.
    """
    canonical_tab = normalize_tab_name(tab_name)
    if canonical_tab == "all":
        raise ValueError("dispatch_single_tab requires a specific tab name, not 'all'")

    if ss is None:
        gc = client or get_gspread_client()
        ss = gc.open_by_key(SPREADSHEET_ID)

    if matrix is None:
        matrix = GlobalHanziFrequencyMatrix(spreadsheet_client=client if client is not None else ss, spreadsheet_id=SPREADSHEET_ID)

    if canonical_tab == "pinyin":
        return ideate_pinyin(ss, count, rotator, matrix=matrix)
    elif canonical_tab == "vocabCN":
        return ideate_vocabcn(ss, count, rotator, matrix=matrix)
    elif canonical_tab == "vocabVN":
        return ideate_vocabvn(ss, count, rotator, matrix=matrix)
    elif canonical_tab == "multilevels":
        return ideate_multilevels(ss, count, rotator, matrix=matrix)
    else:
        raise ValueError(f"Unsupported tab: {canonical_tab}")


def main():
    parser = argparse.ArgumentParser(description="Quiz Ideation Dispatcher with AI Key Rotation")
    parser.add_argument(
        "--tab", "-t", "--pipeline", "-p",
        dest="tab",
        default="all",
        help="Target tab or pipeline (all, pinyin, vocabCN, vocabVN, multilevels)"
    )
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=5,
        help="Number of batches to generate per tab (default: 5)"
    )
    args = parser.parse_args()

    normalized = normalize_tab_name(args.tab)
    target_tabs = ["pinyin", "vocabCN", "vocabVN", "multilevels"] if normalized == "all" else [normalized]
    print(f"🚀 === Starting Quiz Ideation Dispatcher (Target Tabs: {target_tabs}, Count per tab: {args.count}) ===")

    gc = get_gspread_client()
    ss = gc.open_by_key(SPREADSHEET_ID)
    rotator = get_ai_rotator()
    matrix = GlobalHanziFrequencyMatrix(spreadsheet_client=gc, spreadsheet_id=SPREADSHEET_ID)

    for t in target_tabs:
        try:
            dispatch_single_tab(t, args.count, rotator, ss=ss, matrix=matrix)
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


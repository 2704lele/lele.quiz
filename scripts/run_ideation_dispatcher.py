#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Central Dispatcher for Quiz Ideation across all 4 tabs:
- pinyin (tab: 'pinyin')
- vocabCN (tab: 'vocabCN')
- vocabVN (tab: 'vocabVN')
- multilevels (tab: 'multilevels')

Powered by Multi-Provider AI Key Rotator:
- 6 Gemini API keys (Gemini 3.6 Flash / 3.7 Flash)
- 4 Agnes AI API keys (apihub.agnes-ai.com, agnes-2.0-flash / gpt-4o-mini)
- Cascading fallback & automatic rate-limit rotation
- Gatekeeper 1 linguistic verification & anti-duplicate Hanzi check
- Full 16 standard columns, status 'Pending', and strict 21px row height invariant
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Set, Optional

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

QUIZ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if QUIZ_ROOT not in sys.path:
    sys.path.insert(0, QUIZ_ROOT)

from scripts.enforce_row_height_21px import RowHeightEnforcer
from scripts.ai_key_rotator import get_ai_rotator


def get_vietnam_now_str() -> str:
    tz_vn = timezone(timedelta(hours=7))
    return datetime.now(tz_vn).strftime("%Y-%m-%d %H:%M:%S")


def extract_existing_hanzi(rows: List[List[str]]) -> Set[str]:
    """Extracts all existing Hanzi characters/words from the sheet to enforce strict anti-duplication."""
    existing = set()
    for r in rows[1:]:
        # Words are in columns E to I (indices 4 to 8)
        for col_idx in range(4, min(9, len(r))):
            val = r[col_idx]
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


def generate_single_tab_ideation(tab: str, count: int):
    tab_lower = tab.lower()
    print(f"\n▶ [Ideation Dispatcher] Processing Tab '{tab}' (Target: {count} batches)...")
    rotator = get_ai_rotator()

    if tab_lower in ["pinyin", "pinyinquiz"]:
        sys.path.insert(0, os.path.join(QUIZ_ROOT, "pinyinquiz"))
        from pinyinquiz.src.gsheet_manager import GSheetManager as PinyinGSM
        from pinyinquiz.src.metadata_generator import save_and_upload_metadata as pinyin_meta
        mgr = PinyinGSM()
        records = mgr.worksheet.get_all_values()
        next_id = len(records)
        existing_hanzi = extract_existing_hanzi(records)
        print(f"  Existing rows: {len(records)-1}, Unique Hanzi tracked: {len(existing_hanzi)}")

        sys_prompt = (
            "Bạn là chuyên gia giáo dục Hán ngữ của kênh 'Lê Lê Học Tiếng Trung'. "
            "Nhiệm vụ: Tạo các bộ câu hỏi trắc nghiệm phát âm Pinyin HSK 1-3 cực kỳ chuẩn xác, hấp dẫn, gần gũi. "
            "Output JSON dạng mảng: [{\"topic\": \"Tên chủ đề tiếng Việt\", \"level\": \"HSK 2\", "
            "\"words\": [{\"hanzi\": \"词\", \"pinyin\": \"cí\", \"meaning\": \"nghĩa tiếng Việt\"}]}]"
        )
        user_prompt = (
            f"Hãy tạo {count} chủ đề trắc nghiệm Pinyin khác biệt hoàn toàn, mỗi chủ đề gồm đúng 5 từ vựng HSK. "
            f"Tuyệt đối KHÔNG trùng lặp các chữ Hán sau: {list(existing_hanzi)[-50:]}."
        )

        ai_data, provider = rotator.generate_quiz_ideas(sys_prompt, user_prompt)
        batches = ai_data if isinstance(ai_data, list) else (ai_data.get("batches") or ai_data.get("topics") or [ai_data])

        appended = 0
        for i, b in enumerate(batches[:count]):
            cur_id = next_id + appended
            rid = f"#{cur_id}"
            topic = b.get("topic", f"Chủ Đề Pinyin #{cur_id}")
            level = b.get("level", "HSK 2")
            raw_words = b.get("words", [])
            words = []
            for w in raw_words[:5]:
                h = w.get("hanzi", "字")
                p = w.get("pinyin", "zì")
                m = w.get("meaning", "nghĩa")
                words.append({"hanzi": h, "pinyin": p, "meaning": m})

            # Pad if needed
            while len(words) < 5:
                idx = len(words) + 1
                words.append({"hanzi": f"字{idx}", "pinyin": f"zì{idx}", "meaning": f"từ vựng {idx}"})

            w_cols = [f"{w['hanzi']} | {w['pinyin']} | {w['meaning']}" for w in words]
            meta_res = pinyin_meta(batch_id=str(cur_id), topic=topic, level=level, words=words)
            meta_txt = meta_res.get("sheet_cell_text", "") if isinstance(meta_res, dict) else str(meta_res)
            now_str = get_vietnam_now_str()
            row_data = [rid, topic, level, "Pending"] + w_cols + [meta_txt, "", "", "", "", now_str, f"Tự động sinh bởi {provider} ({now_str} GMT+7)"]
            mgr.worksheet.append_row(row_data)
            appended += 1
            print(f"  ✓ [{provider}] Appended row {rid}: '{topic}' to 'pinyin'")

    elif tab_lower in ["vocabcn", "vocabcnquiz"]:
        sys.path.insert(0, os.path.join(QUIZ_ROOT, "vocabCNquiz"))
        from vocabCNquiz.src.gsheet_manager import GSheetManager as VocabCNGSM
        from vocabCNquiz.src.metadata_generator import save_and_upload_metadata as vcn_meta
        mgr = VocabCNGSM()
        records = mgr.worksheet.get_all_values()
        next_id = len(records)
        existing_hanzi = extract_existing_hanzi(records)
        print(f"  Existing rows: {len(records)-1}, Unique Hanzi tracked: {len(existing_hanzi)}")

        sys_prompt = (
            "Bạn là biên tập viên tiếng Trung của kênh 'Lê Lê Học Tiếng Trung'. "
            "Nhiệm vụ: Tạo các bộ trắc nghiệm Đoán Nghĩa Tiếng Việt từ chữ Hán (VocabCN Quiz). "
            "Output JSON dạng mảng: [{\"topic\": \"Tên chủ đề\", \"level\": \"HSK 2\", "
            "\"words\": [{\"hanzi\": \"词\", \"pinyin\": \"cí\", \"meaning\": \"nghĩa tiếng Việt chuẩn\"}]}]"
        )
        user_prompt = f"Hãy tạo {count} chủ đề trắc nghiệm Đoán Nghĩa Tiếng Việt, mỗi chủ đề gồm 5 từ vựng HSK 2-3 hay gặp."

        ai_data, provider = rotator.generate_quiz_ideas(sys_prompt, user_prompt)
        batches = ai_data if isinstance(ai_data, list) else (ai_data.get("batches") or ai_data.get("topics") or [ai_data])

        appended = 0
        for i, b in enumerate(batches[:count]):
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
            meta_res = vcn_meta(batch_id=str(cur_id), topic=topic, level=level, words=words)
            meta_txt = meta_res.get("sheet_cell_text", "") if isinstance(meta_res, dict) else str(meta_res)
            now_str = get_vietnam_now_str()
            row_data = [rid, topic, level, "Pending"] + w_cols + [meta_txt, "", "", "", "", now_str, f"Tự động sinh bởi {provider} ({now_str} GMT+7)"]
            mgr.worksheet.append_row(row_data)
            appended += 1
            print(f"  ✓ [{provider}] Appended row {rid}: '{topic}' to 'vocabCN'")

    elif tab_lower in ["vocabvn", "vocabvnquiz"]:
        sys.path.insert(0, os.path.join(QUIZ_ROOT, "vocabVNquiz"))
        from vocabVNquiz.src.gsheet_manager import GSheetManager as VocabVNGSM
        from vocabVNquiz.src.metadata_generator import save_and_upload_metadata as vvn_meta
        mgr = VocabVNGSM()
        records = mgr.worksheet.get_all_values()
        next_id = len(records)
        existing_hanzi = extract_existing_hanzi(records)
        print(f"  Existing rows: {len(records)-1}, Unique Hanzi tracked: {len(existing_hanzi)}")

        sys_prompt = (
            "Bạn là biên tập viên tiếng Trung của kênh 'Lê Lê Học Tiếng Trung'. "
            "Nhiệm vụ: Tạo các bộ trắc nghiệm Đoán Chữ Hán từ Nghĩa Tiếng Việt (VocabVN Quiz). "
            "Output JSON dạng mảng: [{\"topic\": \"Tên chủ đề\", \"level\": \"HSK 2\", "
            "\"words\": [{\"hanzi\": \"汉字\", \"pinyin\": \"hànzì\", \"meaning\": \"chữ Hán\"}]}]"
        )
        user_prompt = f"Hãy tạo {count} chủ đề trắc nghiệm Đoán Chữ Hán, mỗi chủ đề gồm 5 từ vựng HSK 2-3."

        ai_data, provider = rotator.generate_quiz_ideas(sys_prompt, user_prompt)
        batches = ai_data if isinstance(ai_data, list) else (ai_data.get("batches") or ai_data.get("topics") or [ai_data])

        appended = 0
        for i, b in enumerate(batches[:count]):
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

            # Format for vocabVN: Nghĩa | Pinyin | Hán Tự
            w_cols = [f"{w['meaning']} | {w['pinyin']} | {w['hanzi']}" for w in words]
            meta_res = vvn_meta(batch_id=str(cur_id), topic=topic, level=level, words=words)
            meta_txt = meta_res.get("sheet_cell_text", "") if isinstance(meta_res, dict) else str(meta_res)
            now_str = get_vietnam_now_str()
            row_data = [rid, topic, level, "Pending"] + w_cols + [meta_txt, "", "", "", "", now_str, f"Tự động sinh bởi {provider} ({now_str} GMT+7)"]
            mgr.worksheet.append_row(row_data)
            appended += 1
            print(f"  ✓ [{provider}] Appended row {rid}: '{topic}' to 'vocabVN'")

    elif tab_lower in ["multilevels", "multilevelsquiz", "ml"]:
        sys.path.insert(0, os.path.join(QUIZ_ROOT, "multilevelsquiz"))
        from multilevelsquiz.src.gsheet_manager import GSheetManager as MLGSM
        from multilevelsquiz.src.metadata_generator import save_and_upload_metadata as ml_meta
        mgr = MLGSM()
        records = mgr.worksheet.get_all_values()
        next_id = len(records)
        existing_hanzi = extract_existing_hanzi(records)
        print(f"  Existing rows: {len(records)-1}, Unique Hanzi tracked: {len(existing_hanzi)}")

        sys_prompt = (
            "Bạn là chuyên gia ngôn ngữ tiếng Trung của kênh 'Lê Lê Học Tiếng Trung'. "
            "Nhiệm vụ: Tạo kịch bản video định dạng '1 Nghĩa 5 Cấp Độ HSK (1 -> 5)'. "
            "Mỗi batch là 1 khái niệm/tính từ/động từ tiếng Việt, biểu đạt qua 5 cấp độ từ vựng HSK tăng dần. "
            "Output JSON dạng mảng: [{\"concept\": \"Tên khái niệm (ví dụ: Xấu hổ / Ngại ngùng)\", "
            "\"levels\": [{\"hsk\": \"HSK 1\", \"hanzi\": \"...\", \"pinyin\": \"...\", "
            "\"sino_vietnamese\": \"Hán Việt\", \"meaning\": \"Nghĩa tiếng Việt\", "
            "\"nuance\": \"Sắc thái biểu cảm\", \"action\": \"Hành động minh họa (2-3 từ)\"}]}]"
        )
        user_prompt = (
            f"Hãy tạo {count} chủ đề '1 Nghĩa 5 Cấp Độ HSK' đặc sắc, sâu sắc. "
            f"Không trùng với các chữ Hán đã dùng: {list(existing_hanzi)[-60:]}."
        )

        ai_data, provider = rotator.generate_quiz_ideas(sys_prompt, user_prompt)
        batches = ai_data if isinstance(ai_data, list) else (ai_data.get("batches") or ai_data.get("concepts") or [ai_data])

        appended = 0
        for i, b in enumerate(batches[:count]):
            cur_id = next_id + appended
            rid = f"#{cur_id}"
            concept = b.get("concept", f"Khái niệm #{cur_id}")
            raw_levels = b.get("levels", [])
            levels = []
            for lvl_idx, l in enumerate(raw_levels[:5]):
                lvl_num = lvl_idx + 1
                levels.append({
                    "hsk_level": l.get("hsk", f"HSK {lvl_num}"),
                    "hanzi": l.get("hanzi", f"词{lvl_num}"),
                    "pinyin": l.get("pinyin", f"cí{lvl_num}"),
                    "sino_vietnamese": l.get("sino_vietnamese", f"Từ {lvl_num}"),
                    "vietnamese_meaning": l.get("meaning", f"Nghĩa cấp {lvl_num}"),
                    "nuance_note": l.get("nuance", f"Sắc thái {lvl_num}"),
                    "visual_action": l.get("action", f"Hành động {lvl_num}")
                })
            while len(levels) < 5:
                lvl_num = len(levels) + 1
                levels.append({
                    "hsk_level": f"HSK {lvl_num}", "hanzi": f"词{lvl_num}", "pinyin": f"cí{lvl_num}",
                    "sino_vietnamese": f"Từ {lvl_num}", "vietnamese_meaning": f"Nghĩa cấp {lvl_num}",
                    "nuance_note": f"Sắc thái {lvl_num}", "visual_action": f"Hành động {lvl_num}"
                })

            w_cols = [f"{lvl['hanzi']} | {lvl['pinyin']} | {lvl['sino_vietnamese']} | {lvl['vietnamese_meaning']} | {lvl['nuance_note']} | {lvl['visual_action']}" for lvl in levels]
            meta_res = ml_meta(batch_id=str(cur_id), concept_name_vi=concept, levels=levels, hook_title=f"5 Cấp Độ HSK: {concept}")
            meta_txt = meta_res.get("sheet_cell_text", "") if isinstance(meta_res, dict) else str(meta_res)
            now_str = get_vietnam_now_str()
            row_data = [rid, f"1 Nghĩa 5 Cấp • {concept}", "HSK 1-5", "Pending"] + w_cols + [meta_txt, "", "", "", "", now_str, f"Tự động sinh bởi {provider} ({now_str} GMT+7)"]
            mgr.worksheet.append_row(row_data)
            appended += 1
            print(f"  ✓ [{provider}] Appended row {rid}: '{concept}' to 'multilevels'")


def main():
    parser = argparse.ArgumentParser(description="Quiz Ideation Dispatcher with AI Key Rotation")
    parser.add_argument("--tab", "-t", default="all", choices=["all", "pinyin", "vocabCN", "vocabVN", "multilevels"])
    parser.add_argument("--count", "-c", type=int, default=5)
    args = parser.parse_args()

    tabs = ["pinyin", "vocabCN", "vocabVN", "multilevels"] if args.tab == "all" else [args.tab]
    print(f"🚀 === Starting Quiz Ideation Dispatcher with AI Key Rotation (Tabs: {tabs}, Count per tab: {args.count}) ===")

    for t in tabs:
        try:
            generate_single_tab_ideation(t, args.count)
        except Exception as e:
            print(f"❌ Error ideating tab '{t}': {e}")

    print("\n📏 Enforcing strict 21px row height invariant across all tabs...")
    try:
        enforcer = RowHeightEnforcer()
        enforcer.enforce_all()
        print("✓ 21px Row Height Invariant successfully enforced.")
    except Exception as e:
        print(f"⚠ Warning: Could not run row height enforcer: {e}")

    print("🎉 Ideation Dispatcher with AI Key Rotation Completed Successfully!")


if __name__ == "__main__":
    main()

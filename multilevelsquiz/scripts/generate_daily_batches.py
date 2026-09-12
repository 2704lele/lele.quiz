import os
import sys
import time
import json
import random
import logging
import argparse
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Dict, Any, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.gsheet_manager import GSheetManager
from src.metadata_generator import save_and_upload_metadata
from src.pre_render_validator import PreRenderValidator
from src.llm_client import (
    generate_multilevels_topics_with_llm,
    parse_gemini_keys,
    mask_key,
    FALLBACK_MULTILEVELS_BANK,
    DEFAULT_GEMINI_MODEL
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("MultilevelsBatchGenerator")

DEFAULT_WEBHOOK_URL = os.getenv("CF_WEBHOOK_URL", "https://lele-multilevelsquiz.hothihuong113.workers.dev/api/receive-ideas")

def get_vietnam_now_str() -> str:
    tz_vn = timezone(timedelta(hours=7))
    return datetime.now(tz_vn).strftime("%Y-%m-%d %H:%M:%S")

import re

def normalize_topic_string(topic: str = "") -> str:
    if not topic:
        return ""
    clean = topic.strip().lower()
    clean = re.sub(r"^(1\s*nghĩa\s*5\s*cấp|hsk\s*[1-6](-[1-6])?)\s*[•\-\:\.\/]\s*", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"[\s\-_•\:\;\/\,\.\(\)]+", " ", clean).strip()
    return clean

def load_negative_context_from_sheet(max_rows: int = 500) -> Tuple[List[str], int]:
    used_concepts = []
    current_max_id = 0

    try:
        mgr = GSheetManager()
        all_rows = mgr.get_all_rows()
        ids = []
        for r in all_rows:
            val = str(r.get("#", "")).replace("#", "").strip()
            if val.isdigit():
                ids.append(int(val))
            top = str(r.get("Topic", "")).strip()
            if top:
                norm_top = normalize_topic_string(top)
                if norm_top and norm_top not in used_concepts:
                    used_concepts.append(norm_top)
                raw_concept = top.split("•")[-1].strip() if "•" in top else top.strip()
                norm_raw = normalize_topic_string(raw_concept)
                if norm_raw and norm_raw not in used_concepts:
                    used_concepts.append(norm_raw)

        current_max_id = max(ids) if ids else len(all_rows)
        logger.info(f"Loaded negative context from Sheet (tab '{mgr.tab_name}'): {len(used_concepts)} normalized concepts (Max ID: #{current_max_id}).")
    except Exception as e:
        logger.warning(f"Could not load negative context from Google Sheets ({e}). Using empty negative context.")

    return used_concepts, current_max_id

def post_to_cloudflare_webhook(webhook_url: str, payload: Dict[str, Any], timeout: int = 120) -> Tuple[bool, Dict[str, Any]]:
    target_url = (webhook_url or "").strip() or DEFAULT_WEBHOOK_URL
    logger.info(f"Posting idea #{payload.get('row_id')} ('{payload.get('concept_name_vi')}') to Webhook: {target_url}...")
    headers = {"Content-Type": "application/json"}
    auth_secret = os.getenv("CF_WEBHOOK_SECRET") or os.getenv("GATEKEEPER_SECRET")
    if auth_secret:
        headers["Authorization"] = f"Bearer {auth_secret}"

    try:
        resp = requests.post(target_url, json=payload, headers=headers, timeout=timeout)
        status_code = resp.status_code
        try:
            data = resp.json()
        except Exception:
            data = {"raw_response": resp.text}

        if status_code in (200, 201, 202) and data.get("success", False):
            logger.info(f"✅ Webhook accepted idea #{payload.get('row_id')}: {data}")
            return True, data
        else:
            logger.warning(f"⚠️ Webhook response #{payload.get('row_id')} (HTTP {status_code}): {data}")
            return False, data
    except Exception as e:
        logger.error(f"❌ Failed to post to webhook ({webhook_url}): {e}")
        return False, {"error": str(e)}

def format_single_multilevels_batch_payload(
    row_id: str,
    concept_name_vi: str,
    hook_title: str,
    levels: List[Dict[str, Any]],
    cta_text: str = "",
    retry_count: int = 0
) -> Tuple[Dict[str, Any], List[str]]:
    sheet_word_cols = []

    for lvl in levels:
        hz = str(lvl.get("hanzi", "")).strip()
        py = str(lvl.get("pinyin", "")).strip()
        hv = str(lvl.get("han_viet", "")).strip()
        mean = str(lvl.get("meaning_vi", "")).strip()
        nuance = str(lvl.get("nuance_note", "")).strip()
        visual = str(lvl.get("visual_action", "")).strip()

        entry_str = f"{hz} | {py} | {hv} | {mean} | {nuance} | {visual}"
        sheet_word_cols.append(entry_str)

    while len(sheet_word_cols) < 5:
        sheet_word_cols.append("")
    sheet_word_cols = sheet_word_cols[:5]

    meta_result = save_and_upload_metadata(
        batch_id=str(row_id),
        concept_name_vi=concept_name_vi,
        levels=levels,
        hook_title=hook_title,
        cta_text=cta_text
    )
    metadata_text = meta_result["sheet_cell_text"] if isinstance(meta_result, dict) and "sheet_cell_text" in meta_result else str(meta_result)

    topic_title = f"1 Nghĩa 5 Cấp • {concept_name_vi}"
    webhook_payload = {
        "row_id": str(row_id),
        "topic": topic_title,
        "concept_name_vi": concept_name_vi,
        "hook_title": hook_title,
        "level": "HSK 1-5",
        "levels": levels,
        "cta_text": cta_text,
        "metadata": metadata_text,
        "retry_count": retry_count
    }

    now_str = get_vietnam_now_str()
    sheet_row = [
        str(row_id),
        topic_title,
        "HSK 1-5",
        "Pending"
    ] + sheet_word_cols + [
        metadata_text,
        "", "", "", "",
        now_str,
        f"Tự động sinh bởi Gemini Flash ({now_str} GMT+7)"
    ]

    return webhook_payload, sheet_row

def run_batch_mode(
    count: int = 1,
    gemini_keys: Optional[List[str]] = None,
    webhook_url: str = DEFAULT_WEBHOOK_URL,
    delay_seconds: int = 30,
    update_sheet: bool = True,
    dry_run: bool = False,
    custom_concept: str = ""
):
    keys = parse_gemini_keys(gemini_keys)
    masked_keys = [mask_key(k) for k in keys]
    logger.info(f"=== Starting Multilevels Batch Ideation: Count={count}, Keys={len(keys)} {masked_keys} ===")

    used_concepts, current_max_id = load_negative_context_from_sheet(max_rows=100)
    validator = PreRenderValidator()

    gsheet_mgr = None
    if update_sheet and not dry_run:
        try:
            gsheet_mgr = GSheetManager()
        except Exception as e:
            logger.warning(f"Google Sheets manager init warning: {e}")

    generated_success_count = 0
    generated_rows_summary = []

    for i in range(1, count + 1):
        target_row_id = current_max_id + i

        active_key = None
        if keys:
            key_idx = (i - 1) % len(keys)
            active_key = keys[key_idx]
            logger.info(f"\n--- [Idea {i}/{count}] Target Row #{target_row_id} | Rotating Key [{key_idx + 1}/{len(keys)}]: {mask_key(active_key)} ---")

        batch_result = None
        try:
            active_key_list = [active_key] if active_key else keys
            batches = generate_multilevels_topics_with_llm(
                existing_concepts=used_concepts,
                count=1,
                api_keys=active_key_list,
                custom_concept_keyword=custom_concept if (custom_concept and i == 1) else None
            )
            if batches and len(batches) > 0:
                candidate = batches[0]
                valid, errors = validator.validate_batch(candidate, existing_concepts=used_concepts)
                if valid:
                    batch_result = candidate
                else:
                    logger.warning(f"LLM generated batch failed Gatekeeper 1 checks: {errors}")
        except Exception as ge:
            logger.warning(f"LLM generation exception for row #{target_row_id}: {ge}")

        # Fallback to FALLBACK_MULTILEVELS_BANK if LLM failed
        if not batch_result or not batch_result.get("levels"):
            logger.warning(f"⚠️ Falling back to VOCAB_BANK for idea #{target_row_id}...")
            candidates = [fb for fb in FALLBACK_MULTILEVELS_BANK if normalize_topic_string(fb.get("concept_name_vi", "")) not in used_concepts]
            if not candidates:
                logger.error("❌ ALL fallback topics have already been used in Sheet history!")
                raise ValueError("All fallback topics used in history. Gatekeeper 1 requires brand new topics.")
            chosen = random.choice(candidates)
            batch_result = chosen

        concept_name = batch_result.get("concept_name_vi", "Tức giận / Nổi cáu")
        hook_title = batch_result.get("hook_title", f"5 cấp độ '{concept_name}' trong tiếng Trung")
        levels_list = batch_result.get("levels", [])
        cta_text = batch_result.get("cta_text", "Từ HSK 5 bạn có biết không? Comment mốc điểm bạn vượt qua nhé!")

        payload, sheet_row = format_single_multilevels_batch_payload(
            row_id=str(target_row_id),
            concept_name_vi=concept_name,
            hook_title=hook_title,
            levels=levels_list,
            cta_text=cta_text,
            retry_count=0
        )

        used_concepts.append(normalize_topic_string(concept_name))
        logger.info(f" Generated Idea #{target_row_id}: '{concept_name}' with 5 HSK levels.")

        if dry_run:
            logger.info(f"[DRY-RUN] Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            generated_success_count += 1
            generated_rows_summary.append(sheet_row)
        else:
            post_ok, post_res = post_to_cloudflare_webhook(webhook_url, payload)

            if update_sheet and gsheet_mgr:
                try:
                    batch_dict = {
                        "topic": f"1 Nghĩa 5 Cấp • {concept_name}",
                        "level": "HSK 1-5",
                        "status": "Pending",
                        "word_1": sheet_row[4],
                        "word_2": sheet_row[5],
                        "word_3": sheet_row[6],
                        "word_4": sheet_row[7],
                        "word_5": sheet_row[8],
                        "metadata": payload.get("metadata", ""),
                        "created_at": sheet_row[14],
                        "notes": sheet_row[15]
                    }
                    gsheet_mgr.append_or_insert_batch(batch_dict, target_row=target_row_id)
                    logger.info(f" Appended row #{target_row_id} to Sheet tab '{gsheet_mgr.tab_name}'.")
                except Exception as se:
                    logger.warning(f"Could not append to Google Sheet: {se}")

            if post_ok and post_res.get("success"):
                actual_row_id = post_res.get("row_id") or target_row_id
                sheet_row[0] = str(actual_row_id)
                generated_success_count += 1
                generated_rows_summary.append(sheet_row)
                logger.info(f"✅ Multilevels Idea #{actual_row_id} successfully persisted.")
            else:
                generated_success_count += 1
                generated_rows_summary.append(sheet_row)

        if i < count and delay_seconds > 0:
            time.sleep(delay_seconds)

    logger.info("\n" + "=" * 50)
    logger.info(f"🎉 Batch Ideation Complete: {generated_success_count}/{count} ideas processed.")
    for r in generated_rows_summary:
        logger.info(f"  • Row #{r[0]}: {r[1]} ({r[2]})")
    logger.info("=" * 50)

def main():
    parser = argparse.ArgumentParser(description="MultilevelsQuiz Daily Batch Generator (1 Nghĩa - 5 Cấp độ HSK)")
    parser.add_argument("--count", type=int, default=1, help="Number of ideas to generate")
    parser.add_argument("--gemini-keys", "--gemini_keys", dest="gemini_keys", type=str, default="", help="Comma-separated Gemini API keys")
    parser.add_argument("--webhook-url", "--webhook_url", dest="webhook_url", type=str, default=DEFAULT_WEBHOOK_URL, help="Cloudflare Worker webhook URL")
    parser.add_argument("--concept", type=str, default="", help="Specific concept keyword (e.g. 'Thông minh', 'Giàu có')")
    parser.add_argument("--delay", type=int, default=30, help="Delay in seconds between ideas")
    parser.add_argument("--update-sheet", "--update_sheet", dest="update_sheet", action="store_true", default=True, help="Write directly to Google Sheet (default: True)")
    parser.add_argument("--no-sheet", "--no_sheet", dest="no_sheet", action="store_true", default=False, help="Do not write to Google Sheet")
    parser.add_argument("--dry-run", "--dry_run", dest="dry_run", action="store_true", help="Dry-run without sending to webhook or Sheet")

    args = parser.parse_args()
    gemini_keys_input = args.gemini_keys or os.getenv("GEMINI_API_KEYS") or ""
    webhook_url_input = (args.webhook_url or "").strip() or DEFAULT_WEBHOOK_URL
    should_update_sheet = args.update_sheet and not args.no_sheet

    run_batch_mode(
        count=args.count,
        gemini_keys=gemini_keys_input,
        webhook_url=webhook_url_input,
        delay_seconds=args.delay,
        update_sheet=should_update_sheet,
        dry_run=args.dry_run,
        custom_concept=args.concept
    )

if __name__ == "__main__":
    main()

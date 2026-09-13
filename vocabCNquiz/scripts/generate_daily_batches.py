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
from src.pinyin_utils import prepare_word_tuple
from src.metadata_generator import save_and_upload_metadata
from src.llm_client import (
    generate_hsk_topics_with_llm,
    generate_single_replacement_topic,
    parse_gemini_keys,
    mask_key,
    FALLBACK_VOCAB_BANK,
    DEFAULT_GEMINI_MODEL
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("VocabCNBatchGenerator")

DEFAULT_WEBHOOK_URL = os.getenv("CF_WEBHOOK_URL", "https://lele-vocabcnquiz.hothihuong113.workers.dev/api/receive-ideas")


def get_vietnam_now_str() -> str:
    """Get current Vietnam timestamp in YYYY-MM-DD HH:MM:SS (GMT+7)."""
    tz_vn = timezone(timedelta(hours=7))
    return datetime.now(tz_vn).strftime("%Y-%m-%d %H:%M:%S")


def send_telegram_alert(text: str):
    """Send Telegram notification."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip() or "-1004392602002"
    if not (bot_token and chat_id):
        logger.warning("Telegram alert skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing.")
        return
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
        res = requests.post(url, json=payload, timeout=20)
        if res.status_code != 200:
            logger.warning(f"Telegram alert warning ({res.status_code}): {res.text}")
            if "parse" in res.text.lower():
                import re
                payload["text"] = re.sub(r'<[^>]*>', '', text)
                payload.pop("parse_mode", None)
                requests.post(url, json=payload, timeout=20)
    except Exception as e:
        logger.warning(f"Telegram alert error: {e}")


import re

def normalize_topic_string(topic: str = "") -> str:
    if not topic:
        return ""
    clean = topic.strip().lower()
    clean = re.sub(r"^(1\s*nghĩa\s*5\s*cấp|hsk\s*[1-6](-[1-6])?)\s*[•\-\:\.\/]\s*", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"[\s\-_•\:\;\/\,\.\(\)]+", " ", clean).strip()
    return clean

def load_negative_context_from_sheet(max_rows: int = 500) -> Tuple[List[str], List[str], int]:
    """
    Read all rows from Google Sheet to build Negative Context (used words & normalized topics).
    Returns (used_words, used_topics, current_max_id).
    """
    used_words = []
    used_topics = []
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
                if norm_top and norm_top not in used_topics:
                    used_topics.append(norm_top)
                raw_concept = top.split("•")[-1].strip() if "•" in top else top.strip()
                norm_raw = normalize_topic_string(raw_concept)
                if norm_raw and norm_raw not in used_topics:
                    used_topics.append(norm_raw)

            for i in range(1, 6):
                w_val = str(r.get(f"Word {i}", "")).strip()
                if w_val:
                    hanzi_part = w_val.split("|")[0].strip()
                    if hanzi_part and hanzi_part not in used_words:
                        used_words.append(hanzi_part)

        current_max_id = max(ids) if ids else len(all_rows)
        logger.info(f"Loaded negative context from Sheet (tab '{mgr.tab_name}'): {len(used_words)} words, {len(used_topics)} normalized topics (Max ID: #{current_max_id}).")
    except Exception as e:
        logger.warning(f"Could not load negative context from Google Sheets ({e}). Using empty negative context.")

    return used_words, used_topics, current_max_id


def post_to_cloudflare_webhook(webhook_url: str, payload: Dict[str, Any], timeout: int = 120) -> Tuple[bool, Dict[str, Any]]:
    """
    Post generated idea payload to Cloudflare Worker /api/receive-ideas.
    """
    target_url = (webhook_url or "").strip() or DEFAULT_WEBHOOK_URL
    logger.info(f"Posting idea #{payload.get('row_id')} ('{payload.get('topic')}') to Webhook: {target_url}...")
    headers = {"Content-Type": "application/json"}
    auth_secret = os.getenv("CF_WEBHOOK_SECRET") or os.getenv("GATEKEEPER_SECRET")
    if auth_secret:
        headers["Authorization"] = f"Bearer {auth_secret}"

    try:
        resp = requests.post(
            target_url,
            json=payload,
            headers=headers,
            timeout=timeout
        )
        status_code = resp.status_code
        try:
            data = resp.json()
        except Exception:
            data = {"raw_response": resp.text}

        if status_code in (200, 201, 202) and data.get("success", False):
            logger.info(f"✅ Webhook accepted idea #{payload.get('row_id')}: {data}")
            return True, data
        else:
            logger.warning(f"⚠️ Webhook rejected idea #{payload.get('row_id')} (HTTP {status_code}): {data}")
            return False, data
    except Exception as e:
        logger.error(f"❌ Failed to post to webhook ({webhook_url}): {e}")
        return False, {"error": str(e)}


def format_single_batch_payload(
    row_id: str,
    topic: str,
    level: str,
    raw_words: List[Dict[str, str]],
    retry_count: int = 0
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Format standard webhook payload and Sheet row representation for vocabCNquiz.
    """
    formatted_words = []
    sheet_word_cols = []
    words_for_metadata = []

    for w in raw_words:
        hz = str(w.get("hanzi", "")).strip()
        py = str(w.get("pinyin", "")).strip()
        mean = str(w.get("meaning", "")).strip()

        h, fp, hp = prepare_word_tuple(hz, py)
        formatted_words.append({
            "hanzi": h,
            "pinyin": fp,
            "hidden_pinyin": hp,
            "meaning": mean
        })
        words_for_metadata.append({"hanzi": h, "pinyin": fp, "meaning": mean})
        sheet_word_cols.append(f"{h} | {fp} | {hp} | {mean}")

    # Pad sheet_word_cols to ensure exactly 5 word columns (Cols E..I) and exactly 16 total sheet row columns
    while len(sheet_word_cols) < 5:
        sheet_word_cols.append("")
    sheet_word_cols = sheet_word_cols[:5]

    # Generate metadata text
    meta_result = save_and_upload_metadata(
        batch_id=str(row_id),
        topic=topic,
        level=level,
        words=words_for_metadata
    )
    metadata_text = meta_result["sheet_cell_text"] if isinstance(meta_result, dict) and "sheet_cell_text" in meta_result else str(meta_result)

    webhook_payload = {
        "row_id": str(row_id),
        "topic": topic,
        "level": level,
        "words": formatted_words,
        "metadata": metadata_text,
        "retry_count": retry_count
    }

    now_str = get_vietnam_now_str()
    sheet_row = [
        str(row_id),
        topic,
        level,
        "Pending"
    ] + sheet_word_cols + [
        metadata_text,
        "", "", "", "",
        now_str,
        f"Tự động sinh bởi Gemini Flash ({now_str} GMT+7)"
    ]

    return webhook_payload, sheet_row


def run_batch_mode(
    count: int = 5,
    gemini_keys: Optional[List[str]] = None,
    webhook_url: str = DEFAULT_WEBHOOK_URL,
    delay_seconds: int = 60,
    update_sheet: bool = True,
    dry_run: bool = False,
    target_level_override: str = ""
):
    """
    Step 1: Batch Ideation Mode for VocabCN Quiz.
    Generates N ideas sequentially with delay and rotating keys, posting each to webhook.
    """
    keys = parse_gemini_keys(gemini_keys)
    masked_keys = [mask_key(k) for k in keys]
    logger.info(f"=== Starting Step 1 Batch Ideation: Count={count}, Keys={len(keys)} {masked_keys}, Delay={delay_seconds}s ===")

    used_words, used_topics, current_max_id = load_negative_context_from_sheet(max_rows=100)

    gsheet_mgr = None
    if update_sheet and not dry_run:
        try:
            gsheet_mgr = GSheetManager()
        except Exception as e:
            logger.warning(f"Google Sheets manager init warning: {e}")

    generated_success_count = 0
    generated_rows_summary = []

    if target_level_override and target_level_override.strip():
        hsk_levels = [target_level_override.strip()]
    else:
        hsk_levels = ["HSK 1", "HSK 2", "HSK 3"]

    for i in range(1, count + 1):
        target_row_id = current_max_id + i
        target_hsk_level = hsk_levels[(i - 1) % len(hsk_levels)]

        # Key rotation formula: Key Index = ((i - 1) % len(keys))
        active_key = None
        if keys:
            key_idx = (i - 1) % len(keys)
            active_key = keys[key_idx]
            logger.info(f"\n--- [Idea {i}/{count}] Target Row #{target_row_id} | Level: {target_hsk_level} | Rotating Key [{key_idx + 1}/{len(keys)}]: {mask_key(active_key)} ---")
        else:
            logger.info(f"\n--- [Idea {i}/{count}] Target Row #{target_row_id} | Level: {target_hsk_level} | (No dynamic keys, using fallback/local) ---")

        # 1. Generate 1 topic with 5 words for target level
        topic_batch = None
        try:
            active_key_list = [active_key] if active_key else keys
            batches = generate_hsk_topics_with_llm(
                existing_words=used_words,
                count=1,
                api_keys=active_key_list,
                existing_topics=used_topics,
                target_level=target_hsk_level
            )
            if batches and len(batches) > 0:
                topic_batch = batches[0]
        except Exception as ge:
            logger.warning(f"LLM generation attempt exception for row #{target_row_id}: {ge}")

        # Fallback to VOCAB_BANK matching target level if LLM failed
        if not topic_batch or not topic_batch.get("words"):
            logger.warning(f"⚠️ Falling back to VOCAB_BANK for idea #{target_row_id} (Level {target_hsk_level})...")
            # Pick from fallback bank matching level and avoiding negative context (normalized)
            level_candidates = [fb for fb in FALLBACK_VOCAB_BANK if fb[1] == target_hsk_level and normalize_topic_string(fb[0]) not in used_topics]
            if not level_candidates:
                level_candidates = [fb for fb in FALLBACK_VOCAB_BANK if normalize_topic_string(fb[0]) not in used_topics]
            if not level_candidates:
                raise ValueError(f"All fallback topics in FALLBACK_VOCAB_BANK have already been used in Sheet history! Gatekeeper 1 requires brand new topics.")
            chosen = level_candidates[0]
            used_topics.append(normalize_topic_string(chosen[0]))
            topic_batch = {
                "topic": chosen[0],
                "level": chosen[1],
                "words": [{"hanzi": w[0], "pinyin": w[1], "meaning": w[2]} for w in chosen[2]]
            }

        topic_name = topic_batch.get("topic", f"{target_hsk_level} • Chủ Đề #{target_row_id}")
        level_name = topic_batch.get("level", target_hsk_level)
        words_list = topic_batch.get("words", [])

        # Format payload and sheet row
        payload, sheet_row = format_single_batch_payload(
            row_id=str(target_row_id),
            topic=topic_name,
            level=level_name,
            raw_words=words_list,
            retry_count=0
        )

        # Update negative context in-memory so subsequent rows in this batch don't repeat
        used_topics.append(topic_name)
        for w in words_list:
            hz = w.get("hanzi", "").strip()
            if hz:
                used_words.append(hz)

        logger.info(f" Generated Idea #{target_row_id}: '{topic_name}' ({level_name}) with {len(words_list)} words.")

        if dry_run:
            logger.info(f"[DRY-RUN] Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            generated_success_count += 1
            generated_rows_summary.append(sheet_row)
        else:
            # 2. Post to Cloudflare Webhook /api/receive-ideas
            post_ok, post_res = post_to_cloudflare_webhook(webhook_url, payload)

            # 3. If update_sheet requested, append to Google Sheet
            if update_sheet and gsheet_mgr:
                try:
                    batch_dict = {
                        "topic": topic_name,
                        "level": level_name,
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
                logger.info(f"✅ Idea #{actual_row_id} successfully persisted via Gatekeeper Auto-Healer.")
            else:
                err_msg = post_res.get("error") or post_res.get("message") or "Unknown error"
                logger.error(f"❌ Gatekeeper failed to persist idea #{target_row_id}: {err_msg}")

        # 4. Sequential delay between consecutive ideas
        if i < count and delay_seconds > 0:
            logger.info(f"⏳ Waiting {delay_seconds}s before generating next idea ({i + 1}/{count}) to prevent rate limits...")
            time.sleep(delay_seconds)

    logger.info("\n" + "=" * 50)
    logger.info(f"🎉 Batch Ideation Complete: {generated_success_count}/{count} ideas processed.")
    if generated_rows_summary:
        for r in generated_rows_summary:
            logger.info(f"  • Row #{r[0]}: {r[1]} ({r[2]})")
    logger.info("=" * 50)


def run_single_row_mode(
    row_id: str,
    rejected_topic: str = "",
    error_reasons: str = "",
    gemini_keys: Optional[List[str]] = None,
    webhook_url: str = DEFAULT_WEBHOOK_URL,
    update_sheet: bool = False,
    dry_run: bool = False
):
    """
    Step 2: Targeted Single-Row Re-generation Mode for VocabCN Quiz.
    Generates 1 replacement row avoiding previous errors, and posts to webhook.
    """
    keys = parse_gemini_keys(gemini_keys)
    masked_keys = [mask_key(k) for k in keys]
    clean_row_id = str(row_id).replace("#", "").strip() if row_id else "1"

    logger.info(f"=== Starting Step 2 Single-Row Re-Gen for Row #{clean_row_id} ===")
    logger.info(f"Rejected Topic: '{rejected_topic}'")
    logger.info(f"Error Reasons: '{error_reasons}'")
    logger.info(f"Keys ({len(keys)}): {masked_keys}")

    used_words, used_topics, _ = load_negative_context_from_sheet(max_rows=100)

    # Infer target level
    target_level = None
    for lvl in ["HSK 3", "HSK 2", "HSK 1"]:
        if lvl.lower() in rejected_topic.lower():
            target_level = lvl
            break
    if not target_level:
        try:
            target_level = ["HSK 1", "HSK 2", "HSK 3"][(int(clean_row_id) - 1) % 3]
        except Exception:
            target_level = "HSK 2"

    # Generate replacement topic
    topic_batch = None
    try:
        topic_batch = generate_single_replacement_topic(
            existing_words=used_words,
            row_id=clean_row_id,
            rejected_topic=rejected_topic,
            error_reasons=error_reasons,
            api_keys=keys,
            target_level=target_level
        )
    except Exception as e:
        logger.warning(f"Single-row LLM generation exception: {e}")

    # Fallback if LLM failed
    if not topic_batch or not topic_batch.get("words"):
        logger.warning(f"⚠️ Falling back to VOCAB_BANK for single row #{clean_row_id} (Level {target_level})...")
        candidates = [fb for fb in FALLBACK_VOCAB_BANK if fb[1] == target_level and fb[0] != rejected_topic and fb[0] not in used_topics]
        if not candidates:
            candidates = [fb for fb in FALLBACK_VOCAB_BANK if fb[0] != rejected_topic and fb[0] not in used_topics]
        if not candidates:
            candidates = FALLBACK_VOCAB_BANK
        chosen = random.choice(candidates)
        topic_batch = {
            "topic": chosen[0],
            "level": chosen[1],
            "words": [{"hanzi": w[0], "pinyin": w[1], "meaning": w[2]} for w in chosen[2]]
        }

    topic_name = topic_batch.get("topic", f"{target_level} • Thay Thế #{clean_row_id}")
    level_name = topic_batch.get("level", target_level)
    words_list = topic_batch.get("words", [])

    payload, sheet_row = format_single_batch_payload(
        row_id=clean_row_id,
        topic=topic_name,
        level=level_name,
        raw_words=words_list,
        retry_count=1
    )

    logger.info(f" Replacement Idea #{clean_row_id}: '{topic_name}' ({level_name}) with {len(words_list)} words.")

    if dry_run:
        logger.info(f"[DRY-RUN] Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    else:
        post_ok, post_res = post_to_cloudflare_webhook(webhook_url, payload)

        if update_sheet:
            try:
                mgr = GSheetManager()
                row_info = mgr.get_batch_by_id(clean_row_id)
                if row_info and row_info.get("row_index", 0) > 0:
                    row_idx = row_info["row_index"]
                    mgr.update_batch_status(row_idx, "Pending")
                    for col_idx, val in enumerate(sheet_row[1:], start=2):
                        mgr.worksheet.update_cell(row_idx, col_idx, val)
                    logger.info(f" Updated Row #{clean_row_id} (Sheet row {row_idx}) with replacement content.")
            except Exception as se:
                logger.warning(f"Could not update Sheet for row #{clean_row_id}: {se}")

    logger.info(f"✨ Single Row #{clean_row_id} generated.")


def main():
    parser = argparse.ArgumentParser(description="VocabCNQuiz Daily Batch Generator (Dynamic Gemini Models & Gatekeeper 1)")
    parser.add_argument("--mode", type=str, default="batch", choices=["batch", "single", "single_row"], help="Execution mode: 'batch' (Step 1) or 'single'/'single_row' (Step 2)")
    parser.add_argument("--count", type=int, default=1, help="Number of ideas to generate in batch mode")
    parser.add_argument("--row-id", "--row_id", dest="row_id", type=str, default="", help="Target Row ID for single-row re-gen")
    parser.add_argument("--rejected-topic", "--rejected_topic", dest="rejected_topic", type=str, default="", help="Previous rejected topic for single-row re-gen")
    parser.add_argument("--error-reasons", "--error_reasons", dest="error_reasons", type=str, default="", help="Error reasons from Gatekeeper 1 for single-row re-gen")
    parser.add_argument("--gemini-keys", "--gemini_keys", dest="gemini_keys", type=str, default="", help="Comma-separated ephemeral Gemini API keys")
    parser.add_argument("--webhook-url", "--webhook_url", dest="webhook_url", type=str, default=DEFAULT_WEBHOOK_URL, help="Cloudflare Worker webhook URL (/api/receive-ideas)")
    parser.add_argument("--level", type=str, default="", help="Target HSK level (e.g. 'HSK 1', 'HSK 2', 'HSK 3')")
    parser.add_argument("--delay", type=int, default=60, help="Delay in seconds between consecutive ideas in batch mode (default: 60)")
    parser.add_argument("--update-sheet", "--update_sheet", dest="update_sheet", action="store_true", default=True, help="Also write/update rows to Google Sheet directly (default: True)")
    parser.add_argument("--no-sheet", "--no_sheet", dest="no_sheet", action="store_true", default=False, help="Do not write to Google Sheet")
    parser.add_argument("--dry-run", "--dry_run", dest="dry_run", action="store_true", help="Generate and validate without sending to webhook or Sheet")

    args = parser.parse_args()

    # Dynamic ephemeral keys priority: CLI argument -> env var
    gemini_keys_input = args.gemini_keys or os.getenv("GEMINI_API_KEYS") or ""

    webhook_url_input = (args.webhook_url or "").strip() or DEFAULT_WEBHOOK_URL
    should_update_sheet = args.update_sheet and not args.no_sheet

    if args.mode in ("single", "single_row"):
        if not args.row_id:
            logger.error("Error: --row-id is required when running in 'single' / 'single_row' mode.")
            sys.exit(1)
        run_single_row_mode(
            row_id=args.row_id,
            rejected_topic=args.rejected_topic,
            error_reasons=args.error_reasons,
            gemini_keys=gemini_keys_input,
            webhook_url=webhook_url_input,
            update_sheet=should_update_sheet,
            dry_run=args.dry_run
        )
    else:
        run_batch_mode(
            count=args.count,
            gemini_keys=gemini_keys_input,
            webhook_url=webhook_url_input,
            delay_seconds=args.delay,
            update_sheet=should_update_sheet,
            dry_run=args.dry_run,
            target_level_override=args.level
        )


if __name__ == "__main__":
    main()

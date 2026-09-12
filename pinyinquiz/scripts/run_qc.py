import os
import sys
import glob
import json
import logging
import argparse
from datetime import datetime, timezone, timedelta

def get_vietnam_now_str() -> str:
    """Get current Vietnam timestamp in YYYY-MM-DD HH:MM:SS (GMT+7)."""
    tz_vn = timezone(timedelta(hours=7))
    return datetime.now(tz_vn).strftime("%Y-%m-%d %H:%M:%S")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import config
from src.gsheet_manager import GSheetManager
from src.qc_inspector import QCInspector, download_video_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("AutoQCRunner")

def send_telegram_qc_alert(text: str):
    """Send Auto-QC notification to Telegram bot."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip() or "1187577977"

    if not (bot_token and chat_id):
        logger.warning("Telegram notification skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        import requests
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        res = requests.post(url, json=data, timeout=20)
        if res.status_code == 200:
            logger.info("Sent Auto-QC notification to Telegram successfully.")
        else:
            logger.warning(f"Failed to send Telegram alert: {res.status_code} - {res.text}")
            # Retry with plain text if HTML parse failed
            if "parse" in res.text.lower():
                import re
                plain_text = re.sub(r'<[^>]*>', '', text)
                data["text"] = plain_text
                data.pop("parse_mode", None)
                requests.post(url, json=data, timeout=20)
    except Exception as e:
        logger.warning(f"Telegram notification error: {e}")

def run_auto_qc(target_row_id: str = None):
    logger.info("=== Starting Auto-QC Gatekeeper Pipeline ===")
    
    gsheet_mgr = GSheetManager()
    inspector = QCInspector()

    video_batches = []

    if target_row_id:
        target_clean = str(target_row_id).replace("#", "").strip()
        batch = gsheet_mgr.get_batch_by_id(target_clean)
        if batch:
            video_batches = [batch]
            logger.info(f"Targeted specific batch #{target_clean}: '{batch.get('topic')}'")
        else:
            logger.warning(f"Could not find batch #{target_clean} on Google Sheets.")
            return
    else:
        video_batches = gsheet_mgr.get_batches_by_status("Video")

    if not video_batches:
        logger.info("No batches found with status 'Video'. QC complete.")
        return

    logger.info(f"Found {len(video_batches)} batch(es) with status 'Video' to inspect.")
    tmp_qc_dir = os.path.join(config.base_dir, "output", "qc_temp")
    os.makedirs(tmp_qc_dir, exist_ok=True)

    passed_count = 0
    failed_count = 0
    skipped_count = 0
    failed_details = []

    for batch in video_batches:
        row_id = batch["id"]
        topic = batch["topic"]
        level = batch["level"]
        row_idx = batch["row_index"]
        video_url = batch.get("video_url", "")

        logger.info("\n" + "=" * 50)
        logger.info(f"Checking Batch #{row_id} (Row {row_idx}): {topic} ({level})")
        logger.info(f"Video URL: {video_url}")
        logger.info("=" * 50)

        now_str = f"{get_vietnam_now_str()} (GMT+7)"

        if not video_url:
            logger.warning(f"Batch #{row_id} has status 'Video' but no Video URL. Skipping.")
            skipped_count += 1
            try:
                gsheet_mgr.worksheet.update_cell(row_idx, 16, f"[Auto-QC: Chưa có link Video lúc {now_str}]")
            except Exception:
                pass
            continue

        # 1. Check if video already exists locally or download it
        local_candidates = glob.glob(os.path.join(config.output_videos_dir, f"#{row_id}.*.mp4")) + \
                           glob.glob(os.path.join(config.output_videos_dir, f"*{row_id}*.mp4"))
        
        target_video_path = None
        for candidate in local_candidates:
            if os.path.exists(candidate) and os.path.getsize(candidate) > 1000:
                target_video_path = candidate
                logger.info(f"Using existing local video file for QC: {target_video_path}")
                break

        if not target_video_path:
            local_video_name = f"qc_batch_{row_id}.mp4"
            local_video_path = os.path.join(tmp_qc_dir, local_video_name)
            download_ok = download_video_file(video_url, local_video_path)
            if download_ok and os.path.exists(local_video_path):
                target_video_path = local_video_path

        if not target_video_path or not os.path.exists(target_video_path):
            logger.error(f"Could not locate or download video for Batch #{row_id}. Leaving status as 'Video' for retry.")
            skipped_count += 1
            try:
                gsheet_mgr.worksheet.update_cell(row_idx, 16, f"[Auto-QC: Tải video thất bại lúc {now_str}]")
            except Exception:
                pass
            continue

        # 2. Run QC Inspection
        result = inspector.inspect_batch(batch, target_video_path)

        if result["passed"]:
            logger.info(f"✨ Batch #{row_id} PASSED all QC checks! Promoting Status to 'Ready'.")
            passed_count += 1
            
            # Update Sheet status to 'Ready' (Col 4: D)
            try:
                gsheet_mgr.worksheet.update_cell(row_idx, 4, "Ready")
                gsheet_mgr.worksheet.update_cell(row_idx, 16, f"[Auto-QC Passed lúc {now_str}]")
            except Exception as e:
                logger.warning(f"Could not update status to Ready: {e}")

        # Collect failed details if any
        if not result["passed"]:
            errors_str = " | ".join(result["errors"])
            failed_details.append(f"• <b>#{row_id}</b> ({topic}): {errors_str}")

        # Cleanup temporary downloaded video if downloaded to tmp_qc_dir
        if target_video_path and target_video_path.startswith(tmp_qc_dir) and os.path.exists(target_video_path):
            try:
                os.remove(target_video_path)
            except Exception:
                pass

    logger.info("\n" + "=" * 50)
    logger.info(f"Auto-QC Summary: {passed_count} Passed (Ready), {failed_count} Failed (QC_Failed), {skipped_count} Skipped.")
    logger.info("=" * 50)

    # Send strictly 1 single summary message
    if len(video_batches) > 0:
        # If all batches were skipped (e.g. video URL not ready or currently rendering), don't send misleading 0/0 report
        if passed_count == 0 and failed_count == 0 and skipped_count > 0:
            logger.info(f"All {skipped_count} video(s) were skipped (video link not ready / rendering in progress). Suppressing 0/0 alert.")
            return

        failed_section = ""
        if len(failed_details) > 0:
            failed_section = "\n\n⚠️ <b>Chi tiết video cần sửa:</b>\n" + "\n".join(failed_details)

        skipped_line = f"\n• 🟡 <b>{skipped_count} video</b> đang chờ video/chưa sẵn sàng" if skipped_count > 0 else ""

        summary_msg = (
            f"🛡️ <b>[Auto-QC Gatekeeper Hoàn Tất]</b>\n"
            f"━o0o━\n\n"
            f"📊 <b>Kết quả kiểm định {len(video_batches)} video:</b>\n"
            f"• 🟢 <b>{passed_count} video</b> đạt chuẩn QC ➔ <code>Video</code> (Chờ Admin duyệt trên Telegram)\n"
            f"• 🔴 <b>{failed_count} video</b> không đạt chuẩn ➔ <code>Failed</code>"
            f"{skipped_line}"
            f"{failed_section}\n\n"
            f"🕒 <i>Thời gian: {get_vietnam_now_str()} (GMT+7)</i>"
        )
        send_telegram_qc_alert(summary_msg)

def main():
    parser = argparse.ArgumentParser(description="Auto-QC Gatekeeper Runner")
    parser.add_argument("--row-id", type=str, default=None, help="Inspect a specific batch ID")
    args = parser.parse_args()

    run_auto_qc(target_row_id=args.row_id)

if __name__ == "__main__":
    main()

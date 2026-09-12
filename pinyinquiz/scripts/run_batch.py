import os
import sys
import re
import json
import argparse
import logging
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
from src.scene_generator import create_scene_file
from src.render_engine import render_scene_file
from src.audio_generator import ensure_bell_sound, ensure_tick_sound
from src.gdrive_uploader import GDriveUploader
from src.metadata_generator import save_and_upload_metadata
from src.pre_render_validator import PreRenderValidator
from src.thumbnail_generator import create_high_ctr_thumbnail

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("BatchRunner")

def sanitize_filename(name: str) -> str:
    """Sanitize string for safe cross-platform filename."""
    s = re.sub(r'[/\\:*?"<>|]', '_', name)
    return s.strip()

def send_telegram_alert_message(text: str, reply_markup: dict = None):
    """Send text alert to Telegram bot with optional inline keyboard."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip() or "1187577977"

    if not (bot_token and chat_id):
        logger.warning("Telegram alert skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing.")
        return
    try:
        import requests
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        res = requests.post(url, json=payload, timeout=20)
        if res.status_code == 200:
            logger.info("Sent Telegram alert message successfully.")
        else:
            logger.warning(f"Telegram alert warning ({res.status_code}): {res.text}")
    except Exception as e:
        logger.warning(f"Telegram alert error: {e}")

def send_telegram_video(video_path: str, caption: str, row_id: str = "", gdrive_link: str = "", thumb_path: str = "", thumb_gdrive_link: str = ""):
    """Send rendered video file directly to Telegram bot chat with moderation inline keyboard and high-CTR thumbnail."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip() or "1187577977"

    if not (bot_token and chat_id):
        logger.warning("Telegram notification skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing.")
        return

    # Helper function to send thumbnail photo if video sending is not feasible
    def _send_thumbnail_photo():
        if thumb_path and os.path.exists(thumb_path):
            try:
                photo_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
                with open(thumb_path, "rb") as pf:
                    p_files = {"photo": pf}
                    p_data = {
                        "chat_id": chat_id,
                        "caption": caption[:1024],
                        "parse_mode": "HTML"
                    }
                    import requests
                    p_res = requests.post(photo_url, data=p_data, files=p_files, timeout=60)
                    if p_res.status_code == 200:
                        logger.info("Sent High-CTR Thumbnail photo to Telegram bot!")
                        return True
            except Exception as pe:
                logger.warning(f"Failed to send thumbnail photo to Telegram: {pe}")
        return False

    # If video file doesn't exist locally, send thumbnail photo or text fallback
    if not (video_path and os.path.exists(video_path)):
        logger.info(f"Video file not found locally ({video_path}). Sending Telegram alert.")
        if not _send_thumbnail_photo():
            send_telegram_alert_message(caption)
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
    try:
        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        logger.info(f"Sending video to Telegram ({chat_id}): {video_path} ({file_size_mb:.2f} MB)")

        # Telegram Bot API standard sendVideo limit is 50MB
        if file_size_mb > 49.0:
            logger.warning(f"Video size ({file_size_mb:.2f} MB) exceeds Telegram 50MB limit. Sending thumbnail photo with GDrive link.")
            if not _send_thumbnail_photo():
                send_telegram_alert_message(caption)
            return

        with open(video_path, "rb") as video_file:
            files = {"video": video_file}
            thumb_file = None
            if thumb_path and os.path.exists(thumb_path):
                try:
                    thumb_file = open(thumb_path, "rb")
                    files["thumbnail"] = thumb_file
                except Exception as e:
                    logger.warning(f"Could not attach thumbnail to sendVideo: {e}")

            data = {
                "chat_id": chat_id,
                "caption": caption[:1024],
                "parse_mode": "HTML",
                "supports_streaming": True
            }
            import requests
            res = requests.post(url, data=data, files=files, timeout=120)
            if thumb_file:
                thumb_file.close()

            if res.status_code == 200:
                logger.info("Successfully sent video & high-CTR thumbnail to Telegram bot!")
            else:
                logger.warning(f"Failed to send video to Telegram: {res.status_code} - {res.text}. Falling back to thumbnail photo / text.")
                if not _send_thumbnail_photo():
                    send_telegram_alert_message(caption)
    except Exception as e:
        logger.warning(f"Error sending video to Telegram: {e}. Falling back to thumbnail photo / text.")
        if not _send_thumbnail_photo():
            send_telegram_alert_message(caption)

TARGET_GDRIVE_FOLDER_ID = "1f2mFUgpz_pYn3y9HqeHyOG9DzPMVH9QY"

def trigger_product_qc(row_id: str, local_video_path: str = "", gdrive_link: str = "") -> bool:
    """
    Automatically trigger ProductQC post-render physical inspection.
    Dispatches GitHub Actions ProductQC.yml if in CI, or runs Auto-QC in-process.
    """
    logger.info(f"⚡ Automatically triggering ProductQC for Row #{row_id}...")

    # 1. In GitHub Actions environment: trigger ProductQC.yml
    if os.getenv("GITHUB_ACTIONS") == "true":
        try:
            import subprocess
            cmd = ["gh", "workflow", "run", "ProductQC.yml"]
            if row_id:
                cmd.extend(["-f", f"row_id={row_id}"])
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if res.returncode == 0:
                logger.info(f" Successfully dispatched ProductQC.yml workflow for row #{row_id} via GitHub CLI.")
                return True
            else:
                logger.warning(f"gh workflow run ProductQC.yml returned code {res.returncode}: {res.stderr}")
        except Exception as ge:
            logger.warning(f"Could not dispatch ProductQC.yml via GitHub CLI: {ge}")

    # 2. Local fallback / direct Python invocation
    try:
        from scripts.run_qc import run_auto_qc
        logger.info(f"Running in-process Auto-QC inspection for row #{row_id}...")
        run_auto_qc(target_row_id=str(row_id))
        return True
    except Exception as qe:
        logger.warning(f"In-process Auto-QC execution error for row #{row_id}: {qe}")
        return False

def run_batch_job(
    from_sheet: bool = True,
    target_id: str = None,
    sample: bool = False,
    quality: str = "qh",
    upload_gdrive: bool = False,
    auto_qc: bool = False,
    gdrive_folder_id: str = TARGET_GDRIVE_FOLDER_ID
):
    """
    Main batch processing function.
    """
    ensure_bell_sound()
    ensure_tick_sound()

    batches_to_process = []
    gsheet_mgr = None
    gdrive_uploader = None

    if upload_gdrive:
        try:
            gdrive_uploader = GDriveUploader(folder_id=gdrive_folder_id)
        except Exception as e:
            logger.warning(f"Could not initialize GDriveUploader: {e}")

    if from_sheet:
        logger.info("Connecting to Google Sheets...")
        gsheet_mgr = GSheetManager()
        if target_id:
            batch = gsheet_mgr.get_batch_by_id(target_id)
            if batch:
                batches_to_process = [batch]
                logger.info(f"Targeted specific batch #{target_id}: '{batch.get('topic')}'")
            else:
                logger.warning(f"Could not find Batch with ID #{target_id} on Google Sheets.")
        else:
            batches_to_process = gsheet_mgr.get_pending_batches()
    elif sample:
        sample_words = [
            {"hanzi": "苹果", "pinyin": "píng guǒ", "hidden_pinyin": "p _ _ _   g _ _", "meaning": "Quả táo"},
            {"hanzi": "米饭", "pinyin": "mǐ fàn", "hidden_pinyin": "m _   f _ _", "meaning": "Cơm"},
            {"hanzi": "面包", "pinyin": "miàn bāo", "hidden_pinyin": "m _ _ _   b _ _", "meaning": "Bánh mì"},
            {"hanzi": "喝水", "pinyin": "hē shuǐ", "hidden_pinyin": "h _   s _ _ _", "meaning": "Uống nước"},
            {"hanzi": "吃饭", "pinyin": "chī fàn", "hidden_pinyin": "c _ _   f _ _", "meaning": "Ăn cơm"}
        ]
        sample_meta = save_and_upload_metadata("sample_hsk12", "HSK 1-2 • ĐOÁN PINYIN", "HSK 1-2", sample_words)
        batches_to_process = [{
            "row_index": 0,
            "id": "sample_hsk12",
            "topic": "HSK 1-2 • ĐOÁN PINYIN",
            "level": "HSK 1-2",
            "words": sample_words,
            "metadata": sample_meta
        }]

    if not batches_to_process:
        logger.info("No batches found to process.")
        return

    logger.info(f"Found {len(batches_to_process)} batches to process.")

    for batch in batches_to_process:
        row_id = batch["id"]
        topic = batch["topic"]
        level = batch.get("level", "HSK 1-2")
        words = batch["words"]
        row_index = batch.get("row_index", 0)

        logger.info("\n" + "=" * 50)
        logger.info(f"Processing Batch ID [{row_id}]: {topic}")
        logger.info(f"Total Words: {len(words)}")
        logger.info(f"Quality: {quality}")
        logger.info("=" * 50)

        # 🛑 PRE-RENDER GATEKEEPER CHECK
        validator = PreRenderValidator()
        is_valid, validation_errors = validator.validate_batch(batch)
        if not is_valid:
            error_str = " | ".join(validation_errors)
            logger.warning(f"🛑 Batch [{row_id}] VI PHẠM NGUYÊN TẮC: {error_str}. Chuyển trạng thái sang 'Failed'.")
            if gsheet_mgr and row_index > 0:
                gsheet_mgr.update_batch_status(row_index, "Failed")
                try:
                    now_str = get_vietnam_now_str()
                    gsheet_mgr.worksheet.update_cell(row_index, 16, f"[Pre-Render Vi Phạm: {error_str[:150]} lúc {now_str} (GMT+7)]")
                except Exception as e:
                    logger.warning(f"Could not update Notes cell: {e}")

            # Send Telegram Alert
            bullets = "\n".join([f"• {e}" for e in validation_errors])
            alert_msg = (
                f"🛑 <b>[Pre-Render Gatekeeper] Dòng #{row_id} Bị Chặn:</b>\n\n"
                f"📌 <b>Chủ đề:</b> <b>{topic}</b> (<code>{level}</code>)\n"
                f"❌ <b>Lý do vi phạm nguyên tắc:</b>\n{bullets}\n\n"
                f"🔄 <b>Trạng thái:</b> <code>Pending ➔ Failed</code> (Đã dừng render, hệ thống sẽ tự động khôi phục chuẩn hóa trong lượt tới)."
            )
            send_telegram_alert_message(alert_msg)
            continue

        if gsheet_mgr and row_index > 0:
            gsheet_mgr.update_batch_status(row_index, "In Progress")

        # 1. Generate scene python file (Includes 0.75s High-CTR Cover at 00:00)
        scene_file, scene_name = create_scene_file(batch)
        logger.info(f"Generated scene: {scene_name} at {scene_file}")

        # 2. Render Video with Manim
        clean_topic_name = sanitize_filename(topic)
        final_video_name = f"#{row_id}.{clean_topic_name}.mp4"
        custom_video_path = os.path.join(config.output_videos_dir, final_video_name)

        success, video_path = render_scene_file(
            scene_file,
            scene_name,
            quality=quality,
            custom_output_name=final_video_name
        )

        if success and video_path:
            logger.info(f"Video rendered successfully: {video_path}")

            gdrive_link = ""
            if gdrive_uploader:
                try:
                    gdrive_link = gdrive_uploader.upload_file(video_path, final_video_name) or ""
                except Exception as ue:
                    logger.error(f"GDrive upload error: {ue}")

            # Ensure metadata exists directly as formatted text in Column J
            metadata_text = batch.get("metadata", "")
            if not metadata_text or metadata_text.startswith("http") or not "=== 1. YOUTUBE SHORTS ===" in metadata_text:
                try:
                    metadata_text = save_and_upload_metadata(
                        batch_id=str(row_id),
                        topic=topic,
                        level=level,
                        words=words
                    )
                except Exception as me:
                    logger.error(f"Metadata generation error: {me}")

            if gsheet_mgr and row_index > 0:
                # Update status to 'Video', Video column to GDrive link, metadata directly into cell
                gsheet_mgr.update_batch_status(
                    row_index=row_index,
                    status="Video",
                    video_link=gdrive_link,
                    metadata_link=metadata_text
                )

            # Send video directly to Telegram bot chat with moderation buttons
            tg_caption = (
                f"🎬 <b>[Kiểm Duyệt Video] #{row_id}: {topic} ({level})</b>\n\n"
                f"📊 <b>Trạng thái hiện tại:</b> <code>Video</code> (Đã lưu GDrive)\n"
                f"🔗 <b>GDrive Video:</b> {gdrive_link or 'Đã lưu local'}\n"
                f"🖼️ <b>Ảnh bìa (Cover):</b> Đã tích hợp 0.75s ở đầu video (Frame 00:00)\n\n"
                f"👇 <i>Vui lòng chọn thao tác kiểm duyệt:</i>\n"
                f"• <b>Approve</b> ➔ Chuyển thành <code>Ready</code> (Đăng tự động lúc 07:00 / 13:00)\n"
                f"• <b>Reset</b> ➔ Chuyển về <code>Pending</code> (Để render lại)\n"
                f"• <b>Delete</b> ➔ Xóa dòng khỏi Sheet"
            )
            send_telegram_video(video_path, tg_caption, row_id=str(row_id), gdrive_link=gdrive_link)
            logger.info(f" Batch [{row_id}] finished successfully -> {video_path}")

            # Automatic trigger to ProductQC if requested
            if auto_qc or os.getenv("TRIGGER_QC", "").lower() in ("true", "1") or os.getenv("AUTO_QC", "").lower() in ("true", "1"):
                trigger_product_qc(row_id=str(row_id), local_video_path=video_path, gdrive_link=gdrive_link)
        else:
            logger.error(f"❌ Failed to render batch [{row_id}]")
            if gsheet_mgr and row_index > 0:
                gsheet_mgr.update_batch_status(row_index, "Failed")
                try:
                    now_str = get_vietnam_now_str()
                    gsheet_mgr.worksheet.update_cell(row_index, 16, f"[Render Thất Bại lúc {now_str} (GMT+7)]")
                except Exception:
                    pass
            # Send Telegram alert on render failure
            fail_msg = (
                f"❌ <b>[Render Thất Bại] #{row_id}: {topic} ({level})</b>\n\n"
                f"📊 <b>Trạng thái:</b> <code>Pending ➔ Failed</code>\n"
                f"⚠️ <b>Nguyên nhân:</b> Lỗi trong quá trình kết xuất Manim / FFmpeg.\n"
                f"🔄 Hệ thống sẽ tự động thử khôi phục trong lượt tới hoặc bạn có thể gõ <code>/render {row_id}</code> để thử lại."
            )
            send_telegram_alert_message(fail_msg)

def main():
    try:
        parser = argparse.ArgumentParser(description="lelehoctiengtrung_pinyin Batch Runner (Pipeline 2.0)")
        parser.add_argument("--from-sheet", action="store_true", help="Fetch batches from Google Sheets")
        parser.add_argument("--sample", action="store_true", help="Run with built-in sample batch")
        parser.add_argument("--row-id", type=str, default=None, help="Process a specific row ID from Sheet")
        parser.add_argument("--quality", type=str, default="qh", choices=["ql", "qm", "qh", "qk"], help="Render quality (default: qh 1080p60)")
        parser.add_argument("--upload-gdrive", action="store_true", help="Upload rendered video to Google Drive")
        parser.add_argument("--auto-qc", "--trigger-qc", dest="auto_qc", action="store_true", help="Automatically trigger ProductQC physical inspection after render")
        parser.add_argument("--gdrive-folder-id", type=str, default=TARGET_GDRIVE_FOLDER_ID, help=f"Target Google Drive Folder ID (default: {TARGET_GDRIVE_FOLDER_ID})")

        args = parser.parse_args()

        if not args.from_sheet and not args.sample and not args.row_id:
            args.from_sheet = True

        run_batch_job(
            from_sheet=args.from_sheet or bool(args.row_id),
            target_id=args.row_id,
            sample=args.sample,
            quality=args.quality,
            upload_gdrive=args.upload_gdrive,
            auto_qc=args.auto_qc,
            gdrive_folder_id=args.gdrive_folder_id
        )
    except Exception as e:
        logger.error(f"🔥 FATAL EXCEPTION in Batch Runner: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

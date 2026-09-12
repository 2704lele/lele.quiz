import os
import sys
import re
import json
import argparse
import logging
from datetime import datetime, timezone, timedelta

def get_vietnam_now_str() -> str:
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
    return re.sub(r'[/\\:*?"<>|]', '_', name).strip()

def send_telegram_alert_message(text: str, reply_markup: dict = None):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip() or "1187577977"

    if not (bot_token and chat_id):
        logger.warning("Telegram alert skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing.")
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
        requests.post(url, json=payload, timeout=20)
    except Exception as e:
        logger.warning(f"Telegram alert error: {e}")

def send_telegram_video(video_path: str, caption: str, reply_markup: dict = None):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip() or "1187577977"

    if not (bot_token and chat_id) or not os.path.exists(video_path):
        return
    try:
        import requests
        url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
        with open(video_path, "rb") as f_vid:
            data = {
                "chat_id": chat_id,
                "caption": caption,
                "parse_mode": "HTML",
                "supports_streaming": True
            }
            if reply_markup:
                data["reply_markup"] = json.dumps(reply_markup)
            requests.post(url, data=data, files={"video": f_vid}, timeout=60)
    except Exception as e:
        logger.warning(f"Telegram video upload error: {e}")

def process_batch(batch_row: dict, gsheet: GSheetManager, uploader: GDriveUploader, quality: str = "qh") -> bool:
    row_num = batch_row.get("_row_number")
    batch_id = batch_row.get("#", f"#{row_num}")
    clean_id = str(batch_id).replace("#", "").strip()
    topic = batch_row.get("Topic", "Từ Vựng Cơ Bản")
    level = batch_row.get("Level", "HSK 1")
    
    logger.info(f"▶️ Processing VocabVN Batch {batch_id} (Row {row_num}): '{topic}' ({level})")

    # 1. Parse words
    words = []
    for col_key in ["Word 1", "Word 2", "Word 3", "Word 4", "Word 5"]:
        raw_val = batch_row.get(col_key, "")
        w = gsheet.parse_word_entry(raw_val)
        if w.get("hanzi"):
            words.append(w)

    # 2. Validate
    batch_dict = {
        "id": clean_id,
        "topic": topic,
        "level": level,
        "words": words
    }
    is_valid, val_errors = PreRenderValidator.validate_batch(batch_dict)
    if not is_valid:
        error_msg = f"❌ Pre-render Validation Failed for Batch {batch_id}:\n" + "\n".join(val_errors)
        logger.error(error_msg)
        gsheet.update_batch_status(row_num, "Error", notes=error_msg[:500])
        send_telegram_alert_message(f"⚠️ <b>[VocabVN Gatekeeper 2 Rejected]</b> Batch {batch_id}:\n{error_msg}")
        return False

    # 3. Create High-CTR Thumbnail
    thumb_path = os.path.join(config.output_thumbnails_dir, f"cover_batch_{clean_id}.jpg")
    create_high_ctr_thumbnail(batch_dict, thumb_path)

    # 4. Generate Scene Code
    scene_name = f"VocabCN_Scene_{clean_id}"
    scene_py_path = os.path.join(config.generated_scenes_dir, f"scene_{clean_id}.py")
    create_scene_file(words, topic, level, scene_py_path, scene_name=scene_name, cover_path=thumb_path)

    # 5. Render Video via Manim
    safe_topic = sanitize_filename(topic)
    video_output_name = f"VocabCN_{clean_id}_{safe_topic}.mp4"
    logger.info(f"Rendering Manim video ({quality}) for Batch {batch_id}...")
    success, local_video_path = render_scene_file(scene_py_path, scene_name, quality=quality, custom_output_name=video_output_name)

    if not success or not os.path.exists(local_video_path):
        gsheet.update_batch_status(row_num, "Error", notes="Manim render execution failed.")
        return False

    # 6. Upload Video & Thumbnail to Google Drive
    logger.info(f"Uploading video {video_output_name} to Google Drive...")
    gdrive_video_link = uploader.upload_file(local_video_path, remote_filename=video_output_name, mime_type="video/mp4")
    
    gdrive_thumb_link = ""
    if os.path.exists(thumb_path):
        gdrive_thumb_link = uploader.upload_file(thumb_path, remote_filename=f"cover_batch_{clean_id}.jpg", mime_type="image/jpeg")

    # 7. Generate & Save Metadata
    save_and_upload_metadata(clean_id, topic, level, words, gsheet_mgr=gsheet, row_number=row_num)

    # 8. Update Sheet Status -> 'Video'
    gsheet.update_batch_status(row_num, "Video", video_link=gdrive_video_link, notes=f"Rendered at {get_vietnam_now_str()}")
    logger.info(f"✅ Finished rendering VocabCN Batch {batch_id} -> GDrive Link: {gdrive_video_link}")

    # 9. Send Telegram Video for Moderation
    caption = (
        f"🎬 <b>[VocabCNquiz Video Mới]</b> Batch <b>#{clean_id}</b>\n"
        f"📌 <b>Chủ đề:</b> {topic} ({level})\n"
        f"🔗 <a href='{gdrive_video_link}'>Xem Video trên Google Drive</a>\n"
        f"📅 <i>Thời gian: {get_vietnam_now_str()}</i>"
    )
    if os.path.exists(local_video_path):
        send_telegram_video(local_video_path, caption)
    else:
        send_telegram_alert_message(caption)
    return True

def main():
    parser = argparse.ArgumentParser(description="Render VocabVNQuiz batches from Google Sheet.")
    parser.add_argument("--quality", choices=["ql", "qm", "qh", "qk"], default="qh", help="Manim quality")
    parser.add_argument("--row_id", default="", help="Specific Row ID to render")
    args = parser.parse_args()

    ensure_bell_sound()
    ensure_tick_sound()

    gsheet = GSheetManager()
    uploader = GDriveUploader()

    if args.row_id:
        target_row = gsheet.get_row_by_id(args.row_id)
        if not target_row:
            logger.error(f"Row #{args.row_id} not found on sheet tab '{config.sheet_tab_name}'!")
            sys.exit(1)
        batches_to_render = [target_row]
    else:
        batches_to_render = gsheet.get_pending_batches()

    if not batches_to_render:
        logger.info("ℹ️ No Pending batches found on Google Sheet. Nothing to render.")
        return

    logger.info(f"Found {len(batches_to_render)} batch(es) to process.")
    for b in batches_to_render:
        process_batch(b, gsheet, uploader, quality=args.quality)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
End-to-End Production Script for 5 VocabCNQuiz Batches (Rows #5..#9).
Handles Gatekeeper 1 validation, Google Sheets insertion, 60fps Manim rendering,
Google Drive upload, Auto-QC inspection, and promotion to Ready.
"""

import os
import sys
import time
import logging
from datetime import datetime, timezone, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import config
from src.gsheet_manager import GSheetManager
from src.pre_render_validator import PreRenderValidator
from src.pinyin_utils import prepare_word_tuple
from src.metadata_generator import generate_social_metadata
from src.scene_generator import create_scene_file
from src.render_engine import render_scene_file
from src.audio_generator import ensure_bell_sound, ensure_tick_sound
from src.thumbnail_generator import create_high_ctr_thumbnail
from src.gdrive_uploader import GDriveUploader
from src.qc_inspector import QCInspector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("VocabCNProducer")

def get_vietnam_now_str() -> str:
    tz_vn = timezone(timedelta(hours=7))
    return datetime.now(tz_vn).strftime("%Y-%m-%d %H:%M:%S")

BATCHES_DATA = [
    {
        "row_id": 5,
        "topic": "Màu Sắc Cơ Bản",
        "level": "HSK 1",
        "raw_words": [
            {"hanzi": "红色", "pinyin": "hóng sè", "meaning": "Màu đỏ"},
            {"hanzi": "黄色", "pinyin": "huáng sè", "meaning": "Màu vàng"},
            {"hanzi": "蓝色", "pinyin": "lán sè", "meaning": "Màu xanh lam"},
            {"hanzi": "绿色", "pinyin": "lǜ sè", "meaning": "Màu xanh lá"},
            {"hanzi": "黑色", "pinyin": "hēi sè", "meaning": "Màu đen"},
        ]
    },
    {
        "row_id": 6,
        "topic": "Phương Tiện Giao Thông",
        "level": "HSK 2",
        "raw_words": [
            {"hanzi": "飞机", "pinyin": "fēi jī", "meaning": "Máy bay"},
            {"hanzi": "出租车", "pinyin": "chū zū chē", "meaning": "Xe tắc xi"},
            {"hanzi": "公共汽车", "pinyin": "gōng gòng qì chē", "meaning": "Xe buýt"},
            {"hanzi": "火车站", "pinyin": "huǒ chē zhàn", "meaning": "Ga tàu hỏa"},
            {"hanzi": "自行车", "pinyin": "zì xíng chē", "meaning": "Xe đạp"},
        ]
    },
    {
        "row_id": 7,
        "topic": "Thương Lượng Đàm Phán",
        "level": "HSK 3",
        "raw_words": [
            {"hanzi": "商量", "pinyin": "shāng liang", "meaning": "Thương lượng"},
            {"hanzi": "同意", "pinyin": "tóng yì", "meaning": "Đồng ý"},
            {"hanzi": "拒绝", "pinyin": "jù jué", "meaning": "Cự tuyệt"},
            {"hanzi": "考虑", "pinyin": "kǎo lǜ", "meaning": "Cân nhắc"},
            {"hanzi": "解释", "pinyin": "jiě shì", "meaning": "Giải thích"},
        ]
    },
    {
        "row_id": 8,
        "topic": "Cảm Xúc Thường Ngày",
        "level": "HSK 2",
        "raw_words": [
            {"hanzi": "快乐", "pinyin": "kuài lè", "meaning": "Vui vẻ"},
            {"hanzi": "难过", "pinyin": "nán guò", "meaning": "Buồn bã"},
            {"hanzi": "着急", "pinyin": "zháo jí", "meaning": "Lo lắng"},
            {"hanzi": "聪明", "pinyin": "cōng míng", "meaning": "Thông minh"},
            {"hanzi": "热情", "pinyin": "rè qíng", "meaning": "Nhiệt tình"},
        ]
    },
    {
        "row_id": 9,
        "topic": "Môi Trường Công Sở",
        "level": "HSK 3",
        "raw_words": [
            {"hanzi": "同事", "pinyin": "tóng shì", "meaning": "Đồng nghiệp"},
            {"hanzi": "会议", "pinyin": "huì yì", "meaning": "Hội nghị"},
            {"hanzi": "经理", "pinyin": "jīng lǐ", "meaning": "Giám đốc"},
            {"hanzi": "请假", "pinyin": "qǐng jià", "meaning": "Xin nghỉ"},
            {"hanzi": "加班", "pinyin": "jiā bān", "meaning": "Tăng ca"},
        ]
    }
]

def main():
    logger.info("=== Starting VocabCN 5-Batch Production Pipeline ===")

    # 0. Ensure assets
    ensure_bell_sound()
    ensure_tick_sound()

    gsheet = GSheetManager()
    uploader = GDriveUploader()
    inspector = QCInspector()

    raw_history = PreRenderValidator.fetch_vocabcn_history(gsheet_mgr=gsheet)
    past_batches_baseline = [b for b in raw_history.get("past_batches", []) if b.get("id", "").isdigit() and int(b.get("id")) < 5]
    recent_topics_baseline = [b.get("topic") for b in past_batches_baseline if b.get("topic")]
    history = {
        "recent_topics": list(recent_topics_baseline),
        "past_batches": list(past_batches_baseline)
    }
    logger.info(f"Loaded baseline history (Rows < 5): {len(history['recent_topics'])} topics, {len(history['past_batches'])} batches.")

    # 1. Gatekeeper 1 Validation & Formatting
    prepared_batches = []
    for item in BATCHES_DATA:
        row_id = item["row_id"]
        topic = item["topic"]
        level = item["level"]
        raw_words = item["raw_words"]

        batch_dict = {
            "id": str(row_id),
            "topic": topic,
            "level": level,
            "words": raw_words
        }

        is_valid, errors = PreRenderValidator.validate_batch(batch_dict, history=history)
        if not is_valid:
            logger.error(f"❌ Gatekeeper 1 validation failed for Batch #{row_id}: {errors}")
            sys.exit(1)

        logger.info(f"✅ Gatekeeper 1 passed for Batch #{row_id}: '{topic}' ({level})")

        # Add to history container so subsequent batches don't overlap
        history["recent_topics"].append(topic)
        history["past_batches"].append({
            "id": str(row_id),
            "topic": topic,
            "level": level,
            "words": [w["hanzi"].strip() for w in raw_words]
        })

        # Prepare 4-part word strings
        formatted_words = []
        words_for_meta = []
        sheet_word_cols = []
        for w in raw_words:
            hz = w["hanzi"].strip()
            py = w["pinyin"].strip()
            mean = w["meaning"].strip()
            h, fp, hp = prepare_word_tuple(hz, py)
            formatted_words.append({
                "hanzi": h,
                "pinyin": fp,
                "hidden_pinyin": hp,
                "meaning": mean
            })
            words_for_meta.append({"hanzi": h, "pinyin": fp, "meaning": mean})
            sheet_word_cols.append(f"{h} | {fp} | {hp} | {mean}")

        # Social metadata
        meta_dict = generate_social_metadata(topic, level, words_for_meta)
        meta_text = meta_dict["sheet_cell_text"]

        # Save local metadata files
        meta_dir = os.path.join(config.base_dir, "output", "metadata")
        os.makedirs(meta_dir, exist_ok=True)
        with open(os.path.join(meta_dir, f"metadata_batch_{row_id}_{topic}.txt"), "w", encoding="utf-8") as f:
            f.write(meta_text)

        prepared_batches.append({
            "row_id": row_id,
            "topic": topic,
            "level": level,
            "formatted_words": formatted_words,
            "sheet_word_cols": sheet_word_cols,
            "metadata_text": meta_text,
            "batch_dict": {
                "id": str(row_id),
                "topic": topic,
                "level": level,
                "words": formatted_words
            }
        })

    # 2. Write batches to Google Sheet tab vocabCN as Pending
    logger.info("Writing 5 batches to Google Sheets tab vocabCN (Rows #5..#9)...")
    for b in prepared_batches:
        row_id = b["row_id"]
        batch_dict_for_sheet = {
            "topic": b["topic"],
            "level": b["level"],
            "status": "Pending",
            "word_1": b["sheet_word_cols"][0],
            "word_2": b["sheet_word_cols"][1],
            "word_3": b["sheet_word_cols"][2],
            "word_4": b["sheet_word_cols"][3],
            "word_5": b["sheet_word_cols"][4],
            "metadata": b["metadata_text"],
            "created_at": get_vietnam_now_str(),
            "notes": f"Khởi tạo tự động lúc {get_vietnam_now_str()}"
        }
        gsheet.append_or_insert_batch(batch_dict_for_sheet, target_row=row_id)
        logger.info(f"Wrote Row #{row_id} on Google Sheet tab '{gsheet.tab_name}'.")

    # 3. Render Manim 60fps Videos & Upload to Google Drive
    for b in prepared_batches:
        row_id = b["row_id"]
        topic = b["topic"]
        level = b["level"]
        words = b["formatted_words"]
        clean_id = str(row_id)

        logger.info(f"\n▶️ Rendering Batch #{row_id}: '{topic}' ({level})...")

        # 3.1 Create High-CTR Thumbnail
        os.makedirs(config.output_thumbnails_dir, exist_ok=True)
        thumb_path = os.path.join(config.output_thumbnails_dir, f"cover_batch_{clean_id}.jpg")
        create_high_ctr_thumbnail(b["batch_dict"], thumb_path)
        logger.info(f"Created High-CTR thumbnail: {thumb_path}")

        # 3.2 Create Scene File
        os.makedirs(config.generated_scenes_dir, exist_ok=True)
        scene_name = f"VocabCN_Scene_{clean_id}"
        scene_py_path = os.path.join(config.generated_scenes_dir, f"scene_{clean_id}.py")
        create_scene_file(words, topic, level, scene_py_path, scene_name=scene_name, cover_path=thumb_path)
        logger.info(f"Created Scene Python script: {scene_py_path}")

        # 3.3 Render Scene via Manim (-qh)
        video_filename = f"VocabCN_{clean_id}_{topic.replace(' ', '_')}.mp4"
        success, local_video_path = render_scene_file(scene_py_path, scene_name, quality="qh", custom_output_name=video_filename)

        if not success or not os.path.exists(local_video_path):
            logger.error(f"❌ Failed to render video for Batch #{row_id}!")
            gsheet.update_batch_status(row_id, "Error", notes="Manim render execution failed.")
            sys.exit(1)

        logger.info(f"✅ Manim render successful: {local_video_path} ({os.path.getsize(local_video_path)/(1024*1024):.2f} MB)")

        # 3.4 Upload Video to Google Drive
        logger.info(f"Uploading {video_filename} to Google Drive...")
        gdrive_video_link = uploader.upload_file(local_video_path, remote_filename=video_filename, mime_type="video/mp4")
        logger.info(f"✅ Uploaded to Drive: {gdrive_video_link}")

        # Upload Thumbnail
        if os.path.exists(thumb_path):
            uploader.upload_file(thumb_path, remote_filename=f"cover_batch_{clean_id}.jpg", mime_type="image/jpeg")

        # Update Sheet to 'Video'
        now_time = get_vietnam_now_str()
        gsheet.update_batch_status(row_id, "Video", video_link=gdrive_video_link, notes=f"Rendered at {now_time}")
        b["local_video_path"] = local_video_path
        b["gdrive_video_link"] = gdrive_video_link

    # 4. Auto-QC Inspector (Gatekeeper 2) & Promotion to 'Ready'
    logger.info("\n=== Running Gatekeeper 2 Auto-QC on all rendered batches ===")
    for b in prepared_batches:
        row_id = b["row_id"]
        topic = b["topic"]
        level = b["level"]
        local_video = b["local_video_path"]

        batch_qc_input = {
            "id": str(row_id),
            "topic": topic,
            "level": level,
            "words": b["formatted_words"]
        }

        qc_result = inspector.inspect_batch(batch_qc_input, local_video)
        logger.info(f"QC Result for Batch #{row_id} ({topic}): passed={qc_result['passed']}")
        logger.info(f"  Details: {qc_result['details']}")
        if not qc_result["passed"]:
            logger.error(f"❌ QC Errors for Batch #{row_id}: {qc_result['errors']}")
            sys.exit(1)

        # Promote to 'Ready' on Google Sheet
        now_str = get_vietnam_now_str()
        gsheet.worksheet.update_cell(row_id, 4, "Ready")
        gsheet.worksheet.update_cell(row_id, 16, f"[Auto-QC Passed lúc {now_str} (GMT+7)]")
        logger.info(f"✨ Promoted Row #{row_id} to 'Ready' on Google Sheet tab '{gsheet.tab_name}'.")

    logger.info("\n🎉 All 5 batches successfully ideated, rendered, QC-passed, and promoted to Ready!")

if __name__ == "__main__":
    main()

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

import site
import glob
for p in [site.getusersitepackages()] + site.getsitepackages():
    if p and p not in sys.path and os.path.exists(p):
        sys.path.insert(0, p)
for p in glob.glob("/usr/local/lib/python*/dist-packages") + glob.glob("/root/.local/lib/python*/site-packages"):
    if p not in sys.path and os.path.exists(p):
        sys.path.insert(0, p)

from src.config import config
from src.gsheet_manager import GSheetManager
from src.scene_generator import create_scene_file
from src.render_engine import render_scene_file
from src.audio_generator import ensure_all_sound_effects
from src.gdrive_uploader import GDriveUploader
from src.metadata_generator import save_and_upload_metadata
from src.pre_render_validator import PreRenderValidator
from src.thumbnail_generator import generate_multilevels_thumbnail

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("MultilevelsBatchRunner")

def sanitize_filename(name: str) -> str:
    return re.sub(r'[/\\:*?"<>|]', '_', name).strip()

def run_multilevels_batch(batch_id: str, quality: str = "qh", force: bool = False, notify_tg: bool = True):
    clean_id = str(batch_id).replace("#", "").strip()
    logger.info(f"=== Starting Multilevels Batch Runner for Row #{clean_id} (Quality: {quality}) ===")

    mgr = GSheetManager()
    batch_info = mgr.get_batch_by_id(clean_id)
    if not batch_info:
        logger.error(f"Batch #{clean_id} not found on Google Sheet tab '{mgr.tab_name}'!")
        sys.exit(1)

    row_index = batch_info["row_index"]
    topic = batch_info["topic"]
    levels = batch_info["levels"]

    concept_name = topic.replace("1 Nghĩa 5 Cấp •", "").replace("1 Nghĩa - 5 Cấp Độ •", "").strip()

    logger.info(f"Batch #{clean_id} found at Sheet Row {row_index}: Topic='{topic}', Levels={len(levels)}")

    # 1. Update Status to Rendering
    mgr.update_batch_status(row_index, "Rendering")

    # 2. Generate Cover Thumbnail
    safe_topic = sanitize_filename(concept_name)
    cover_path = os.path.join(config.output_thumbnails_dir, f"cover_batch_{clean_id}_{safe_topic}.jpg")
    try:
        generate_multilevels_thumbnail(clean_id, concept_name, levels, output_path=cover_path)
    except Exception as te:
        logger.warning(f"Could not generate cover thumbnail: {te}")
        cover_path = ""

    # 3. Create Scene Script
    scene_file_path = os.path.join(config.generated_scenes_dir, f"scene_batch_{clean_id}.py")
    scene_name = f"MultilevelsQuizScene_{clean_id}"
    create_scene_file(
        levels=levels,
        concept_name=concept_name,
        hook_title=f"5 CẤP ĐỘ '{concept_name.upper()}' TRONG TIẾNG TRUNG",
        output_py_path=scene_file_path,
        scene_name=scene_name,
        cover_path=cover_path
    )

    # 4. Render Video via Manim Engine
    output_filename = f"multilevels_batch_{clean_id}_{safe_topic}.mp4"
    render_ok, video_path = render_scene_file(
        scene_file=scene_file_path,
        scene_name=scene_name,
        quality=quality,
        custom_output_name=output_filename
    )

    if not render_ok or not os.path.exists(video_path):
        mgr.update_batch_status(row_index, "Failed", notes="Manim render failed")
        logger.error(f"Render failed for Batch #{clean_id}")
        sys.exit(1)

    # 5. Upload Video to Google Drive
    uploader = GDriveUploader()
    gdrive_link = uploader.upload_file(video_path, filename=output_filename, subfolder_name="multilevelsquiz")

    # 6. Save Metadata & Update Google Sheet to 'Video'
    now_vn = get_vietnam_now_str()
    save_and_upload_metadata(
        batch_id=clean_id,
        concept_name_vi=concept_name,
        levels=levels,
        gsheet_mgr=mgr,
        row_number=row_index
    )

    mgr.update_batch_status(
        row_number=row_index,
        status="Video",
        video_link=gdrive_link,
        notes=f"Render hoàn tất lúc {now_vn} (GMT+7)"
    )

    logger.info(f"✅ Multilevels Batch #{clean_id} rendered and uploaded successfully! Link: {gdrive_link}")

def main():
    parser = argparse.ArgumentParser(description="MultilevelsQuiz Batch Runner (30s Manim Video)")
    parser.add_argument("--id", type=str, required=True, help="Target Row ID (e.g. 2, 3, #2)")
    parser.add_argument("--quality", type=str, default="qh", choices=["ql", "qm", "qh", "qk"], help="Manim render quality (default: qh 1080x1920)")
    parser.add_argument("--force", action="store_true", help="Force re-render even if already done")

    args = parser.parse_args()
    run_multilevels_batch(batch_id=args.id, quality=args.quality, force=args.force)

if __name__ == "__main__":
    main()

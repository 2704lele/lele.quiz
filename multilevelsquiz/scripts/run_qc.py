import os
import sys
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

from src.gsheet_manager import GSheetManager
from src.config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("QCInspectorRunner")

def run_qc_for_batch(batch_id: str):
    clean_id = str(batch_id).replace("#", "").strip()
    logger.info(f"=== Running QC for Multilevels Batch #{clean_id} ===")

    mgr = GSheetManager()
    batch_info = mgr.get_batch_by_id(clean_id)
    if not batch_info:
        logger.error(f"Batch #{clean_id} not found on Google Sheet tab '{mgr.tab_name}'!")
        sys.exit(1)

    row_index = batch_info["row_index"]
    video_url = batch_info["video_url"]

    # Check local video file in output/videos
    videos = []
    if os.path.exists(config.output_videos_dir):
        videos = [os.path.join(config.output_videos_dir, f) for f in os.listdir(config.output_videos_dir) if f.startswith(f"multilevels_batch_{clean_id}_") and f.endswith(".mp4")]

    if not videos:
        logger.warning(f"No local video found for Batch #{clean_id} in {config.output_videos_dir}. Verifying GDrive link: {video_url}")
        if not video_url or "drive.google.com" not in video_url:
            logger.error("No valid Google Drive URL found for QC.")
            sys.exit(1)
        
        import re
        try:
            from src.gdrive_uploader import GDriveUploader
            uploader = GDriveUploader()
            match = re.search(r'/d/([a-zA-Z0-9_-]+)', video_url) or re.search(r'id=([a-zA-Z0-9_-]+)', video_url)
            file_id = match.group(1) if match else None
            if not file_id:
                raise ValueError(f"Could not parse file ID from {video_url}")
            file_meta = uploader.service.files().get(fileId=file_id, fields="id, name, size, mimeType, trashed", supportsAllDrives=True).execute()
            if file_meta.get("trashed"):
                raise ValueError("File is in trash")
            file_size = int(file_meta.get("size", 0))
            if file_size < 100000:
                raise ValueError(f"File too small ({file_size} bytes)")
            logger.info(f"✓ Real Google Drive file verified: {file_meta.get('name')} ({file_size / (1024*1024):.2f} MB)")
        except Exception as ge:
            logger.error(f"❌ Real Google Drive verification failed for {video_url}: {ge}")
            mgr.update_batch_status(row_index, "Failed", notes=f"[QC Failed: GDrive file not found or inaccessible: {ge}]")
            sys.exit(1)

        now_vn = get_vietnam_now_str()
        mgr.update_batch_status(row_index, "Ready", notes=f"[Auto-QC Verified Real GDrive Link lúc {now_vn}]")
        logger.info(f"✅ Batch #{clean_id} status updated to 'Ready'")
        return

    from src.qc_inspector import inspect_video_file
    local_video = videos[0]
    report = inspect_video_file(local_video, expected_duration=30.0)
    now_vn = get_vietnam_now_str()

    if report["passed"]:
        mgr.update_batch_status(row_index, "Ready", notes=f"[Auto-QC Passed lúc {now_vn} (GMT+7)]")
        logger.info(f"✅ QC Passed for Batch #{clean_id}! Status set to 'Ready'.")
    else:
        err_str = "; ".join(report["errors"])
        mgr.update_batch_status(row_index, "Failed", notes=f"[QC Failed: {err_str}]")
        logger.error(f"❌ QC Failed for Batch #{clean_id}: {err_str}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="MultilevelsQuiz QC Inspector Runner")
    parser.add_argument("--id", type=str, required=True, help="Target Row ID (e.g. 2, #2)")
    args = parser.parse_args()
    run_qc_for_batch(args.id)

if __name__ == "__main__":
    main()

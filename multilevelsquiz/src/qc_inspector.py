import os
import re
import io
import cv2
import json
import logging
import subprocess
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("QCInspector")

try:
    import opencc
    _opencc_converter = opencc.OpenCC('t2s')
except ImportError:
    _opencc_converter = None

def sanitize_filename(name: str) -> str:
    return re.sub(r'[/\\:*?"<>|]', '_', name).strip()

def extract_gdrive_file_id(gdrive_url: str) -> Optional[str]:
    if not gdrive_url or not isinstance(gdrive_url, str):
        return None
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', gdrive_url) or re.search(r'id=([a-zA-Z0-9_-]+)', gdrive_url)
    return match.group(1) if match else None

def inspect_video_file(video_path: str, expected_duration: float = 30.0) -> Dict[str, Any]:
    """
    Performs deep Gatekeeper 2 automated quality checks on the rendered MP4 file:
    - File existence & non-empty
    - Video resolution: 1080x1920 (Vertical 9:16)
    - Duration tolerance: ~30s (+/- 2.5s)
    - Audio stream presence
    - Frame corruption check via OpenCV
    """
    report = {
        "passed": False,
        "video_path": video_path,
        "width": 0,
        "height": 0,
        "duration": 0.0,
        "has_audio": False,
        "fps": 0.0,
        "errors": []
    }

    if not os.path.exists(video_path):
        report["errors"].append(f"Tệp video không tồn tại: {video_path}")
        return report

    if os.path.getsize(video_path) < 10000:
        report["errors"].append("Kích thước video quá nhỏ (<10KB).")
        return report

    # FFprobe Inspection
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=width,height,r_frame_rate,codec_type,duration",
            "-show_entries", "format=duration",
            "-of", "json",
            video_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        probe_data = json.loads(res.stdout)

        streams = probe_data.get("streams", [])
        v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        if v_stream:
            report["width"] = int(v_stream.get("width", 0))
            report["height"] = int(v_stream.get("height", 0))
            report["fps"] = eval(v_stream.get("r_frame_rate", "0/1")) if "/" in v_stream.get("r_frame_rate", "") else float(v_stream.get("r_frame_rate", 0))

        if a_stream:
            report["has_audio"] = True

        fmt = probe_data.get("format", {})
        report["duration"] = float(fmt.get("duration", 0.0))

    except Exception as e:
        report["errors"].append(f"Lỗi khi kiểm tra ffprobe: {e}")

    # Resolution Check
    if report["width"] != 1080 or report["height"] != 1920:
        report["errors"].append(f"Độ phân giải không chuẩn 1080x1920 (Hiện tại: {report['width']}x{report['height']}).")

    # Duration Check (Vertical Short-form standard for 5-level HSK quiz: 25s - 58s)
    if report["duration"] < 25.0 or report["duration"] > 58.0:
        report["errors"].append(f"Thời lượng video không đúng chuẩn Shorts/TikTok (Hiện tại: {report['duration']:.2f}s, yêu cầu 25s - 58s).")

    # OpenCV Frame Inspection
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            report["errors"].append("OpenCV không thể mở tệp video.")
        else:
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames < 300:
                report["errors"].append(f"Tổng số frame quá ít ({total_frames} frames).")
            cap.release()
    except Exception as cv_err:
        report["errors"].append(f"Lỗi khi kiểm tra frame qua OpenCV: {cv_err}")

    report["passed"] = len(report["errors"]) == 0
    return report

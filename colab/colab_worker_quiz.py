#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Colab Remote Quiz Worker for LeLe Chinese Automation.
Executes Manim video rendering (1080x1920 60fps), Edge-TTS synthesis, Google Drive upload,
and Gatekeeper 2 automated physical QC directly inside Google Colab VM (with GPU T4/L4 or CPU).
Supports continuous processing across all 4 quiz tabs (pinyinquiz, vocabCNquiz, vocabVNquiz, multilevelsquiz).
"""

import os
import sys
import time
import json
import shutil
import argparse
import subprocess
import glob
from pathlib import Path
from typing import List, Optional

DEFAULT_REPO = ""
DEFAULT_DRIVE_FOLDER = "1Y240J5-oXA-UDm2IKvp7qCBVsRempbCB"
DEFAULT_CHAT_ID = "1187577977"

ALL_PIPELINES = ["pinyinquiz", "vocabCNquiz", "vocabVNquiz", "multilevelsquiz"]

PIPELINE_MAP = {
    "pinyin": "pinyinquiz",
    "pinyinquiz": "pinyinquiz",
    "vocabcn": "vocabCNquiz",
    "vocabcnquiz": "vocabCNquiz",
    "vocabvn": "vocabVNquiz",
    "vocabvnquiz": "vocabVNquiz",
    "multilevels": "multilevelsquiz",
    "multilevelsquiz": "multilevelsquiz",
    "ml": "multilevelsquiz",
    "all": "all",
    "all_pending": "all",
    "all_tabs": "all"
}


def log(msg: str):
    t_str = time.strftime("%H:%M:%S")
    print(f"[{t_str}] [ColabWorker] {msg}", flush=True)


def find_uploaded_file(filename: str) -> Optional[Path]:
    """Finds uploaded file regardless of whether placed at vault, cwd, /, or /content/."""
    candidates = [
        Path.home() / ".cloud-profiles" / "lelehoctiengtrung" / "google_sa" / filename,
        Path.home() / ".cloud-profiles" / "lelehoctiengtrung" / "google_oauth" / filename,
        Path.home() / ".cloud-profiles" / "lelehoctiengtrung" / "gemini" / filename,
        Path.home() / ".cloud-profiles" / "lelehoctiengtrung" / "buffer" / filename,
        Path(__file__).resolve().parent.parent / filename,
        Path(f"/{filename}"),
        Path(f"/content/{filename}"),
        Path(filename),
        Path(f"/content/content/{filename}")
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c

    for search_dir in [Path("/content"), Path("/")]:
        if search_dir.exists():
            matches = list(search_dir.glob(filename))
            if matches:
                return matches[0]
    return None


def parse_row_ids(row_str: str) -> List[str]:
    """Parses row string like '19', '19-22', '19,20,21,22', '#19' into list of clean IDs."""
    if not row_str:
        return []
    cleaned = str(row_str).replace("#", "").strip()
    if not cleaned:
        return []

    # Handle range e.g. 19-22
    if "-" in cleaned and "," not in cleaned:
        parts = cleaned.split("-")
        if len(parts) == 2 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
            start, end = int(parts[0].strip()), int(parts[1].strip())
            return [str(i) for i in range(start, end + 1)]

    # Handle comma-separated list
    tokens = [t.strip() for t in cleaned.split(",") if t.strip()]
    res = []
    for t in tokens:
        if "-" in t:
            parts = t.split("-")
            if len(parts) == 2 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
                res.extend(str(i) for i in range(int(parts[0].strip()), int(parts[1].strip()) + 1))
            else:
                res.append(t)
        else:
            res.append(t)
    return res


def ensure_system_dependencies():
    """Install system packages: ffmpeg, pango, cairo for Manim."""
    log("Checking system development dependencies (pkg-config, cairo, pango, ffmpeg)...")
    dev_ok = False
    try:
        res = subprocess.run(["pkg-config", "--exists", "cairo", "pango"], capture_output=True)
        if res.returncode == 0:
            dev_ok = True
    except Exception:
        dev_ok = False

    if not dev_ok:
        log("📦 Installing required C libraries via apt: ffmpeg, pkg-config, libpango1.0-dev, libcairo2-dev...")
        subprocess.run(["sudo", "apt-get", "update", "-qq"], check=False)
        subprocess.run(
            ["sudo", "apt-get", "install", "-y", "-qq", "ffmpeg", "pkg-config", "libpango1.0-dev", "libcairo2-dev", "fonts-noto-cjk"],
            check=False
        )
        log("✓ C development dependencies installed.")
    else:
        log("✓ Cairo and Pango C development headers already satisfied.")


def ensure_python_dependencies():
    """Ensure required Python packages are installed in Colab VM without breaking pre-installed packages."""
    log("Verifying Python packages...")
    log(f"Current Python: {sys.executable} (Version: {sys.version.splitlines()[0]})")

    packages_map = {
        "manim": "manim",
        "pypinyin": "pypinyin",
        "edge_tts": "edge-tts",
        "cv2": "opencv-python-headless",
        "opencc": "opencc-python-reimplemented",
        "pydub": "pydub",
        "gspread": "gspread"
    }

    needed = []
    for mod, pkg in packages_map.items():
        try:
            __import__(mod)
        except ImportError:
            needed.append(pkg)

    if needed:
        log(f"📦 Installing {len(needed)} missing Python packages: {needed}...")
        for pkg in needed:
            log(f"Installing '{pkg}'...")
            cmd = [sys.executable, "-m", "pip", "install", "--break-system-packages", pkg]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if res.returncode != 0:
                cmd2 = ["pip3", "install", "--break-system-packages", pkg]
                res = subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if res.returncode == 0:
                log(f"  ✓ '{pkg}' installed.")
            else:
                log(f"  ⚠️ Warning: '{pkg}' install returned code {res.returncode}")
                if res.stdout:
                    for line in res.stdout.splitlines()[-4:]:
                        log(f"     {line}")

        # Dynamic sys.path refresh
        import site
        for p in [site.getusersitepackages()] + site.getsitepackages():
            if p and p not in sys.path and os.path.exists(p):
                sys.path.insert(0, p)
        for p in glob.glob("/usr/local/lib/python*/dist-packages") + glob.glob("/root/.local/lib/python*/site-packages"):
            if p not in sys.path and os.path.exists(p):
                sys.path.insert(0, p)

        # Verification check
        for mod in packages_map.keys():
            try:
                __import__(mod)
                log(f"✓ Module '{mod}' verified ready.")
            except ImportError as ie:
                log(f"⚠️ Warning: module '{mod}' import failed: {ie}")

        log("✓ Python dependencies installation finished.")
    else:
        log("✓ Python dependencies already satisfied.")


def setup_hardware() -> str:
    """Detect and log hardware accelerator (GPU or CPU)."""
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            log(f"⚡ GPU Accelerator Active: {name}")
            return "cuda"
        else:
            log("⚡ Running on High-Speed CPU VM (Automatic Fallback Active)")
            return "cpu"
    except Exception:
        log("⚡ Hardware: Standard CPU VM")
        return "cpu"


def setup_repo_and_fonts(repo_url: str = "") -> Path:
    """Ensure codebase is extracted from uploaded bundle or cloned."""
    local_root = Path(__file__).resolve().parent.parent
    if (local_root / "pinyinquiz").exists():
        quiz_dir = local_root
    else:
        base_dir = Path("/content")
        quiz_dir = base_dir / "quiz"
        quiz_dir.mkdir(parents=True, exist_ok=True)

        bundle_file = find_uploaded_file("quiz_bundle.tar.gz")

        if bundle_file:
            log(f"📦 Extracting codebase bundle from {bundle_file} into {quiz_dir}...")
            subprocess.run(["tar", "-xzf", str(bundle_file), "-C", str(quiz_dir)], check=True)
            log("✓ Codebase bundle extracted successfully.")
        else:
            log("⚠️ No quiz_bundle.tar.gz found! Checking git clone...")
            repo_dir = base_dir / "lele2vid"
            if not repo_dir.exists() and repo_url:
                try:
                    log(f"📥 Cloning repository from {repo_url}...")
                    subprocess.run(["git", "clone", "--depth", "1", repo_url, str(repo_dir)], check=True)
                    quiz_dir = repo_dir / "quiz"
                    log("✓ Repository cloned.")
                except Exception as ge:
                    log(f"⚠️ Git clone failed: {ge}")
            elif repo_dir.exists():
                quiz_dir = repo_dir / "quiz"

    fonts_dir = Path.home() / ".fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    for sub in ALL_PIPELINES:
        sub_fonts = quiz_dir / sub / "assets" / "fonts"
        if sub_fonts.exists():
            for f in sub_fonts.glob("*.*"):
                dest = fonts_dir / f.name
                if not dest.exists():
                    shutil.copy2(f, dest)

    noto_cand = fonts_dir / "NotoSansSC.ttf"
    if not noto_cand.exists() and (quiz_dir / "pinyinquiz" / "assets" / "fonts" / "NotoSansSC.ttf").exists():
        noto_cand = quiz_dir / "pinyinquiz" / "assets" / "fonts" / "NotoSansSC.ttf"
    if noto_cand.exists():
        for sub in ALL_PIPELINES:
            target_fonts = quiz_dir / sub / "assets" / "fonts"
            target_fonts.mkdir(parents=True, exist_ok=True)
            for fname in ["NotoSansSC.ttf", "NotoSansSC-Bold.otf"]:
                tf = target_fonts / fname
                if not tf.exists():
                    try:
                        shutil.copy2(noto_cand, tf)
                    except Exception:
                        pass
    subprocess.run(["fc-cache", "-f"], check=False, stdout=subprocess.DEVNULL)
    log("✓ CJK fonts registered with fontconfig.")

    return quiz_dir


def setup_credentials(quiz_dir: Path):
    """Setup GCP Service Account and OAuth credentials across all pipelines."""
    # 1. Service Account
    sa_source = find_uploaded_file("service_account.json")
    if sa_source:
        log(f"🔑 Configuring GCP Service Account credentials from {sa_source}...")
        for sub in ALL_PIPELINES:
            configs_dir = quiz_dir / sub / "configs"
            configs_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sa_source, configs_dir / "service_account.json")
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(sa_source)
        log("✓ Service account credentials installed in all pipelines.")
    else:
        log("ℹ️ No service_account.json found on Colab VM.")

    # 2. OAuth Credentials for Google Drive Upload
    oauth_source = find_uploaded_file("oauth_credentials.json") or find_uploaded_file("user_oauth2.json")
    if oauth_source:
        log(f"🔑 Configuring Google OAuth 2.0 credentials from {oauth_source}...")
        try:
            with open(oauth_source, "r", encoding="utf-8") as f:
                oauth_data = json.load(f)
            if oauth_data.get("client_id"):
                os.environ["GDRIVE_CLIENT_ID"] = oauth_data["client_id"]
            if oauth_data.get("client_secret"):
                os.environ["GDRIVE_CLIENT_SECRET"] = oauth_data["client_secret"]
            if oauth_data.get("refresh_token"):
                os.environ["GDRIVE_REFRESH_TOKEN"] = oauth_data["refresh_token"]

            for sub in ALL_PIPELINES:
                configs_dir = quiz_dir / sub / "configs"
                configs_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(oauth_source, configs_dir / "oauth_credentials.json")
            log("✓ Google OAuth 2.0 installed in all pipelines.")
        except Exception as e:
            log(f"⚠️ Failed reading oauth credentials: {e}")
    else:
        log("ℹ️ No oauth_credentials.json found on Colab VM.")


def execute_pipeline(
    quiz_dir: Path,
    target_sub: str,
    action: str,
    quality: str,
    row_id: str,
    drive_folder: str,
    telegram_token: str,
    telegram_chat_id: str
) -> bool:
    """Executes render and QC for a specific pipeline with accurate CLI argument mapping and live streaming."""
    sub_dir = quiz_dir / target_sub
    if not sub_dir.exists() and (quiz_dir / "quiz" / target_sub).exists():
        sub_dir = quiz_dir / "quiz" / target_sub
    if not sub_dir.exists() and (Path("/content") / target_sub).exists():
        sub_dir = Path("/content") / target_sub

    if not sub_dir.exists():
        log(f"❌ Pipeline directory not found: {sub_dir} (Checked {quiz_dir})")
        return False

    env = os.environ.copy()
    child_pythonpath = [str(sub_dir)] + [p for p in sys.path if p and os.path.exists(p)]
    env["PYTHONPATH"] = ":".join(child_pythonpath)

    tab_folder_map = {
        "pinyinquiz": "1f2mFUgpz_pYn3y9HqeHyOG9DzPMVH9QY",
        "vocabCNquiz": "1eI7I4jQqGBjD7MC_NXJ4zwFANxrcZM1E",
        "vocabVNquiz": "1VPqs9h4LLmmmXWKDGWoAz1fUCylVLK2H",
        "multilevelsquiz": "17xOkiW-XOWRDK2CCwNEl_rlf1rGKqKXm"
    }
    effective_folder = tab_folder_map.get(target_sub, drive_folder)
    map_candidates = [quiz_dir / "gdrive_folder_map.json", find_uploaded_file("gdrive_folder_map.json")]
    for mc in map_candidates:
        if mc and mc.exists():
            try:
                with open(mc, "r", encoding="utf-8") as mf:
                    mdata = json.load(mf)
                    for tinfo in mdata.get("tabs", {}).values():
                        if tinfo.get("pipeline") == target_sub and tinfo.get("target_folder_id"):
                            effective_folder = tinfo["target_folder_id"]
                            break
            except Exception:
                pass
            break

    env["GDRIVE_TARGET_FOLDER"] = effective_folder
    env["PATH"] = f"/usr/local/bin:/root/.local/bin:{os.path.expanduser('~/.local/bin')}:{env.get('PATH', '')}"
    if telegram_token:
        env["TELEGRAM_BOT_TOKEN"] = telegram_token
    if telegram_chat_id:
        env["TELEGRAM_CHAT_ID"] = telegram_chat_id

    target_ids = parse_row_ids(row_id)
    overall_success = True

    # -------------------------------------------------------------
    # CASE A: MULTILEVELS QUIZ
    # -------------------------------------------------------------
    if target_sub == "multilevelsquiz":
        if not target_ids:
            try:
                if str(sub_dir) not in sys.path:
                    sys.path.insert(0, str(sub_dir))
                from src.gsheet_manager import GSheetManager
                mgr = GSheetManager()
                pending = mgr.get_pending_batches()
                target_ids = [str(b.get("#", b.get("id", b.get("row_index", b.get("_row_number", ""))))) for b in pending]
                log(f"Multilevels pending scan found {len(target_ids)} batch(es): {target_ids}")
            except Exception as e:
                log(f"Warning: could not auto-fetch pending multilevels batches: {e}")
                target_ids = []

        if not target_ids:
            log("ℹ️ No target rows to process for multilevelsquiz.")
            return True

        for tid in target_ids:
            clean_tid = tid.replace("#", "").strip()
            log(f"\n▶ [multilevelsquiz] Processing Row #{clean_tid} (Quality: {quality})")

            # 1. Render
            if action in ["render", "all", "render_and_qc"]:
                log(f"🚀 [Render] Executing Manim render for #{clean_tid}...")
                cmd = [sys.executable, "scripts/run_batch.py", "--id", clean_tid, "--quality", quality, "--force"]
                cmd_str = " ".join(cmd)
                log(f"Running: {cmd_str}")
                proc = subprocess.Popen(
                    cmd, cwd=str(sub_dir), env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1
                )
                if proc.stdout:
                    for line in proc.stdout:
                        print(f"  [{clean_tid}] {line}", end="", flush=True)
                proc.wait()
                rc = proc.returncode
                if rc != 0:
                    log(f"❌ Render failed for multilevels row #{clean_tid} (code {rc})")
                    overall_success = False
                    continue
                log(f"✓ Video Render and GDrive upload completed for row #{clean_tid}!")

            # 2. QC
            if action in ["qc", "all", "render_and_qc"]:
                log(f"🔍 [QC] Executing Auto-QC Gatekeeper for Row #{clean_tid}...")
                qc_cmd = [sys.executable, "scripts/run_qc.py", "--id", clean_tid]
                qc_str = " ".join(qc_cmd)
                log(f"Running QC: {qc_str}")
                proc = subprocess.Popen(
                    qc_cmd, cwd=str(sub_dir), env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1
                )
                if proc.stdout:
                    for line in proc.stdout:
                        print(f"  [QC-{clean_tid}] {line}", end="", flush=True)
                proc.wait()
                rc = proc.returncode
                if rc != 0:
                    log(f"❌ Auto-QC failed for multilevels row #{clean_tid} (code {rc})")
                    overall_success = False
                else:
                    log(f"🎉 QC PASSED for multilevels row #{clean_tid}! Status updated to 'Ready'.")

        return overall_success

    # -------------------------------------------------------------
    # CASE B: VOCABCN / VOCABVN QUIZ
    # -------------------------------------------------------------
    elif target_sub in ["vocabCNquiz", "vocabVNquiz"]:
        if target_ids:
            for tid in target_ids:
                clean_tid = tid.replace("#", "").strip()
                log(f"\n▶ [{target_sub}] Processing Row #{clean_tid}")
                if action in ["render", "all", "render_and_qc"]:
                    cmd = [sys.executable, "scripts/run_batch.py", "--quality", quality, "--row_id", clean_tid]
                    proc = subprocess.Popen(cmd, cwd=str(sub_dir), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    if proc.stdout:
                        for line in proc.stdout:
                            print(f"  [{clean_tid}] {line}", end="", flush=True)
                    proc.wait()
                    if proc.returncode != 0:
                        overall_success = False
                        continue
                if action in ["qc", "all", "render_and_qc"]:
                    qc_cmd = [sys.executable, "scripts/run_qc.py", "--row-id", clean_tid]
                    proc = subprocess.Popen(qc_cmd, cwd=str(sub_dir), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    if proc.stdout:
                        for line in proc.stdout:
                            print(f"  [QC-{clean_tid}] {line}", end="", flush=True)
                    proc.wait()
                    if proc.returncode != 0:
                        overall_success = False
        else:
            if action in ["render", "all", "render_and_qc"]:
                cmd = [sys.executable, "scripts/run_batch.py", "--quality", quality]
                proc = subprocess.Popen(cmd, cwd=str(sub_dir), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                if proc.stdout:
                    for line in proc.stdout:
                        print(line, end="", flush=True)
                proc.wait()
                if proc.returncode != 0:
                    overall_success = False
            if action in ["qc", "all", "render_and_qc"]:
                qc_cmd = [sys.executable, "scripts/run_qc.py"]
                proc = subprocess.Popen(qc_cmd, cwd=str(sub_dir), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                if proc.stdout:
                    for line in proc.stdout:
                        print(line, end="", flush=True)
                proc.wait()
                if proc.returncode != 0:
                    overall_success = False

        return overall_success

    # -------------------------------------------------------------
    # CASE C: PINYIN QUIZ
    # -------------------------------------------------------------
    else:
        if target_ids:
            for tid in target_ids:
                clean_tid = tid.replace("#", "").strip()
                log(f"\n▶ [pinyinquiz] Processing Row #{clean_tid}")
                if action in ["render", "all", "render_and_qc"]:
                    cmd = [
                        sys.executable, "scripts/run_batch.py",
                        "--from-sheet", "--row-id", clean_tid,
                        "--quality", quality, "--upload-gdrive"
                    ]
                    proc = subprocess.Popen(cmd, cwd=str(sub_dir), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    if proc.stdout:
                        for line in proc.stdout:
                            print(f"  [{clean_tid}] {line}", end="", flush=True)
                    proc.wait()
                    if proc.returncode != 0:
                        overall_success = False
                        continue
                if action in ["qc", "all", "render_and_qc"]:
                    qc_cmd = [sys.executable, "scripts/run_qc.py", "--row-id", clean_tid]
                    proc = subprocess.Popen(qc_cmd, cwd=str(sub_dir), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    if proc.stdout:
                        for line in proc.stdout:
                            print(f"  [QC-{clean_tid}] {line}", end="", flush=True)
                    proc.wait()
                    if proc.returncode != 0:
                        overall_success = False
        else:
            if action in ["render", "all", "render_and_qc"]:
                cmd = [
                    sys.executable, "scripts/run_batch.py",
                    "--from-sheet", "--quality", quality, "--upload-gdrive"
                ]
                proc = subprocess.Popen(cmd, cwd=str(sub_dir), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                if proc.stdout:
                    for line in proc.stdout:
                        print(line, end="", flush=True)
                proc.wait()
                if proc.returncode != 0:
                    overall_success = False
            if action in ["qc", "all", "render_and_qc"]:
                qc_cmd = [sys.executable, "scripts/run_qc.py"]
                proc = subprocess.Popen(qc_cmd, cwd=str(sub_dir), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                if proc.stdout:
                    for line in proc.stdout:
                        print(line, end="", flush=True)
                proc.wait()
                if proc.returncode != 0:
                    overall_success = False

        return overall_success


def main():
    parser = argparse.ArgumentParser(description="Colab Remote Quiz Worker")
    parser.add_argument("--pipeline", "-p", default="", help="Target pipeline: pinyin, vocabcn, vocabvn, multilevels, or all")
    parser.add_argument("--row-id", "-r", default="", help="Specific Row ID(s) to render (e.g. 19, 19-22)")
    parser.add_argument("--quality", "-q", default="qh", choices=["ql", "qm", "qh", "qk"], help="Render quality")
    parser.add_argument("--action", "-a", default="all", choices=["render", "qc", "all", "render_and_qc"], help="Action to execute")
    parser.add_argument("--repo-url", default=DEFAULT_REPO, help="Git repository URL")
    parser.add_argument("--drive-folder", default=DEFAULT_DRIVE_FOLDER, help="Target GDrive Folder ID")
    parser.add_argument("--telegram-token", default="", help="Telegram Bot Token")
    parser.add_argument("--telegram-chat-id", default=DEFAULT_CHAT_ID, help="Telegram Chat ID")
    parser.add_argument("-f", default="", help="IPython/Jupyter kernel connection file (ignored)")

    # parse_known_args ensures unrecognized IPython arguments don't cause SystemExit 2
    args, unknown = parser.parse_known_args()
    if unknown:
        log(f"Ignoring unrecognized arguments from Jupyter/Colab kernel: {unknown}")

    # Discover job spec from multiple potential locations
    job_file = find_uploaded_file("quiz_job.json")
    if job_file:
        try:
            with open(job_file, "r", encoding="utf-8") as f:
                job_spec = json.load(f)
                log(f"📄 Loaded Job Spec from {job_file}: {job_spec}")
                if not args.pipeline:
                    args.pipeline = job_spec.get("pipeline", "all")
                if not args.row_id:
                    args.row_id = str(job_spec.get("row_id", ""))
                if "quality" in job_spec and job_spec["quality"]:
                    args.quality = job_spec["quality"]
                if "action" in job_spec and job_spec["action"]:
                    args.action = job_spec["action"]
                if "telegram_token" in job_spec and job_spec["telegram_token"]:
                    args.telegram_token = job_spec["telegram_token"]
                if "telegram_chat_id" in job_spec and job_spec["telegram_chat_id"]:
                    args.telegram_chat_id = job_spec["telegram_chat_id"]
        except Exception as e:
            log(f"Warning reading job spec: {e}")

    if not args.pipeline:
        args.pipeline = "all"

    log(f"=== Starting Quiz Worker: Pipeline={args.pipeline.upper()} | Row={args.row_id or 'ALL_PENDING'} | Quality={args.quality} | Action={args.action} ===")

    ensure_system_dependencies()
    ensure_python_dependencies()
    setup_hardware()

    quiz_dir = setup_repo_and_fonts(args.repo_url)
    setup_credentials(quiz_dir)

    # Determine pipelines to process
    target_raw = args.pipeline.lower()
    if target_raw in ["all", "all_pending", "all_tabs", ""]:
        targets = ALL_PIPELINES
        log(f"🔄 Continuous Mode: Processing ALL 4 Quiz Pipelines: {targets}")
    else:
        mapped = PIPELINE_MAP.get(target_raw)
        if not mapped:
            log(f"❌ Unknown pipeline: {args.pipeline}")
            return False
        targets = [mapped]

    success_all = True
    for sub in targets:
        log(f"\n=======================================================")
        log(f"▶ Processing Pipeline: {sub.upper()}")
        log(f"=======================================================")
        ok = execute_pipeline(
            quiz_dir=quiz_dir,
            target_sub=sub,
            action=args.action,
            quality=args.quality,
            row_id=args.row_id,
            drive_folder=args.drive_folder,
            telegram_token=args.telegram_token,
            telegram_chat_id=args.telegram_chat_id
        )
        if not ok:
            log(f"⚠️ Pipeline {sub} reported failure or incomplete rendering.")
            success_all = False

    if success_all:
        log("🎉 [COLAB_QUIZ_COMPLETE] All requested pipelines completed successfully on Google Colab VM.")
        print("[COLAB_QUIZ_COMPLETE]", flush=True)
        return True
    else:
        log("❌ [COLAB_QUIZ_FAILED] One or more pipelines encountered errors.")
        return False


if __name__ == "__main__":
    ok = main()
    if not ok:
        raise RuntimeError("Worker execution reported failures.")

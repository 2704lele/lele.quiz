import os
from dataclasses import dataclass, field
from typing import List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@dataclass
class AppConfig:
    base_dir: str = BASE_DIR
    quiz_type: str = "multilevels"  # 1 Nghĩa - 5 Cấp độ HSK (HSK 1 -> HSK 5)

    # Spreadsheet Settings
    spreadsheet_id: str = "1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0"
    sheet_tab_name: str = "multilevels"

    # Shared Google Drive target folder
    gdrive_target_folder: str = "17xOkiW-XOWRDK2CCwNEl_rlf1rGKqKXm"
    gdrive_subfolder: str = "multilevelsquiz"

    # Credential Paths
    creds_paths: List[str] = field(default_factory=lambda: [
        os.path.expanduser("~/.cloud-profiles/lelehoctiengtrung/google_sa/service_account.json"),
        "/workspace/lelehoctiengtrung/credentials/google_sa/service_account.json",
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
        os.path.join(BASE_DIR, "configs", "service_account.json"),
        os.path.join(BASE_DIR, "service_account.json"),
        os.path.join(os.path.dirname(BASE_DIR), "vocabCNquiz", "configs", "service_account.json"),
        os.path.join(os.path.dirname(BASE_DIR), "pinyinquiz", "configs", "service_account.json"),
        os.path.join(os.path.dirname(BASE_DIR), "configs", "service_account.json"),
        os.path.expanduser("~/.config/gspread/service_account.json")
    ])

    # Video Specs
    pixel_width: int = 1080
    pixel_height: int = 1920
    frame_width: float = 9.0
    frame_height: float = 16.0
    fps: int = 60

    # Fonts
    chinese_font: str = "Arial Unicode MS"
    latin_font: str = "sans-serif"
    vietnamese_font: str = "Arial"

    # Visual Theme - Multi-Level Gamified Progression
    theme_primary_color: str = "#8b5cf6"     # Purple 500
    theme_accent_color: str = "#f59e0b"      # Amber 500
    theme_card_bg: str = "#0b0f19"
    theme_hook_text: str = "1 NGHĨA - 5 CẤP ĐỘ HSK"

    # Level Colors (Level 1 -> 5)
    level_colors: List[str] = field(default_factory=lambda: [
        "#10b981",  # L1 (HSK 1): Emerald Green
        "#06b6d4",  # L2 (HSK 2): Cyan Sky
        "#3b82f6",  # L3 (HSK 3): Royal Blue
        "#f59e0b",  # L4 (HSK 4): Amber Orange
        "#ef4444"   # L5 (HSK 5): Crimson Boss / Gold
    ])

    # Timing
    countdown_seconds_per_level: float = 5.0
    outro_seconds: float = 5.0
    total_duration_seconds: float = 30.0

    # Paths
    assets_audio_dir: str = os.path.join(BASE_DIR, "assets", "audio")
    output_videos_dir: str = os.path.join(BASE_DIR, "output", "videos")
    output_thumbnails_dir: str = os.path.join(BASE_DIR, "output", "thumbnails")
    output_metadata_dir: str = os.path.join(BASE_DIR, "output", "metadata")
    generated_scenes_dir: str = os.path.join(BASE_DIR, "output", "generated_scenes")

    # Audio effect paths
    tick_audio_path: str = os.path.join(BASE_DIR, "assets", "audio", "tick.mp3")
    swoosh_audio_path: str = os.path.join(BASE_DIR, "assets", "audio", "swoosh.mp3")
    ding_audio_path: str = os.path.join(BASE_DIR, "assets", "audio", "ding.mp3")
    tension_audio_path: str = os.path.join(BASE_DIR, "assets", "audio", "tension.mp3")
    glow_audio_path: str = os.path.join(BASE_DIR, "assets", "audio", "glow.mp3")
    victory_audio_path: str = os.path.join(BASE_DIR, "assets", "audio", "victory.mp3")

config = AppConfig()

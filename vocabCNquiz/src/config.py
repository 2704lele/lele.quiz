import os
from dataclasses import dataclass, field
from typing import List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@dataclass
class AppConfig:
    base_dir: str = BASE_DIR
    quiz_type: str = "vocabCN"  # Chinese Question -> Guess Vietnamese Answer

    # Spreadsheet Settings
    spreadsheet_id: str = "1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0"
    sheet_tab_name: str = "vocabCN"

    # Shared Google Drive target folder
    gdrive_target_folder: str = "1Y240J5-oXA-UDm2IKvp7qCBVsRempbCB"
    gdrive_subfolder: str = "vocabCNquiz"

    # Credential Paths
    creds_paths: List[str] = field(default_factory=lambda: [
        os.path.expanduser("~/.cloud-profiles/lelehoctiengtrung/google_sa/service_account.json"),
        "/workspace/lelehoctiengtrung/credentials/google_sa/service_account.json",
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
        os.path.join(BASE_DIR, "configs", "service_account.json"),
        os.path.join(BASE_DIR, "service_account.json"),
        os.path.join(os.path.dirname(BASE_DIR), "pinyinquiz", "configs", "service_account.json"),
        os.path.join(os.path.dirname(BASE_DIR), "configs", "service_account.json"),
        os.path.expanduser("~/.config/gspread/service_account.json")
    ])

    # Video Specs
    pixel_width: int = 1080
    pixel_height: int = 1920
    frame_width: float = 9.0
    frame_height: float = 16.0

    # Fonts
    chinese_font: str = "Arial Unicode MS"
    latin_font: str = "sans-serif"
    vietnamese_font: str = "Arial"

    # Visual Theme - Cyber Emerald Green
    theme_primary_color: str = "#10b981"    # Emerald 500
    theme_accent_color: str = "#34d399"     # Emerald 400
    theme_card_bg: str = "#0b0f19"
    theme_hook_text: str = "DỊCH NGHĨA TRONG 5S"

    # Timing
    countdown_seconds: int = 5
    answer_wait_seconds: float = 2.2
    transition_wait_seconds: float = 0.5

    # Paths
    assets_audio_dir: str = os.path.join(BASE_DIR, "assets", "audio")
    output_videos_dir: str = os.path.join(BASE_DIR, "output", "videos")
    output_thumbnails_dir: str = os.path.join(BASE_DIR, "output", "thumbnails")
    generated_scenes_dir: str = os.path.join(BASE_DIR, "output", "generated_scenes")
    bell_audio_path: str = os.path.join(BASE_DIR, "assets", "audio", "ding.mp3")
    tick_audio_path: str = os.path.join(BASE_DIR, "assets", "audio", "tick.mp3")

config = AppConfig()

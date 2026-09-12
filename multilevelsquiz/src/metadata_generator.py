import os
import re
import json
import logging
from typing import List, Dict, Any
try:
    from multilevelsquiz.src.config import config
except ImportError:
    from src.config import config

logger = logging.getLogger("MetadataGenerator")

def sanitize_filename(name: str) -> str:
    s = re.sub(r'[/\\:*?"<>|]', '_', name)
    return s.strip()

def clean_topic_display(topic: str) -> str:
    parts = topic.split("•")
    if len(parts) > 1:
        return parts[1].strip()
    return topic.strip()

def generate_multilevels_metadata(
    concept_name_vi: str,
    levels: List[Dict[str, Any]],
    hook_title: str = "",
    cta_text: str = ""
) -> Dict[str, Any]:
    clean_concept = clean_topic_display(concept_name_vi)

    emoji_map = {
        "tức giận": "😡🔥",
        "giận": "😡😤",
        "vui": "😄🎉",
        "đẹp": "✨🌸",
        "thông minh": "🧠💡",
        "giàu": "💰💎",
        "đắt": "🏷️💸",
        "sợ": "😱⚡",
        "cẩn thận": "⚠️👀",
        "nhanh": "⚡🏃",
        "khó": "🧩🏋️",
        "thích": "💖🥰",
        "thất vọng": "🥺🥀",
        "giúp": "🤝❤️",
        "thành công": "🏆🌟",
        "tự tin": "🦁💪"
    }

    chosen_emoji = "🎯🔥"
    for key, emo in emoji_map.items():
        if key in clean_concept.lower():
            chosen_emoji = emo
            break

    if hook_title and hook_title.strip():
        yt_title = f"{hook_title.strip()} {chosen_emoji} | Lê Lê Học Tiếng Trung #Shorts"
    else:
        yt_title = f"5 Cấp Độ '{clean_concept}' Trong Tiếng Trung - Bạn Ở HSK Mấy? {chosen_emoji} | Lê Lê Học Tiếng Trung #Shorts"

    if len(yt_title) > 95:
        yt_title = f"5 Cấp Độ '{clean_concept}' Tiếng Trung (HSK 1-5) {chosen_emoji} #Shorts"

    level_lines = []
    for item in levels:
        lvl_num = item.get("level", 1)
        hz = item.get("hanzi", "")
        py = item.get("pinyin", "")
        hv = item.get("han_viet", "")
        mean = item.get("meaning_vi", "")
        nuance = item.get("nuance_note", "")

        line = f"• HSK {lvl_num}: {hz} ({py}) [{hv}] ➔ {mean}"
        if nuance:
            line += f" ({nuance})"
        level_lines.append(line)

    levels_formatted = "\n".join(level_lines)

    final_cta = cta_text or "Từ HSK 5 bạn có biết không? Comment mốc điểm bạn vượt qua nhé!"

    yt_description = f"""🎯 Thử thách phản xạ từ vựng: 1 NGHĨA - 5 CẤP ĐỘ HSK (Chủ đề: {clean_concept.upper()})!
Cứ mỗi 5 giây độ khó sẽ tăng dần từ HSK 1 đến HSK 5. Bạn dừng lại ở cấp độ mấy? Hãy comment điểm số bên dưới nhé! 👇

📚 5 CẤP ĐỘ TỪ VỰNG TRONG VIDEO:
{levels_formatted}

💬 {final_cta}

🔔 Đừng quên bấm Like, Đăng ký kênh @lelehoctiengtrung và bật chuông thông báo để cùng luyện phản xạ tiếng Trung mỗi ngày cùng Lê Lê nhé!

#lelehoctiengtrung #hoctiengtrung #tiengtrunggiaotiep #hsk #hsk1 #hsk2 #hsk3 #hsk4 #hsk5 #tiengtrungonline #Shorts #learnchinese
"""

    tiktok_caption = f"5 cấp độ từ vựng '{clean_concept}' từ HSK 1 đến HSK 5! {chosen_emoji} Bạn dừng ở HSK mấy? Comment kết quả bên dưới nhé! 💬👇 #lelehoctiengtrung #hoctiengtrung #tiengtrung #hsk #vocabquiz #xuhuong #learnchinese"

    fb_caption = f"Thử tài phản xạ: 1 Nghĩa - 5 Cấp độ HSK (Chủ đề: {clean_concept})! {chosen_emoji}\nBạn chinh phục được từ HSK 5 không? Comment mốc điểm bên dưới cùng Lê Lê nha! ✨\n\n#lelehoctiengtrung #tiengtrung #hoctiengtrung #hsk #reelsvn"

    full_text = f"""📝 METADATA CHO VIDEO: 1 Nghĩa - 5 Cấp Độ ({clean_concept})
───────────────────────────────────────────────────────────────────

【 1. YOUTUBE SHORTS 】
Tiêu đề (Title):
{yt_title}

Mô tả (Description):
{yt_description.strip()}

【 2. TIKTOK 】
Caption & Hashtags:
{tiktok_caption}

【 3. FACEBOOK REELS 】
Caption & Hashtags:
{fb_caption}
"""

    return {
        "concept_name_vi": clean_concept,
        "topic": f"1 Nghĩa 5 Cấp • {clean_concept}",
        "level": "HSK 1-5",
        "hook_title": hook_title,
        "cta_text": final_cta,
        "youtube": {
            "title": yt_title,
            "description": yt_description.strip(),
            "tags": ["lelehoctiengtrung", "hoctiengtrung", "tiengtrunggiaotiep", "multilevelsquiz", "hsk", "Shorts", "learnchinese"]
        },
        "tiktok": {
            "caption": tiktok_caption
        },
        "facebook": {
            "caption": fb_caption
        },
        "sheet_cell_text": full_text
    }

def save_and_upload_metadata(
    batch_id: Any,
    concept_name_vi: str,
    levels: List[Dict[str, Any]],
    hook_title: str = "",
    cta_text: str = "",
    gsheet_mgr=None,
    row_number: int = None
) -> Dict[str, Any]:
    data = generate_multilevels_metadata(
        concept_name_vi=concept_name_vi,
        levels=levels,
        hook_title=hook_title,
        cta_text=cta_text
    )
    clean_id = str(batch_id).replace("#", "").strip()
    safe_topic = sanitize_filename(concept_name_vi)

    meta_dir = os.path.join(config.base_dir, "output", "metadata")
    os.makedirs(meta_dir, exist_ok=True)

    local_txt = os.path.join(meta_dir, f"metadata_batch_{clean_id}_{safe_topic}.txt")
    with open(local_txt, "w", encoding="utf-8") as f:
        f.write(data["sheet_cell_text"])

    local_json = os.path.join(meta_dir, f"metadata_batch_{clean_id}_{safe_topic}.json")
    with open(local_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if gsheet_mgr and row_number:
        try:
            gsheet_mgr.worksheet.update(f"J{row_number}", [[data["sheet_cell_text"]]])
            logger.info(f"Updated metadata in Column J for row {row_number}")
        except Exception as e:
            logger.warning(f"Failed to update metadata to Google Sheet row {row_number}: {e}")

    return data

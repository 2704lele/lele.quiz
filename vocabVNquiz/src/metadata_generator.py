import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
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

def generate_social_metadata(topic: str, level: str, words: List[Dict[str, str]]) -> Dict[str, Any]:
    clean_topic = clean_topic_display(topic)
    level_tag = level.replace(" ", "").upper()
    
    emoji_map = {
        "Đồ Ăn": "🍎🍜",
        "Thức Uống": "🧋🥤",
        "Đời Sống": "🏠✨",
        "Gia Đình": "👨‍👩‍👧‍👦❤️",
        "Số Đếm": "🔢⏰",
        "Thời Gian": "⏳🕰️",
        "Địa Điểm": "🏫✈️",
        "Cảm Xúc": "😄🥰",
        "Mua Sắm": "🛍️🏷️",
        "Phương Tiện": "🚗🚌",
        "Thời Tiết": "☀️🌧️"
    }
    
    chosen_emoji = "🎯✨"
    for key, emo in emoji_map.items():
        if key.lower() in topic.lower():
            chosen_emoji = emo
            break

    yt_title = f"Thử Thách Đoán Tiếng Trung {level}: {clean_topic} {chosen_emoji} | Lê Lê Học Tiếng Trung #Shorts"
    if len(yt_title) > 95:
        yt_title = f"Đoán Tiếng Trung {level}: {clean_topic} {chosen_emoji} #Shorts"
        
    word_lines = []
    for idx, w in enumerate(words, start=1):
        hz = w.get("hanzi", "")
        py = w.get("pinyin", "")
        mean = w.get("meaning", "")
        word_lines.append(f"{idx}. {mean} ➔ {hz} ({py})")
    words_formatted = "\n".join(word_lines)

    yt_description = f"""🎯 Thử thách phản xạ Tiếng Việt ➔ Tiếng Trung {level} chủ đề: {clean_topic.upper()}!
Bạn đoán đúng được bao nhiêu từ trên {len(words)} từ? Hãy comment số điểm của bạn bên dưới nhé! 👇

📚 DANH SÁCH TỪ VỰNG TRONG VIDEO:
{words_formatted}

🔔 Đừng quên bấm Like, Đăng ký kênh @lelehoctiengtrung và bật chuông thông báo để cùng luyện phản xạ tiếng Trung mỗi ngày cùng Lê Lê nhé!

#lelehoctiengtrung #hoctiengtrung #tiengtrunggiaotiep #vocabquiz #{level_tag.lower()} #tiengtrungonline #Shorts #learnchinese #hsk
"""

    tiktok_caption = f"Đố bạn đoán đúng 5/5 từ tiếng Trung chủ đề {clean_topic} này? {chosen_emoji} Thử ngay xem bạn được mấy điểm nhé! 💬👇 #lelehoctiengtrung #hoctiengtrung #tiengtrung #tiengtrungmoibatdau #{level_tag.lower()} #vocabquiz #xuhuong #learnchinese"

    fb_caption = f"Thử tài phản xạ dịch Tiếng Việt sang Tiếng Trung {level} - Chủ đề {clean_topic}! {chosen_emoji}\nBạn tự tin đúng bao nhiêu câu? Comment kết quả bên dưới cùng Lê Lê nha! ✨\n\n#lelehoctiengtrung #tiengtrung #hoctiengtrung #{level_tag.lower()} #reelsvn #hsk"

    full_text = f"""📝 METADATA CHO VIDEO: {topic} ({level})
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
        "topic": topic,
        "clean_topic": clean_topic,
        "level": level,
        "youtube": {
            "title": yt_title,
            "description": yt_description.strip(),
            "tags": ["lelehoctiengtrung", "hoctiengtrung", "tiengtrunggiaotiep", "vocabquiz", level_tag.lower(), "Shorts", "learnchinese", "hsk"]
        },
        "tiktok": {
            "caption": tiktok_caption
        },
        "facebook": {
            "caption": fb_caption
        },
        "sheet_cell_text": full_text
    }

def save_and_upload_metadata(batch_id: Any, topic: str, level: str, words: List[Dict[str, str]], gsheet_mgr=None, row_number: int = None) -> Dict[str, Any]:
    data = generate_social_metadata(topic, level, words)
    clean_id = str(batch_id).replace("#", "").strip()
    safe_topic = sanitize_filename(topic)
    
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

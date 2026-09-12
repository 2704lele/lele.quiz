"""
Social Media Batch Publisher for LeLe Chinese Quiz.
Publishes video/post for a specific sheet row across 3 Buffer 1 platforms (YouTube Shorts, TikTok, Facebook Reels).
Compliant with 06_SECURITY_AND_CODE_AUDITING_GUIDE.md (<= 150 lines).
"""
import os, re, sys, time, argparse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from monitor import get_gsheet_client, fetch_tab_raw_values, STANDARD_COLUMNS, SOCIAL_CHANNELS

try:
    from buffer_client import load_buffer_credentials, publish_post, get_channel_token
except (ImportError, ModuleNotFoundError):
    from scripts.buffer_client import load_buffer_credentials, publish_post, get_channel_token


def parse_args():
    parser = argparse.ArgumentParser(description="Publish quiz batch row to 3 Buffer 1 Social Media channels")
    parser.add_argument("--tab", type=str, default="pinyin", choices=["pinyin", "vocabCN", "vocabVN", "vocabcn", "vocabvn", "multilevels", "multilevelsquiz"])
    parser.add_argument("--id", "--row", dest="row_id", type=int, required=True, help="Row number / Batch ID to publish")
    parser.add_argument("--channels", type=str, default="all", help="Target channels: 'all', 'buffer1', 'youtube', 'tiktok', 'facebook', 'fb'")
    parser.add_argument("--dry-run", action="store_true", help="Simulate publishing without writing to Buffer or Sheets")
    return parser.parse_args()


def parse_platform_metadata(row_dict: Dict[str, str]) -> Dict[str, str]:
    """Extracts tailored title, description, and captions for each platform from metadata column."""
    meta, topic, level = row_dict.get("metadata", ""), row_dict.get("Topic", "HỌC TIẾNG TRUNG"), row_dict.get("Level", "HSK")
    words = [row_dict.get(f"Word {i}", "") for i in range(1, 6) if row_dict.get(f"Word {i}")]
    word_lines = "\n".join([f"✨ {w.replace('||', ' : ').replace('|', ' ')}" for w in words])
    fallback = f"🏮 {topic.upper()} ({level})\n\nCùng Lê Lê thử thách trí nhớ với 5 từ vựng siêu hay hôm nay nhé!\n\n{word_lines}\n\n👇 Bình luận ngay đáp án của bạn bên dưới nha! ❤️\n#lelehoctiengtrung #hoctiengtrung #hsk"
    data = {"youtube_title": f"Thử Thách Đoán Pinyin {level}: {topic} 🎯✨ | Lê Lê Học Tiếng Trung #Shorts", "youtube_desc": fallback, "tiktok": fallback, "facebook": fallback, "general": fallback}
    if not meta or "【" not in meta:
        return data

    yt = re.search(r"【\s*1\.\s*YOUTUBE[^】]*】(.*?)(?=【|\Z)", meta, re.DOTALL | re.IGNORECASE)
    if yt:
        yt_b = yt.group(1).strip()
        t_m, d_m = re.search(r"Tiêu đề[^\n:]*:\s*\n?([^\n]+)", yt_b, re.IGNORECASE), re.search(r"Mô tả[^\n:]*:\s*\n?(.*)", yt_b, re.DOTALL | re.IGNORECASE)
        if t_m: data["youtube_title"] = t_m.group(1).strip()
        if d_m: data["youtube_desc"] = d_m.group(1).strip()

    tt = re.search(r"【\s*2\.\s*TIKTOK[^】]*】(.*?)(?=【|\Z)", meta, re.DOTALL | re.IGNORECASE)
    if tt:
        tt_b = tt.group(1).strip()
        c_m = re.search(r"Caption[^\n:]*:\s*\n?(.*)", tt_b, re.DOTALL | re.IGNORECASE)
        data["tiktok"] = (c_m.group(1) if c_m else tt_b).strip()

    fb = re.search(r"【\s*3\.\s*FACEBOOK[^】]*】(.*?)(?=【|\Z)", meta, re.DOTALL | re.IGNORECASE)
    if fb:
        fb_b = fb.group(1).strip()
        c_m = re.search(r"Caption[^\n:]*:\s*\n?(.*)", fb_b, re.DOTALL | re.IGNORECASE)
        data["facebook"] = (c_m.group(1) if c_m else fb_b).strip()
    return data


def is_channel_match(ch: Dict[str, str], channels_filter: str) -> bool:
    """Checks if a channel matches the user's filter expression (Buffer 1 only)."""
    if not channels_filter or channels_filter.lower() in ["all", "buffer1", "video"]: return True
    f, p_name, c_name = channels_filter.lower(), ch.get("platform", "").lower(), ch.get("name", "").lower()
    return any(t.strip() in p_name or t.strip() in c_name or (t.strip() == "fb" and "facebook" in p_name) for t in f.split(","))


def to_direct_stream_url(url: str) -> str:
    """Converts Google Drive view URL to direct download stream link."""
    m = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    return f"https://drive.usercontent.google.com/download?id={m.group(1)}&confirm=t" if m else url


def publish_row_to_social(tab_name: str, row_id: int, channels: str = "buffer1", dry_run: bool = False, delay_minutes: int = 30) -> Dict[str, Any]:
    """Executes social publishing with automatic 30-minute queue delay and updates Google Sheets state."""
    tab_map = {"vocabcn": "vocabCN", "vocabvn": "vocabVN", "pinyin": "pinyin", "multilevels": "multilevels", "multilevelsquiz": "multilevels"}
    target_tab = tab_map.get(tab_name.lower(), tab_name)

    client, err = get_gsheet_client()
    if not client: raise RuntimeError(f"GSheet Auth Error: {err}")
    ok, rows, msg = fetch_tab_raw_values(target_tab, client=client, use_cache=False)
    if not ok or len(rows) < row_id: raise ValueError(f"Row #{row_id} not found in tab '{target_tab}'")

    headers, row_data = rows[0], rows[row_id - 1]
    row_dict = {headers[i]: row_data[i] if i < len(row_data) else "" for i in range(len(headers))}
    topic, video_url = row_dict.get("Topic", "Unknown"), row_dict.get("Video", "").strip()
    meta_map = parse_platform_metadata(row_dict)
    direct_video = to_direct_stream_url(video_url) if video_url else ""
    creds = load_buffer_credentials()

    vn_time = (datetime.now() + timedelta(minutes=delay_minutes)).strftime("%H:%M %d/%m")
    due_utc = (datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    print(f"\n🚀 [SOCIAL DISPATCH] Tab: '{target_tab}' | Row #{row_id}: '{topic}'")
    print(f"🎬 Video: {direct_video if direct_video else 'None'} | ⏰ Đăng lúc: {vn_time} (30 phút sau)")

    published_channels = []
    for ch in SOCIAL_CHANNELS:
        ch_name, ch_id, platform = ch["name"], ch["channel_id"], ch["platform"]
        if not is_channel_match(ch, channels): continue

        if "youtube" in platform.lower() or ch_id == "6a83dda0ccaf649a67c8cb92":
            caption, post_title = meta_map["youtube_desc"], meta_map["youtube_title"]
        elif "tiktok" in platform.lower() or ch_id == "6a83dc5bccaf649a67c8b30f":
            caption, post_title = meta_map["tiktok"], topic
        else:
            caption, post_title = meta_map["facebook"], topic

        ch_token = get_channel_token(ch_id, creds)
        if dry_run:
            print(f"  [DRY-RUN] ✔ {platform} ({ch_name}) [Lên lịch: {vn_time}] [Tiêu đề: '{post_title[:30]}...']")
            published_channels.append(platform)
        else:
            try:
                media = [direct_video] if direct_video else []
                publish_post(ch_token, ch_id, caption, media_urls=media, title=post_title, delay_minutes=delay_minutes, due_at=due_utc)
                print(f"  [LIVE] ✔ Đã lên lịch (đúng {vn_time} đăng) ➔ {platform} ({ch_name})")
                published_channels.append(platform)
            except Exception as ex:
                print(f"  [LIVE] ⚠ {platform} ({ch_name}): {ex}")
                published_channels.append(f"{platform} (Error)")

    if not dry_run:
        try:
            ws = client.open_by_key(os.getenv("SPREADSHEET_ID", "1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0")).worksheet(target_tab)
            ws.update_cell(row_id, 4, "Published")       # Column D: Status
            ws.update_cell(row_id, 12, f"✔ Scheduled ({vn_time})") # Col L: Youtube
            ws.update_cell(row_id, 13, f"✔ Scheduled ({vn_time})") # Col M: Tiktok
            ws.update_cell(row_id, 14, f"✔ Scheduled ({vn_time})") # Col N: Facebook
            print(f"🎉 Updated Sheet Tab '{target_tab}' Row #{row_id} Status -> 'Published' (Lịch: {vn_time})!")
        except Exception as e:
            print(f"⚠ Could not update sheet cells: {e}")

    return {"status": "success", "row_id": row_id, "tab": target_tab, "channels": published_channels, "scheduled_at": vn_time}


def main():
    args = parse_args()
    publish_row_to_social(args.tab, args.row_id, channels=args.channels, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

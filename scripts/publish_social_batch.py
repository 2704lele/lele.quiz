"""
Social Media Batch Publisher for LeLe Chinese Quiz.
Publishes video/post for a specific sheet row across 3 Buffer 1 platforms (YouTube Shorts, TikTok, Facebook Reels).
Compliant with 06_SECURITY_AND_CODE_AUDITING_GUIDE.md (<= 150 lines).
"""
import os, re, sys, time, argparse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

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
    parser.add_argument("--id", "--row", dest="row_id", type=int, default=None, help="Row number / Batch ID (optional, auto-detected if omitted)")
    parser.add_argument("--level", type=str, default="", help="Filter auto-detect by HSK level (e.g. 'HSK 1', 'HSK 2', 'HSK 3')")
    parser.add_argument("--schedule", type=str, default="", help="Multi-slot schedule: '07:16:HSK1,11:18:HSK2,16:26:HSK3' or '07:00,11:00,16:00'")
    parser.add_argument("--channels", type=str, default="youtube,tiktok", help="Target channels: 'all', 'buffer1', 'youtube,tiktok', 'facebook'")
    parser.add_argument("--time", "--scheduled-at", dest="scheduled_at", type=str, default="", help="Scheduled time 'HH:MM' or 'YYYY-MM-DD HH:MM'")
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


def find_eligible_row(rows: List[List[str]], level: str = "", exclude_rows: Optional[set] = None) -> Optional[int]:
    """Finds the first eligible Ready row matching the specified level."""
    exclude = exclude_rows or set()
    headers = rows[0]
    target_lvl = re.sub(r'[^a-zA-Z0-9]', '', level).lower() if level else ""
    for idx in range(1, len(rows)):
        r_num = idx + 1
        if r_num in exclude: continue
        r_data = rows[idx]
        r_dict = {headers[i]: r_data[i] if i < len(r_data) else "" for i in range(len(headers))}
        status, video = r_dict.get("Status", "").strip(), r_dict.get("Video", "").strip()
        row_lvl = re.sub(r'[^a-zA-Z0-9]', '', r_dict.get("Level", "")).lower()
        if status.lower() == "ready" and video and "drive.google.com" in video:
            if not target_lvl or target_lvl in row_lvl:
                return r_num
    return None


def publish_row_to_social(tab_name: str, row_id: int, channels: str = "youtube,tiktok", dry_run: bool = False, delay_minutes: int = 30, scheduled_at: Optional[str] = None) -> Dict[str, Any]:
    """Executes social publishing with automatic or explicit scheduled time and updates Google Sheets state."""
    tab_map = {"vocabcn": "vocabCN", "vocabvn": "vocabVN", "pinyin": "pinyin", "multilevels": "multilevels", "multilevelsquiz": "multilevels"}
    target_tab = tab_map.get(tab_name.lower(), tab_name)

    client, err = get_gsheet_client()
    if not client: raise RuntimeError(f"GSheet Auth Error: {err}")
    ok, rows, msg = fetch_tab_raw_values(target_tab, client=client, use_cache=False)
    if not ok or len(rows) < row_id: raise ValueError(f"Row #{row_id} not found in tab '{target_tab}'")

    headers, row_data = rows[0], rows[row_id - 1]
    row_dict = {headers[i]: row_data[i] if i < len(row_data) else "" for i in range(len(headers))}
    topic, video_url = row_dict.get("Topic", "Unknown"), row_dict.get("Video", "").strip()
    level = row_dict.get("Level", "")
    meta_map = parse_platform_metadata(row_dict)
    direct_video = to_direct_stream_url(video_url) if video_url else ""
    creds = load_buffer_credentials()

    if scheduled_at:
        now_ict = datetime.now(timezone(timedelta(hours=7)))
        s_str = scheduled_at.strip()
        if len(s_str.split(":")) == 2 and " " not in s_str:
            h, m = map(int, s_str.split(":"))
            target_ict = now_ict.replace(hour=h, minute=m, second=0, microsecond=0)
        else:
            target_ict = datetime.strptime(s_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone(timedelta(hours=7)))
        vn_time = target_ict.strftime("%H:%M %d/%m")
        due_utc = target_ict.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    else:
        vn_time = (datetime.now() + timedelta(minutes=delay_minutes)).strftime("%H:%M %d/%m")
        due_utc = (datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    print(f"\n🚀 [SOCIAL DISPATCH] Tab: '{target_tab}' | Row #{row_id} ({level}): '{topic}'")
    print(f"🎬 Video: {direct_video if direct_video else 'None'} | ⏰ Đăng lúc: {vn_time}")

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
            if any("youtube" in p.lower() for p in published_channels):
                ws.update_cell(row_id, 12, f"✔ Scheduled ({vn_time})")
            if any("tiktok" in p.lower() for p in published_channels):
                ws.update_cell(row_id, 13, f"✔ Scheduled ({vn_time})")
            if any("facebook" in p.lower() for p in published_channels):
                ws.update_cell(row_id, 14, f"✔ Scheduled ({vn_time})")
            print(f"🎉 Updated Sheet Tab '{target_tab}' Row #{row_id} Status -> 'Published' (Lịch: {vn_time})!")
        except Exception as e:
            print(f"⚠ Could not update sheet cells: {e}")

    return {"status": "success", "row_id": row_id, "tab": target_tab, "channels": published_channels, "scheduled_at": vn_time}


def main():
    args = parse_args()
    tab_map = {"vocabcn": "vocabCN", "vocabvn": "vocabVN", "pinyin": "pinyin", "multilevels": "multilevels", "multilevelsquiz": "multilevels"}
    target_tab = tab_map.get(args.tab.lower(), args.tab)

    if args.schedule:
        client, err = get_gsheet_client()
        if not client: raise RuntimeError(f"GSheet Auth Error: {err}")
        ok, rows, msg = fetch_tab_raw_values(target_tab, client=client, use_cache=False)
        if not ok: raise ValueError(f"Failed to fetch '{target_tab}': {msg}")

        slots = [s.strip() for s in args.schedule.split(",") if s.strip()]
        used_rows = set()
        for slot in slots:
            parts = slot.split(":")
            if len(parts) >= 3:
                time_str, lvl = f"{parts[0]}:{parts[1]}", parts[2]
            elif len(parts) == 2:
                time_str, lvl = slot, ""
            else:
                time_str, lvl = slot, ""

            r_id = find_eligible_row(rows, level=lvl, exclude_rows=used_rows)
            if not r_id:
                print(f"❌ [Auto-Filter] Không tìm thấy dòng Ready nào cho Level '{lvl or 'bất kỳ'}' trong tab '{target_tab}'!")
                continue
            used_rows.add(r_id)
            publish_row_to_social(target_tab, r_id, channels=args.channels, dry_run=args.dry_run, scheduled_at=time_str)
        return

    if args.row_id is not None:
        publish_row_to_social(target_tab, args.row_id, channels=args.channels, dry_run=args.dry_run, scheduled_at=args.scheduled_at)
    else:
        client, err = get_gsheet_client()
        if not client: raise RuntimeError(f"GSheet Auth Error: {err}")
        ok, rows, msg = fetch_tab_raw_values(target_tab, client=client, use_cache=False)
        if not ok: raise ValueError(f"Failed to fetch '{target_tab}': {msg}")

        r_id = find_eligible_row(rows, level=args.level)
        if not r_id:
            print(f"❌ [Auto-Filter] Không tìm thấy dòng Ready nào cho Level '{args.level or 'bất kỳ'}' trong tab '{target_tab}'!")
            sys.exit(1)
        print(f"🎯 [Auto-Filter] Tìm thấy Dòng #{r_id} (Level: '{args.level or 'bất kỳ'}') trong tab '{target_tab}'")
        publish_row_to_social(target_tab, r_id, channels=args.channels, dry_run=args.dry_run, scheduled_at=args.scheduled_at)


if __name__ == "__main__":
    main()

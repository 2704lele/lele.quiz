"""
Interactive Telegram Bot & Polling Listener for LeLe Chinese Social Publishing.
Enables 1-Click Moderation & Immediate Dispatch via Telegram Inline Buttons.
Compliant with Zero-Leak Vault Isolation & Single Responsibility (<= 150 lines).
"""
import os, sys, time, json, urllib.request, urllib.parse
from typing import Tuple, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from publish_social_batch import publish_row_to_social, parse_platform_metadata
except (ImportError, ModuleNotFoundError):
    from scripts.publish_social_batch import publish_row_to_social, parse_platform_metadata
from monitor import get_gsheet_client, fetch_tab_raw_values

TELEGRAM_ENV_PATH = os.path.expanduser("~/.cloud-profiles/lelehoctiengtrung/telegram/telegram.env")


def load_telegram_creds() -> Tuple[str, str]:
    """Loads Telegram Bot credentials safely from isolated vault."""
    token, chat_id = os.getenv("TELEGRAM_BOT_TOKEN", "").strip(), os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token and os.path.exists(TELEGRAM_ENV_PATH):
        with open(TELEGRAM_ENV_PATH, "r") as f:
            for line in f:
                if line.startswith("TELEGRAM_BOT_TOKEN="): token = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("TELEGRAM_CHAT_ID="): chat_id = line.split("=", 1)[1].strip().strip('"').strip("'")
    return token, chat_id or "1187577977"


def send_review_post(tab_name: str, row_id: int) -> bool:
    """Sends an interactive review card with inline buttons to Telegram."""
    bot_token, chat_id = load_telegram_creds()
    if not bot_token:
        print("⚠ TELEGRAM_BOT_TOKEN missing in vault.")
        return False

    client, err = get_gsheet_client()
    tab_map = {"vocabcn": "vocabCN", "vocabvn": "vocabVN", "pinyin": "pinyin"}
    target_tab = tab_map.get(tab_name.lower(), tab_name)
    ok, rows, _ = fetch_tab_raw_values(target_tab, client=client)
    if not ok or len(rows) < row_id:
        print(f"Row #{row_id} not found in tab '{target_tab}'")
        return False

    headers, row_data = rows[0], rows[row_id - 1]
    row_dict = {headers[i]: row_data[i] if i < len(row_data) else "" for i in range(len(headers))}
    topic, level, video_url = row_dict.get("Topic", "Unknown"), row_dict.get("Level", "HSK"), row_dict.get("Video", "").strip()
    meta_map = parse_platform_metadata(row_dict)

    text = (
        f"🏮 <b>[LELE QUIZ] DUYỆT BÀI ĐĂNG MẠNG XÃ HỘI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Tab:</b> <code>{target_tab}</code> | <b>Dòng:</b> #{row_id}\n"
        f"📝 <b>Chủ đề:</b> {topic} ({level})\n"
        f"🎬 <b>Video:</b> <a href=\"{video_url}\">Xem Video GDrive</a>\n\n"
        f"📺 <b>YouTube:</b> <i>{meta_map.get('youtube_title', topic)[:90]}</i>\n"
        f"🎵 <b>TikTok:</b> <i>{meta_map.get('tiktok', '')[:100]}...</i>\n"
        f"🌐 <b>Facebook:</b> <i>{meta_map.get('facebook', '')[:100]}...</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 <b>Bấm nút dưới để ĐĂNG NGAY (thay vì hẹn giờ):</b>"
    )

    markup = {
        "inline_keyboard": [
            [{"text": "🚀 Đăng Ngay 3 Kênh Video (Shorts / TikTok / Fanpage)", "callback_data": f"pub:{target_tab}:{row_id}:buffer1"}],
            [
                {"text": "🎬 Xem Video", "url": video_url or "https://drive.google.com"},
                {"text": "📊 Mở Sheet", "url": "https://docs.google.com/spreadsheets/d/1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0/edit"}
            ]
        ]
    }
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "reply_markup": markup}
    req = urllib.request.Request(f"https://api.telegram.org/bot{bot_token}/sendMessage", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode()).get("ok", False)
    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def handle_callback_query(bot_token: str, cb: Dict[str, Any]):
    """Handles inline button clicks to trigger immediate social dispatch."""
    cb_id = cb.get("id")
    data = cb.get("data", "")
    chat_id = cb.get("message", {}).get("chat", {}).get("id")

    # Acknowledge callback immediately
    ack_req = urllib.request.Request(f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery", data=json.dumps({"callback_query_id": cb_id, "text": "🚀 Đang tiến hành đăng bài..."}).encode(), headers={"Content-Type": "application/json"})
    urllib.request.urlopen(ack_req, timeout=5)

    if data.startswith("pub:"):
        parts = data.split(":")
        if len(parts) >= 4:
            _, tab, row_str, channels = parts[0], parts[1], parts[2], parts[3]
            row_id = int(row_str)
            try:
                res = publish_row_to_social(tab, row_id, channels=channels, dry_run=False)
                ch_list = ", ".join(res.get("channels", []))
                confirm_msg = f"🎉 <b>ĐÃ ĐĂNG THÀNH CÔNG!</b>\n\n📌 Tab: <code>{tab}</code> | Dòng: #{row_id}\n🌐 Các kênh đã đẩy: {ch_list}\n📊 Trạng thái Sheet: <b>Published</b>"
            except Exception as ex:
                confirm_msg = f"❌ <b>Lỗi khi đăng bài:</b> {ex}"

            send_req = urllib.request.Request(f"https://api.telegram.org/bot{bot_token}/sendMessage", data=json.dumps({"chat_id": chat_id, "text": confirm_msg, "parse_mode": "HTML"}).encode(), headers={"Content-Type": "application/json"})
            urllib.request.urlopen(send_req, timeout=10)


def start_polling():
    """Runs lightweight long-polling listener for interactive Telegram buttons."""
    bot_token, _ = load_telegram_creds()
    if not bot_token:
        print("❌ Cannot start Telegram polling: Missing token.")
        return
    offset = 0
    print("🤖 [Telegram Interactive Bot] Polling listener active. Listening for 1-Click publish buttons...")
    while True:
        try:
            url = f"https://api.telegram.org/bot{bot_token}/getUpdates?offset={offset}&timeout=20"
            with urllib.request.urlopen(url, timeout=25) as r:
                updates = json.loads(r.read().decode()).get("result", [])
                for u in updates:
                    offset = max(offset, u["update_id"] + 1)
                    if "callback_query" in u:
                        handle_callback_query(bot_token, u["callback_query"])
                    elif "message" in u and "text" in u["message"]:
                        text = u["message"]["text"].strip()
                        if text.startswith("/preview"):
                            p = text.split()
                            send_review_post(p[1] if len(p) > 1 else "pinyin", int(p[2]) if len(p) > 2 else 16)
                        elif text.startswith("/publish"):
                            p = text.split()
                            publish_row_to_social(p[1] if len(p) > 1 else "pinyin", int(p[2]) if len(p) > 2 else 16, channels=p[3] if len(p) > 3 else "buffer1", dry_run=False)
        except Exception:
            time.sleep(2)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        send_review_post(sys.argv[2] if len(sys.argv) > 2 else "pinyin", int(sys.argv[3]) if len(sys.argv) > 3 else 16)
    else:
        start_polling()

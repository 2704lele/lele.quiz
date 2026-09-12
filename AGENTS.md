# 🏛️ AGENT OPERATIONAL CONSTITUTION: LELE CHINESE QUIZ AUTOMATION

> **Căn cứ pháp lý & Chuẩn kiến trúc:** `/home/vpsg16gb/Documents/Structure/` (`00_TONG_QUAN.md` đến `10_AUTONOMOUS_ORCHESTRATION_HERMES_AGY_SPECIFICATION.md`).  
> **Phạm vi áp dụng:** Toàn bộ AI Agents (Antigravity, Claude, Hermes/Emma, Cursor, Codex), Subagents và Kỹ sư điều hành tại `/media/vpsg16gb/Media/lelehoctiengtrung/quiz`.  
> **Nguyên tắc bất biến:** Single Source of Truth • Zero-Leak Credentials • Zero-VPS Compute • Strict 21px Row Height • exFAT Bytecode Hygiene.

---

## 📜 I. 10 ĐIỀU KHOẢN HIẾN PHÁP BẮT BUỘC (SUPREME OPERATING ARTICLES)

### Điều 1: Kỹ Nghệ AI Có Khuôn Khổ (Constrained AI Engineering - Doc 01)
- **Định mức tệp tin:** Mọi tệp tin logic nghiệp vụ, kịch bản điều khiển và tiện ích bắt buộc phải tuân thủ định mức $\le 150$ dòng/tệp (trừ các file bảng biểu/từ điển cấu trúc hoặc test suite toàn diện).
- **Bảo toàn mã nguồn:** Tuyệt đối không tự ý xóa bỏ, rút gọn hoặc viết lại các hàm, biến, comments hoặc logic cũ khi chưa được người dùng xác nhận rõ ràng.
- **Tự phục hồi (Self-Healing):** Mọi thao tác I/O mạng (Google Sheets API, Google Drive API, Colab RPC, Buffer API, Telegram Bot) bắt buộc phải bọc trong khối `try-catch` an toàn và thiết lập cơ chế **Retry tối thiểu 3 lần** kèm exponential backoff.
- **Phát triển Hướng Kiểm Thử (TDD):** Bắt buộc viết hoặc cập nhật Unit Test trước khi triển khai tính năng mới. Mọi thay đổi phải vượt qua 100% Pytest suite trước khi nghiệm thu.

### Điều 2: Không Rò Rỉ Bí Mật (Zero-Leak Credentials & Storage Vault - Doc 03)
- **Cấm Tuyệt Đối Plaintext Secrets:** Không lưu trữ các tệp `.env`, `service_account.json`, `token.json`, `client_secret.json`, `cookies.txt` tại thư mục gốc của dự án hoặc commit vào git.
- **Vị trí lưu trữ Profile Vault:** Toàn bộ thông tin đăng nhập, Service Account GCP, OAuth tokens, Buffer tokens, Telegram credentials phải được đặt tại:
  `~/.cloud-profiles/lelehoctiengtrung/` với phân quyền an toàn nghiêm ngặt:
  - Thư mục: `chmod 700`
  - Tệp cấu hình / secrets: `chmod 600`
- **Môi trường Container / MicroVM / GHA:** Chỉ gắn (mount) thư mục secrets vào container ở chế độ Read-Only (`:ro`) hoặc giải mã vào bộ nhớ RAM tạm `tmpfs /dev/shm` và GitHub Actions Secrets.

### Điều 3: Không Gánh Tải VPS (Zero-VPS Compute Architecture - Doc 02)
- **0% Tải Render:** Máy chủ VPS `vpsg16gb` chỉ đóng vai trò Orchestrator (điều phối RPC, kiểm duyệt ngôn ngữ Gatekeeper 1 nhẹ nhàng và cập nhật bảng tính).
- **100% Cloud Compute:** Toàn bộ tác vụ render video Manim 1080x1920 60fps nặng nề và tổng hợp âm thanh Edge-TTS phải chạy hoàn toàn trên đám mây:
  - **Kênh Chính (Default):** GitHub Actions Runner Cloud (Ubuntu-latest).
  - **Kênh Dự Phòng (Fallback):** Google Colab Cloud VM (GPU Nvidia T4 hoặc High-Speed CPU VM qua pool `gmail_1` đến `gmail_5`).

### Điều 4: Xử Lý Dứt Điểm (Batch Continuity Engine - Doc 07)
- Khi một quy trình render khởi động, phiên làm việc đó phải xử lý liên hoàn **TOÀN BỘ** các dòng có trạng thái `Pending` trên cả 4 tabs (`pinyin`, `vocabCN`, `vocabVN`, `multilevels`).
- Quá trình chỉ dừng lại khi không còn bất kỳ dòng `Pending` nào (`Pending count == 0`).

### Điều 5: Nguyên Tắc Ngắt Nghỉ 30 Phút & Timeout Treo 80 Phút (Cooldown & Hang Protection)
- **Strict 30-Minute Cooldown (1800s):** Một tài khoản Colab tuyệt đối không được sử dụng lại trong vòng 30 phút (1800 giây) kể từ lần chạy trước.
- **Strict 80-Minute Hang Protection (4800s):** Bất kỳ session Colab nào chạy vượt quá 4800s sẽ bị Auto-Healing Engine tự động phát hiện, cưỡng chế hủy (`colab stop -s <session_id>`) và giải phóng tài nguyên.

### Điều 6: Thử Lại 3 Lần & Fallback CPU Bắt Buộc (3-Retry & Immediate CPU Fallback - Doc 06)
- Mỗi tài khoản Colab chỉ được phép thử kết nối / cấp phát tối đa **3 lần**.
- GPU (Nvidia T4) là tùy chọn, không bắt buộc. Khi khởi tạo: ưu tiên GPU T4; nếu GPU bận hoặc hết quota, fallback ngay sang High-Speed CPU VM.

### Điều 7: Khóa Cứng Định Danh & Danh Sách Đen Vĩnh Viễn (Strict Identity Binding - Doc 06)
- **Email bị cấm vĩnh viễn:** Tài khoản `aleron.dt@gmail.com` bị cấm tuyệt đối khỏi việc sử dụng làm Colab Runner.
- **Pool Colab hợp lệ:** Chỉ sử dụng 5 tài khoản Gmail đã đăng ký trong `~/.config/colab_profiles/` (`gmail_1` đến `gmail_5`).

### Điều 8: Cách Ly Telegram Bot & Buffer Social (Strict Channel Isolation - Doc 03 & 09)
- Telegram Bot Token & Chat ID dành riêng:
  - Cấu hình: `~/.cloud-profiles/lelehoctiengtrung/telegram/telegram.env` (`chmod 600`)
  - Chat ID: `1187577977`
- Buffer Social API sử dụng token riêng tại `~/.cloud-profiles/lelehoctiengtrung/buffer/credentials.json` trỏ đúng 3 channels: YouTube Shorts (`6a83dda0ccaf649a67c8cb92`), TikTok (`6a83dc5bccaf649a67c8b30f`), Facebook Fanpage (`6a871331ccaf649a67e1b724`).

### Điều 9: Bất Biến Chiều Cao Hàng 21px & 16 Cột Chuẩn (Google Sheets Invariants - Doc 04 & 05)
- **Bất biến Định danh:** `Batch ID (#) == Số dòng vật lý trên Sheet`.
- **Cấu trúc 16 cột chuẩn:**
  `A (ID) | B (Topic) | C (Level) | D (Status) | E:I (Word 1..5) | J (Drive Folder) | K (Video Streamable URL) | L:N (Social Metadata) | O (Social Status) | P (Notes)`.
- **Khóa chặt chiều cao hàng:** Mọi dòng dữ liệu trên cả 4 tabs (`pinyin`, `vocabCN`, `vocabVN`, `multilevels`) phải luôn duy trì chính xác độ cao **21 px** thông qua `scripts/enforce_row_height_21px.py`.

### Điều 10: Vệ Sinh Phân Vùng exFAT & Đồng Bộ / Sao Lưu GDrive (Doc 08)
- Phân vùng `/media/vpsg16gb/Media/` là định dạng exFAT (`/dev/sdc1`):
  - Virtualenv **bắt buộc** đặt trên ext4 tại `/home/vpsg16gb/.venvs/lele_quiz`.
  - Nghiêm cấm tạo `.pyc`, `__pycache__` trên exFAT (`PYTHONDONTWRITEBYTECODE=1`).
- Mọi thay đổi mã nguồn trên VPS được đồng bộ lên Google Drive `00.codebases` (`1C-n3Un-D6Teu4LapgIWWeVZ6l7toH8lm`) và backup version history lên `Backups` (`1QHYaOfvE8yoShR4UcM0o3zd0uOh7rhaK`).

---

## 🗂️ II. BẢN ĐỒ LƯU TRỮ GOOGLE DRIVE (SINGLE SOURCE OF TRUTH)

| Phân Vùng / Tab | Thư Mục Đích | Google Drive Folder ID | Mục Đích |
|---|---|---|---|
| **Codebases** | `00.codebases` | `1C-n3Un-D6Teu4LapgIWWeVZ6l7toH8lm` | Lưu trữ các bản zip mã nguồn sạch từ VPS |
| **Backups** | `Backups` | `1QHYaOfvE8yoShR4UcM0o3zd0uOh7rhaK` | Snapshot version history Google Sheets & config |
| **Tab 1: Pinyin** | `01.pinyinquiz` | `1f2mFUgpz_pYn3y9HqeHyOG9DzPMVH9QY` | Video trắc nghiệm Pinyin từ Hán tự (HSK 1-6) |
| **Tab 2: VocabCN** | `02.vocabCNquiz` | `1eI7I4jQqGBjD7MC_NXJ4zwFANxrcZM1E` | Video trắc nghiệm Nghĩa tiếng Việt từ Hán tự |
| **Tab 3: VocabVN** | `03.vocabVNquiz` | `1VPqs9h4LLmmmXWKDGWoAz1fUCylVLK2H` | Video trắc nghiệm Hán tự từ Nghĩa tiếng Việt |
| **Tab 4: Multilevels** | `04.multilevelsquiz` | `17xOkiW-XOWRDK2CCwNEl_rlf1rGKqKXm` | Video 1 nghĩa cốt lõi xuyên suốt 5 cấp độ HSK |

---

## ⏰ III. KIẾN TRÚC 3 CỘT MỐC TỰ ĐỘNG HÓA CLOUDFLARE CRON (ZERO-GITHUB CRON)

Toàn bộ lịch trình tự động được kích hoạt **duy nhất** từ **Cloudflare Workers Cron Triggers** (không dùng GitHub Action scheduled cron):

1. **00:01 AM GMT+7 (17:01 UTC) - Ideation & Scripting:**
   - Cron trigger: `1 17 * * *`
   - Kích hoạt: `01_quiz_ideation_and_scripting.yml` (hoặc `./quick_idea.sh all 5`)
   - Sản lượng: 20 dòng mới (5 dòng x 4 tabs `pinyin`, `vocabCN`, `vocabVN`, `multilevels`).
   - Động cơ AI: Multi-Provider AI Rotator:
     - 6 Google AI Studio Keys (`gemini-3.6-flash`, `gemini-3.7-flash`).
     - 4 Agnes AI Keys (`https://apihub.agnes-ai.com/v1`, `agnes-2.0-flash`, `gpt-4o-mini`).
     - Tự động xoay vòng khi chạm rate-limit (HTTP 429) và chuyển tầng an toàn.
   - Kiểm định Gatekeeper 1: Kiểm duyệt Hán tự, Pinyin chuẩn thanh điệu, chống trùng lặp từ vựng 100%. Đặt trạng thái `Pending` và khóa 21px.

2. **03:01 AM GMT+7 (20:01 UTC) - Cloud Video Rendering & Gatekeeper 2:**
   - Cron trigger: `1 20 * * *`
   - Kích hoạt: `02_quiz_video_rendering_and_qc.yml` (hoặc `./quick_render.sh all`)
   - Xử lý liên hoàn: Quét và render toàn bộ các dòng `Pending` còn lại.
   - Kiểm định Gatekeeper 2: Đảm bảo độ phân giải 1080x1920 60fps, audio sync, tải lên đúng thư mục Drive, cập nhật Cột K và chuyển sang `Ready` (khóa 21px).

3. **05:01 AM GMT+7 (22:01 UTC) - Morning Audit & Verification:**
   - Cron trigger: `1 22 * * *`
   - Kích hoạt: `03_quiz_morning_audit.yml` (hoặc `python3 scripts/run_morning_audit.py`)
   - Nhiệm vụ:
     - Kiểm toán 20/20 video đã đạt trạng thái `Ready`.
     - Xác minh HTTP 200 cho toàn bộ link Google Drive ở Cột K.
     - Cưỡng chế bất biến chiều cao dòng 21px trên cả 4 tabs.
     - Gửi báo cáo tổng hợp buổi sáng lên Telegram cho anh Hoàng.

4. **Social Media Distribution (Thao tác Thủ công / Kích hoạt Theo Yêu Cầu):**
   - Kích hoạt: `04_quiz_social_distribution.yml` (hoặc `python3 scripts/run_publish_dispatcher.py`)
   - Kiểm định Gatekeeper 3:
     - **Chống đăng trùng (Anti-Duplicate):** Bỏ qua các hàng đã có trạng thái `Published`.
     - **Chống lặp (Anti-Repeat):** Không xuất bản lại vào các kênh đã ghi nhận `Scheduled`.
     - **Chống thiếu (Anti-Missing):** Chỉ xuất bản các hàng có trạng thái `Ready` và link Drive hợp lệ. Lên lịch đồng thời cả 3 nền tảng (Shorts, TikTok, Fanpage) với khoảng cách giãn cách 30 phút giữa các video.

---

## 🤖 IV. HUẤN LUYỆN HERMES EMMA: DUAL-PATH EXECUTION GUIDE

Hermes Emma trên `vpsg16gb` được trao quyền điều phối kép:

### Kênh 1 (Default Path) - GitHub Actions Dispatch:
Emma sử dụng GitHub Actions API để kích hoạt runner trên đám mây:
```bash
# 1. Kích hoạt Ideation 5 dòng mỗi tab:
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/nwtuanhoang-coder/lele-quiz-automation/actions/workflows/01_quiz_ideation_and_scripting.yml/dispatches \
  -d '{"ref":"main","inputs":{"tab":"all","batch_count":"5"}}'

# 2. Kích hoạt Render toàn bộ dòng Pending:
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/nwtuanhoang-coder/lele-quiz-automation/actions/workflows/02_quiz_video_rendering_and_qc.yml/dispatches \
  -d '{"ref":"main","inputs":{"tab":"all","mode":"all_pending","quality":"qh"}}'

# 3. Kích hoạt Kiểm toán buổi sáng:
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/nwtuanhoang-coder/lele-quiz-automation/actions/workflows/03_quiz_morning_audit.yml/dispatches \
  -d '{"ref":"main"}'

# 4. Kích hoạt Xuất bản Mạng Xã Hội (GK3):
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/nwtuanhoang-coder/lele-quiz-automation/actions/workflows/04_quiz_social_distribution.yml/dispatches \
  -d '{"ref":"main","inputs":{"tab":"all","channels":"buffer1","delay_minutes":"30"}}'
```

### Kênh 2 (Fallback Path) - Colab CLI & Local Scripts trên `vpsg16gb`:
Khi mạng GitHub gián đoạn hoặc cần render nhanh cục bộ qua Colab:
```bash
cd /media/vpsg16gb/Media/lelehoctiengtrung/quiz
source env.sh

# Sinh kịch bản qua Multi-Provider AI Rotator:
python3 scripts/run_ideation_dispatcher.py --tab all --count 5

# Render video qua Colab Cloud VM Pool (Zero VPS Compute):
./quick_render.sh all

# Kiểm toán chất lượng & báo cáo Telegram:
python3 scripts/run_morning_audit.py

# Xuất bản mạng xã hội với chốt chặn Gatekeeper 3:
python3 scripts/run_publish_dispatcher.py --tab all --channels buffer1 --delay 30
```

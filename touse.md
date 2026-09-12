# 🏮 CẨM NANG ĐIỀU HÀNH HỆ THỐNG LELE CHINESE QUIZ AUTOMATION

Tài liệu hướng dẫn sử dụng nhanh, tra cứu toàn bộ **Bảng Điều Khiển (Boards)** và **Tập Lệnh Python (`.py`)** để vận hành, giám sát In-View, tạo idea, đăng dòng idea thủ công và điều phối render Manim 60fps trên **Google Colab Cloud GPU T4** cho cả 4 sub-pipelines:
- **`pinyinquiz`** (Tab `pinyin`): Hanzi ➔ Đoán Pinyin
- **`vocabCNquiz`** (Tab `vocabCN`): Hanzi ➔ Đoán Nghĩa Tiếng Việt
- **`vocabVNquiz`** (Tab `vocabVN`): Nghĩa Tiếng Việt ➔ Đoán Hanzi
- **`multilevelsquiz`** (Tab `multilevels`): 1 Nghĩa ➔ 5 Cấp độ HSK (30s Video ngắn 9:16)

---

## ⚡ 1. CÁCH DỄ NHẤT: MENU ĐIỀU HÀNH 1-CLICK (KHUYÊN DÙNG)

Bạn **không cần nhớ bất kỳ câu lệnh phức tạp nào**, chỉ cần mở Menu và bấm các phím số `1`, `2`, `3`...:

```bash
cd /media/vpsg16gb/Media/lelehoctiengtrung/quiz

./menu.sh
# Hoặc: python3 menu.py
```

### 🖥️ Màn hình Menu Điều Hành:
```text
===================================================================
🏮 LELE CHINESE QUIZ — MENU ĐIỀU HÀNH NHANH (1-CLICK COMMANDS)
===================================================================
  [1] 📊 Xem bảng trạng thái nhanh 4 Pipelines (In-View Status)
  [2] 💡 Tự động sinh Idea mới (Auto Ideation Batch)
  [3] 📝 Đăng nhanh 1 dòng Idea thủ công (Kèm Gatekeeper kiểm duyệt)
  [4] 🎬 Kích hoạt Render Manim (Google Colab GPU T4 — Zero VPS)
  [5] 🚀 Đăng Video dòng số X lên Mạng Xã Hội (Buffer 1: Shorts/TikTok/Fanpage)
  [6] 🔍 Kích hoạt QC kiểm tra Video (Google Colab Auto-QC)
  [7] 🔄 Đặt lại trạng thái dòng thành Pending (Re-render)
  [8] 🌐 Xem cấu hình 3 kênh Video & Buffer 1 Vault (In-View Social)
  [9] 🧪 Chạy bộ kiểm thử hệ thống (pytest)
  [c] ⚡ Quản lý Google Colab CLI Pool (Xem tài khoản, phiên, giải phóng VM)
  [0] ❌ Thoát
-------------------------------------------------------------------
👉 Nhập số lựa chọn của bạn [0-9, c]:
```

---

## 📂 2. DANH MỤC CÁC CÔNG CỤ & TẬP LỆNH CHÍNH (FILE DIRECTORY)

### 📊 Nhóm 1: Bảng Điều Khiển & Giám Sát (Dashboards & Monitors)
| Tên File | Chức Năng & Mục Đích | Cách Chạy |
|---|---|---|
| **[`menu.py`](file:///media/vpsg16gb/Media/lelehoctiengtrung/quiz/menu.py)** / **[`menu.sh`](file:///media/vpsg16gb/Media/lelehoctiengtrung/quiz/menu.sh)** | **Trình Điều Hành 1-Click** — Menu tương tác số hoá giúp vận hành toàn bộ hệ thống quiz không cần gõ lệnh dài. | `./menu.sh` |
| **[`monitor.py`](file:///media/vpsg16gb/Media/lelehoctiengtrung/quiz/monitor.py)** | **In-View Visual Pipeline Monitor** — Bảng giám sát đồ họa thời gian thực 4 nodes, xem số lượng video theo từng trạng thái, kiểm tra 3 kênh Video Mạng Xã Hội (Buffer 1: YouTube Shorts, TikTok, Facebook Reels) và kiểm tra ràng buộc schema. | `python3 monitor.py --status`<br>`python3 monitor.py --social`<br>`python3 monitor.py --no-clear`<br>`python3 monitor.py --inview 5` |
| **[`control_tui.py`](file:///media/vpsg16gb/Media/lelehoctiengtrung/quiz/control_tui.py)** | **Full Textual Terminal Control Center** — Bảng điều khiển TUI đa tab toàn màn hình (Monitor bảng tính, Auto Idea, Form nhập 5 từ thủ công có nút Live Gatekeeper 1). | `python3 control_tui.py` |

---

### 🚀 Nhóm 2: Trình Sinh Idea Tự Động & Kiểm Duyệt Gatekeeper 1 (Ideation Generators)
| Tên File | Chức Năng & Mục Đích | Cách Chạy |
|---|---|---|
| **[`scripts/generate_daily_batches.py`](file:///media/vpsg16gb/Media/lelehoctiengtrung/quiz/scripts/generate_daily_batches.py)** | **Root Unified Batch Generator** — Trình sinh idea gốc gom cả 4 pipelines (`pinyin`, `vocabcn`, `vocabvn`, `multilevels` hoặc `all`), xoay vòng 6 Gemini keys và lọc từ cũ. | `./quick_idea.sh all 1`<br>`python3 scripts/generate_daily_batches.py --pipeline all --count 1` |
| **[`pinyinquiz/scripts/generate_daily_batches.py`](file:///media/vpsg16gb/Media/lelehoctiengtrung/quiz/pinyinquiz/scripts/generate_daily_batches.py)** | Trình sinh idea độc lập cho riêng `pinyinquiz` (Hanzi ➔ Pinyin). | `python3 pinyinquiz/scripts/generate_daily_batches.py --count 1` |
| **[`vocabCNquiz/scripts/generate_daily_batches.py`](file:///media/vpsg16gb/Media/lelehoctiengtrung/quiz/vocabCNquiz/scripts/generate_daily_batches.py)** | Trình sinh idea độc lập cho riêng `vocabCNquiz` (Hanzi ➔ Nghĩa TV). | `python3 vocabCNquiz/scripts/generate_daily_batches.py --count 1` |
| **[`vocabVNquiz/scripts/generate_daily_batches.py`](file:///media/vpsg16gb/Media/lelehoctiengtrung/quiz/vocabVNquiz/scripts/generate_daily_batches.py)** | Trình sinh idea độc lập cho riêng `vocabVNquiz` (Nghĩa TV ➔ Hanzi). | `python3 vocabVNquiz/scripts/generate_daily_batches.py --count 1` |
| **[`multilevelsquiz/scripts/generate_daily_batches.py`](file:///media/vpsg16gb/Media/lelehoctiengtrung/quiz/multilevelsquiz/scripts/generate_daily_batches.py)** | Trình sinh idea độc lập cho riêng `multilevelsquiz` (1 Nghĩa ➔ 5 Cấp HSK). | `python3 multilevelsquiz/scripts/generate_daily_batches.py --count 1` |

---

### 🎬 Nhóm 3: Trình Thực Thi Batch & Kích Hoạt Render Trên Google Colab CLI (Cloud Compute)
| Tên File | Chức Năng & Mục Đích | Cách Chạy |
|---|---|---|
| **[`quick_render.sh`](file:///media/vpsg16gb/Media/lelehoctiengtrung/quiz/quick_render.sh)** | **Lệnh tắt kích hoạt Render** — Hỗ trợ render sạch TOÀN BỘ dòng Pending trên 4 tabs (`all`) hoặc render 1 dòng cụ thể. Tự động thử GPU T4 và fallback CPU siêu tốc. | `./quick_render.sh all`<br>`./quick_render.sh pinyin 24`<br>`./quick_render.sh multilevels 2` |
| **[`scripts/colab_render_cli.py`](file:///media/vpsg16gb/Media/lelehoctiengtrung/quiz/scripts/colab_render_cli.py)** | **CLI Dispatcher chuyên dụng** — Điều phối job sang Colab VM. Hỗ trợ Batch Continuity (`--pipeline all`), kiểm tra hàng chờ (`--pending`), xem trạng thái nghỉ 30 phút (`--status`), ép chạy CPU (`--cpu`). | `python3 scripts/colab_render_cli.py --pipeline all`<br>`python3 scripts/colab_render_cli.py --pending`<br>`python3 scripts/colab_render_cli.py --status`<br>`python3 scripts/colab_render_cli.py --pipeline pinyin --row 24` |
| **[`scripts/colab_auto_render_daemon.py`](file:///media/vpsg16gb/Media/lelehoctiengtrung/quiz/scripts/colab_auto_render_daemon.py)** | **Daemon Tự Động Quét Sheet** — Quét định kỳ cả 4 tab Google Sheet; khi có dòng `Pending`, tự động mount 1 Colab VM và render dứt điểm toàn bộ trước khi ngắt phiên. | `python3 scripts/colab_auto_render_daemon.py --once`<br>`python3 scripts/colab_auto_render_daemon.py --interval 300` |
| **[`scripts/enforce_row_height_21px.py`](file:///media/vpsg16gb/Media/lelehoctiengtrung/quiz/scripts/enforce_row_height_21px.py)** | **Khóa Chặt Độ Cao Hàng 21px** — Quét toàn bộ các hàng trên cả 4 tabs Google Sheets và cưỡng chế đặt pixelSize = 21px chuẩn tuyệt đối. | `python3 scripts/enforce_row_height_21px.py` |
| **[`scripts/colab_auth_pool.py`](file:///media/vpsg16gb/Media/lelehoctiengtrung/quiz/scripts/colab_auth_pool.py)** | **Quản Trị Pool Tài Khoản Colab** — Thêm tài khoản Gmail mới vào pool qua mã xác thực OAuth2, tự động chặn `aleron.dt@gmail.com`. | `python3 scripts/colab_auth_pool.py add <alias>`<br>`python3 scripts/colab_auth_pool.py list` |
| **[`colab/colab_orchestrator.py`](file:///media/vpsg16gb/Media/lelehoctiengtrung/quiz/colab/colab_orchestrator.py)** | **Master Orchestrator Engine** — Quản lý vòng đời session, retry tối đa 3 lần, tự động fallback CPU, kiểm soát thời gian nghỉ 30 phút (1800s) cho từng email. | Dùng như thư viện Python |
| **[`colab/colab_worker_quiz.py`](file:///media/vpsg16gb/Media/lelehoctiengtrung/quiz/colab/colab_worker_quiz.py)** | **In-VM Remote Worker** — Script tự động bootstrap hệ thống font chữ Hán, dependencies và thực thi Manim liên hoàn trực tiếp trong Colab VM. | Chạy tự động trên Colab VM |

---

### 🔍 Nhóm 4: Công Cụ Kiểm Tra Chất Lượng & Dọn Dẹp (QC & Audit Tools)
| Tên File | Chức Năng & Mục Đích | Cách Chạy |
|---|---|---|
| **[`pinyinquiz/scripts/run_qc.py`](file:///media/vpsg16gb/Media/lelehoctiengtrung/quiz/pinyinquiz/scripts/run_qc.py)** | Chạy kiểm định chất lượng video và link Google Drive cho `pinyinquiz`. | `python3 pinyinquiz/scripts/run_qc.py --id 24` |
| **[`vocabCNquiz/scripts/run_qc.py`](file:///media/vpsg16gb/Media/lelehoctiengtrung/quiz/vocabCNquiz/scripts/run_qc.py)** | Chạy kiểm định chất lượng video và link Google Drive cho `vocabCNquiz`. | `python3 vocabCNquiz/scripts/run_qc.py --id 10` |
| **[`vocabVNquiz/scripts/run_qc.py`](file:///media/vpsg16gb/Media/lelehoctiengtrung/quiz/vocabVNquiz/scripts/run_qc.py)** | Chạy kiểm định chất lượng video và link Google Drive cho `vocabVNquiz`. | `python3 vocabVNquiz/scripts/run_qc.py --id 5` |
| **[`multilevelsquiz/scripts/run_qc.py`](file:///media/vpsg16gb/Media/lelehoctiengtrung/quiz/multilevelsquiz/scripts/run_qc.py)** | Chạy kiểm định chất lượng video và link Google Drive cho `multilevelsquiz`. | `python3 multilevelsquiz/scripts/run_qc.py --id 2` |
| **[`vocabCNquiz/scripts/audit_and_cleanup_sheet.py`](file:///media/vpsg16gb/Media/lelehoctiengtrung/quiz/vocabCNquiz/scripts/audit_and_cleanup_sheet.py)** | Tự động kiểm toán, chuẩn hóa cột và làm sạch dữ liệu bảng tính `vocabCN`. | `python3 vocabCNquiz/scripts/audit_and_cleanup_sheet.py` |

---

## 🚀 3. TỔNG HỢP CÁC LỆNH TẮT 1 DÒNG (ONE-LINERS)

| Nhu Cầu Điều Hành | Lệnh Chạy Nhanh |
|---|---|
| **Mở Menu tương tác 1-Click** | `./menu.sh` |
| **Xem bảng trạng thái Google Sheets** | `python3 monitor.py --status` |
| **Xem danh sách hàng Pending cả 4 tabs** | `python3 scripts/colab_render_cli.py --pending` |
| **Xem trạng thái Pool tài khoản & Cooldown 30p** | `python3 scripts/colab_render_cli.py --status` |
| **Render sạch TOÀN BỘ hàng Pending cả 4 tabs** | `./quick_render.sh all` |
| **Render video dòng 24 trên Colab** | `./quick_render.sh pinyin 24` |
| **Khóa chặt độ cao hàng 21px cả 4 tabs** | `python3 scripts/enforce_row_height_21px.py` |
| **Quét & tự động render các hàng Pending (1 lần)** | `python3 scripts/colab_auto_render_daemon.py --once` |
| **Chạy daemon tự động quét Sheet mỗi 5 phút** | `python3 scripts/colab_auto_render_daemon.py --interval 300` |
| **Đăng Mạng Xã Hội dòng số 24 (tab pinyin)** | `./quick_publish.sh pinyin 24 all` |
| **Xem 3 kênh Video MXH (Buffer 1) & Vault** | `python3 monitor.py --social` |
| **Giám sát đồ họa 4 nodes In-View** | `python3 monitor.py --no-clear` |
| **Giám sát liên tục mỗi 5s** | `python3 monitor.py --inview 5` |
| **Kiểm tra tính toàn vẹn 16 cột** | `python3 monitor.py --verify-tab all` |
| **Tạo 1 batch mới cho cả 4 pipelines** | `./quick_idea.sh all 1` |
| **Tạo 1 batch thử nghiệm (dry-run)** | `python3 scripts/generate_daily_batches.py --pipeline all --dry-run --count 1` |
| **Chạy toàn bộ bộ kiểm thử hệ thống** | `python3 -m pytest tests/ -v` |

---

## ⚡ 4. QUẢN LÝ TÀI KHOẢN GOOGLE COLAB CLI (ACCOUNT POOL)

Hệ thống hỗ trợ cơ chế đa tài khoản Gmail để xoay vòng hạn ngạch GPU T4 / CPU:
- **Nguyên tắc ngắt nghỉ 30 phút (1800s):** Bất kể thành công hay thất bại/hết lượt retry, mỗi email sẽ được đưa vào chế độ nghỉ 30 phút trước khi được sử dụng lại.
- **Retry tối đa 3 lần:** Khi kết nối, mỗi tài khoản thử tối đa 3 lần. Ưu tiên GPU T4, nếu lỗi/quota tự động fallback CPU tốc độ cao ngay lập tức.
- **Batch Continuity:** Khi đã mount thành công 1 tài khoản, phiên Colab VM đó được giữ ấm để render liên hoàn toàn bộ hàng `Pending` cho đến khi không còn hàng nào mới ngắt phiên.
- Thư mục lưu trữ profile: `~/.config/colab_profiles/<alias>`
- Kiểm tra danh sách tài khoản:
  ```bash
  python3 scripts/colab_render_cli.py --status
  ```
- **Chính sách bảo mật nghiêm ngặt:** Email `aleron.dt@gmail.com` đã được đưa vào blacklist vĩnh viễn và bị chặn toàn diện trên hệ thống.
- Thêm tài khoản mới vào pool:
  ```bash
  python3 scripts/colab_auth_pool.py add <alias>
  ```

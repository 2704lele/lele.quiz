# 📚 HƯỚNG DẪN QUY TRÌNH VẬN HÀNH PIPELINE 2.0
## Kênh "Lê Lê Học Tiếng Trung" (@lelehoctiengtrung)

> **Kiến trúc:** Zero-Secret & Multi-Tier AI Gatekeeper Serverless  
> **Phiên bản:** Pipeline 2.0 (Chạy tự động 100% 24/7)  
> **Cập nhật lần cuối:** 20/08/2026

---

## 🗺️ 1. TỔNG QUAN KIẾN TRÚC 3 TẦNG (HIGH-LEVEL ARCHITECTURE)

```text
[1. CLOUDFLARE WORKER MASTER ORCHESTRATOR] (24/7)
  ├── 00:01 GMT+7: Kích hoạt Workflow 1 với 6 Gemini Keys động
  ├── /api/receive-ideas: Tiếp nhận & Kiểm duyệt Gatekeeper 5 tiêu chí
  │     ├── Đạt ➔ Ghi vào Google Sheet (Pending) ➔ Kích hoạt Workflow 2
  │     └── Lỗi ➔ Tự động gọi Step 2 tạo lại (Tối đa 2 lần, lần 3 xóa dòng)
  ├── Telegram Webhook: Nhận tương tác Approve / Reset / Delete từ Admin
  └── 07:00, 13:00, 19:00: Xuất bản tự động video 'Ready' qua Buffer API
               │
               ▼
[2. GITHUB ACTIONS 3-WORKFLOWS RUNTIME ENGINE]
  ├── Workflow 1: ScriptNewIdeation.yml (Sinh ý tưởng + HSK 1-2-3 Diversity)
  ├── Workflow 2: Render.yml (Manim 1080x1920 60fps + 0.75s Cover Intro + GDrive)
  └── Workflow 3: ProductQC.yml (Kiểm tra vật lý OpenCV + Đổi trạng thái 'Ready')
               │
               ▼
[3. GOOGLE WORKSPACE & MẠNG XÃ HỘI]
  ├── Google Sheets: Quản lý Database 14 cột
  ├── Google Drive: Lưu trữ video MP4 chất lượng cao
  └── Buffer API ➔ YouTube Shorts, TikTok, Facebook Reels
```

---

## 📋 2. CẤU TRÚC 14 CỘT DATABASE GOOGLE SHEETS

| Cột | Tên Cột | Mô Tả Dữ Liệu | Ví Dụ / Giá Trị |
| :--- | :--- | :--- | :--- |
| **A** | `ID` | Mã định danh duy nhất của video | `1`, `2`, `3`... |
| **B** | `Topic` | Tên chủ đề kèm cấp độ HSK | `HSK 1 • Đồ Ăn & Thức Uống` |
| **C** | `Level` | Trình độ HSK | `HSK 1`, `HSK 2`, `HSK 3` (Xoay tua) |
| **D** | `Status` | Trạng thái vòng đời của video | `Pending` ➔ `Video` ➔ `Ready` ➔ `Published` *(hoặc `Error`)* |
| **E** | `Word_1` | Cặp từ vựng câu 1: `Chữ Hán: Pinyin` | `苹果: píngguǒ` |
| **F** | `Word_2` | Cặp từ vựng câu 2: `Chữ Hán: Pinyin` | `米饭: mǐfàn` |
| **G** | `Word_3` | Cặp từ vựng câu 3: `Chữ Hán: Pinyin` | `面包: miànbāo` |
| **H** | `Word_4` | Cặp từ vựng câu 4: `Chữ Hán: Pinyin` | `喝水: hēshuǐ` |
| **I** | `Word_5` | Cặp từ vựng câu 5: `Chữ Hán: Pinyin` | `吃饭: chīfàn` |
| **J** | `Metadata` | Tiêu đề, Caption, Hashtags YouTube/TikTok/FB | Định dạng text chuẩn SEO |
| **K** | `Video` | Đường link Google Drive xem trước video | `https://drive.google.com/file/d/...` |
| **L** | `YouTube` | Trạng thái đăng tải lên YouTube Shorts | `Published` *(hoặc link/error)* |
| **M** | `TikTok` | Trạng thái đăng tải lên TikTok | `Published` *(hoặc link/error)* |
| **N** | `Facebook` | Trạng thái đăng tải lên Facebook Reels | `Published` *(hoặc link/error)* |

---

## 🛡️ 3. LỚP LÁ CHẮN AI GATEKEEPER (5 TIÊU CHÍ BẮT BUỘC)

Trước khi bất kỳ ý tưởng nào được lưu vào Sheet, Gatekeeper trên Cloudflare Worker sẽ kiểm tra nghiêm ngặt:

1. **100% Tiếng Trung Giản Thể (Simplified Chinese):** Không lẫn chữ Phồn thể, chữ rác, ký tự lạ.
2. **Đồng Nhất Đơn Chủ Đề (Single Topic Consistency):** Cả 5 từ trong một batch phải thuộc đúng 1 chủ đề xác định (ví dụ: *Đồ ăn, Cảm xúc, Giao thông...*).
3. **Tiếng Việt Thuần Khiết (100% Pure Vietnamese):** Tên chủ đề không được chêm từ tiếng Anh (ví dụ: cấm `Topic Đồ Ăn`, phải là `Đồ Ăn`).
4. **Khớp Dấu Pinyin (Pinyin Tone Matching):** Số lượng âm tiết và thanh điệu Pinyin phải khớp tuyệt đối 1:1 với số lượng chữ Hán tương ứng.
5. **Chống Trùng Lặp Cặp Từ Tuyệt Đối (Zero Word Duplication):** 5 từ trong 1 batch không được trùng nhau và không được trùng với các từ trong 100 hàng gần nhất trên Sheet (Negative Context).

### Cơ Chế Xử Lý Lỗi Tự Động (Smart Retry & Fresh Topic Switch):
- **Lần 1 & 2:** Nếu phát hiện lỗi (Pinyin, Tiếng Anh, Chữ phồn thể...), Gatekeeper không lưu vào Sheet mà tự động kích hoạt **Step 2 (Single-Row Re-generation)** trên GitHub Actions để AI viết lại, kèm báo cáo chi tiết lý do lỗi về Telegram.
- **Nếu thất bại sau 2 lần sửa:** Hệ thống **TỰ ĐỘNG KÍCH HOẠT VIẾT CHỦ ĐỀ MỚI HOÀN TOÀN (Fresh Topic)** trên GitHub Actions để lấp đầy dòng đó và gửi thông báo Telegram rõ ràng. Tuyệt đối không im lặng, không bỏ trống và không dùng văn bản thô.

---

## ⚙️ 4. CHI TIẾT 3 GITHUB ACTIONS WORKFLOWS

### 🚀 Workflow 1: `ScriptNewIdeation.yml` (Sáng Tạo Nội Dung)
- **Tần suất chạy:** 00:01 GMT+7 hàng ngày (17:01 UTC hôm trước) do Cloudflare Worker dispatch tự động.
- **Nhiệm vụ:**
  - Lấy 100 dòng gần nhất từ Google Sheet làm **Negative Context**.
  - Sinh 5 kịch bản mới/ngày với cơ chế **Xoay tua cấp độ (HSK 1 ➔ HSK 2 ➔ HSK 3)**.
  - Áp dụng độ trễ an toàn (Delay 60s) giữa các lần gọi AI và xoay vòng 6 Google Gemini Keys.
  - Gửi kết quả về Webhook `/api/receive-ideas` trên Cloudflare Worker.

### 🎬 Workflow 2: `Render.yml` (Sản Xuất Video Manim 60fps)
- **Kích hoạt:** Tự động khi có dòng mới ở trạng thái `Pending` (hoặc chạy thủ công qua `workflow_dispatch`).
- **Nhiệm vụ:**
  - Tạo ảnh bìa High-CTR Thumbnail và nhúng **0.75s Cover Intro** tại `00:00:00` đầu video.
  - Chạy Manim Community Edition dựng video 9:16 chuẩn 1080x1920 60fps (`-qh`).
  - Sinh giọng đọc phát âm chuẩn Tiếng Trung bằng `edge-tts`.
  - Tải video lên Google Drive (Thư mục: `1Y240J5-oXA-UDm2IKvp7qCBVsRempbCB`).
  - Cập nhật trạng thái Sheet sang `Video` và tự động kích hoạt Workflow 3 (`ProductQC.yml`).

### 🔍 Workflow 3: `ProductQC.yml` (Auto-QC Kiểm Định Vật Lý)
- **Kích hoạt:** Tự động ngay sau khi Workflow 2 kết thúc thành công.
- **Nhiệm vụ:**
  - Dùng **OpenCV & FFprobe** phân tích từng khung hình của file video thực tế:
    - ✅ Độ sáng, tương phản của Cover Thumbnail tại frame `00:00`.
    - ✅ Đảm bảo luồng âm thanh không bị câm (No silent audio).
    - ✅ Thời lượng chuẩn Short-form (15s – 120s).
  - Nếu đạt 100% điểm kiểm định: Tự động chuyển trạng thái Sheet thành **`Ready`** để sẵn sàng phát hành.

---

## 🎭 3. CHIẾN THUẬT NỘI DUNG & ĐỒ THỊ CẢM XÚC 5 TỪ (REELS RETENTION)

Mỗi video được biên soạn theo "Đồ thị cảm xúc" tăng tiến để tối ưu hóa thời gian xem (Watch Time), tỷ lệ lặp lại (Loop Rate) và lượt lưu video (Save Rate):

1. **Từ 1 (Cực Dễ - Instant Hook):** Từ/cụm từ cực kỳ quen thuộc (ví dụ: *谢谢, 苹果, 咖啡, 喝水*) giúp người xem làm đúng ngay trong 1-2 giây đầu, tạo cảm giác tự tin xem tiếp.
2. **Từ 2 & 3 (Chuẩn Trình Độ - Core HSK):** Các từ vựng chủ đề phổ thông theo đúng cấp độ bài học.
3. **Từ 4 (Bẫy Âm Điệu / Biến Điệu ⚡):** Chứa bẫy thanh điệu (thanh 1 vs 4, thanh 2 vs 3, phân biệt *买 mǎi / 卖 mài*), biến điệu của *不 (bù/bú)*, *一 (yī/yí/yì)*, hoặc biến âm 2 thanh 3 đi liền nhau. Kích thích người xem khựng lại suy nghĩ kỹ. Trên video hiển thị biểu tượng `4/5 ⚡`.
4. **Từ 5 (Thử Thách Boss / Thành Ngữ Viral 🔥):** Cấp độ khó nhất trong bộ (âm c/z, x/sh, q/ch, *练习 vs 联系*) hoặc với HSK 3 là cụm từ 3-4 chữ viral phim ảnh / thành ngữ thông dụng. Kích thích người xem xem lại (Loop) hoặc nhấn "Lưu bài viết" (Save). Trên video hiển thị biểu tượng `5/5 🔥`.

---

## 📱 5. QUY TRÌNH PHÁT HÀNH TỰ ĐỘNG PHÂN TẦNG (BUFFER 3 KHUNG GIỜ)

Cloudflare Worker tự động quét và phân loại video `Ready` trên Google Sheet theo từng khung giờ chuyên biệt:

- ⏰ **07:00 GMT+7 (Combo HSK 1 - Khởi Động Ngày Mới):** Lọc video `Ready` cấp độ **HSK 1** (từ vựng quen thuộc, nhẹ nhàng).
- ⏰ **13:00 GMT+7 (Combo HSK 2 - Giờ Nghỉ Trưa Tỉnh Táo):** Lọc video `Ready` cấp độ **HSK 2** (tập trung bẫy âm điệu, phân biệt thanh điệu khó).
- ⏰ **19:00 GMT+7 (Combo HSK 3 - Thử Thách Giờ Vàng / Phim Ảnh):** Lọc video `Ready` cấp độ **HSK 3** (cụm từ hot trend, lời thoại phim, thành ngữ 4 chữ).
- **Cơ chế Fallback:** Nếu kho thiếu video đúng cấp độ của khung giờ đó, hệ thống tự động gắp video `Ready` kế tiếp để đảm bảo lịch phát hành không bao giờ bị gián đoạn.
- **Sau khi Buffer tiếp nhận thành công:** Trạng thái trên Sheet tự động chuyển thành **`Published`**.

---

## 🔔 6. KIỂM DUYỆT QUA TELEGRAM BOT

Mỗi khi một video render xong, Telegram Bot gửi thông báo kiểm duyệt kèm video preview:
- 🟢 **[Approve]**: Chuyển ngay thành `Ready` (Đăng tự động theo lịch Buffer).
- 🟡 **[Reset]**: Chuyển về `Pending` (Để render lại nếu muốn chỉnh sửa).
- 🔴 **[Delete]**: Xóa dòng khỏi Google Sheet.

---

## 🔒 7. NGUYÊN TẮC BẢO MẬT ZERO-SECRET
- **Không lưu cứng API Keys/Secrets trên GitHub Actions:** Toàn bộ API keys (Gemini, Agnes, Buffer, Service Account, Telegram) được lưu trữ an toàn trong Secret Bindings của Cloudflare Worker.
- Khi kích hoạt GitHub Action, Cloudflare Worker truyền parameters động dưới dạng Payload mã hóa dùng một lần (Ephemeral Payload) và được che mặt nạ log (`***`) trong suốt quá trình chạy.

---

## ⚡ 8. VẬN HÀNH 100% CLOUD SERVERLESS & CƠ CHẾ PHỤC HỒI QUOTA GEMINI
- **100% Serverless Cloud (Zero-VPS / Zero-Local):** Toàn bộ pipeline chạy khép kín giữa **Cloudflare Workers** (Orchestrator 24/7) và **GitHub Actions Runners** (Compute Engine), hoàn toàn không phụ thuộc vào bất kỳ máy chủ VPS hay máy tính cá nhân nào.
- **Cơ Chế Quota Recovery Cho 6 Gemini API Keys:**
  - Khi một key chạm giới hạn `429 (Rate Limit)`, hệ thống tự động xoay tua sang key tiếp theo trong bộ 6 keys.
  - **Nếu toàn bộ 6 keys đều chạm ngưỡng 429:** Hệ thống gửi ngay cảnh báo khẩn cấp về **Telegram**, tự động kích hoạt chu kỳ **Cooldown Recovery 60s** để hạn ngạch Google AI Studio phục hồi, sau đó tự động thử lại vòng xoay (tối đa 3 chu kỳ).
  - **Mục tiêu tối thượng:** Bắt buộc **MỖI NGÀY PHẢI SẢN XUẤT ĐỦ 5 DÒNG KỊCH BẢN MỚI** đạt chuẩn để luôn có kho gối đầu phát hành đều đặn 3 ca/ngày.

# 📚 TÀI LIỆU VẬN HÀNH PIPELINE 2.0

Chi tiết toàn bộ quy trình sản xuất, kiểm duyệt và xuất bản tự động của kênh **Lê Lê Học Tiếng Trung (@lelehoctiengtrung)** được trình bày chi tiết tại:

👉 **[PIPELINE_2.0_WORKFLOW.md](file:///media/vpsg16gb/HaRiDisk/CHANNELS/lelehoctiengtrung/pinyinquiz/docs/PIPELINE_2.0_WORKFLOW.md)**

### 📋 Tóm tắt các thành phần cốt lõi:
1. **Kiến trúc 3 tầng Serverless Zero-Secret:** Cloudflare Worker (Orchestrator 24/7) ➔ GitHub Actions (3 Workflows) ➔ Google Workspace & Buffer.
2. **Chiến thuật Đồ thị cảm xúc 5 từ (Reels Retention):** Từ 1 (Hook cực dễ) ➔ Từ 2,3 (Core HSK) ➔ Từ 4 (Bẫy âm điệu `4/5 ⚡`) ➔ Từ 5 (Thử thách Boss `5/5 🔥`).
3. **Phát hành tự động Buffer phân tầng 3 khung giờ:** 
   - `07:00 GMT+7`: Combo HSK 1 (Khởi động ngày mới)
   - `13:00 GMT+7`: Combo HSK 2 (Bẫy âm điệu tỉnh táo)
   - `19:00 GMT+7`: Combo HSK 3 (Thử thách giờ vàng / Phim ảnh / Viral)
4. **Schema 14 Cột Google Sheets Database:** Quản lý vòng đời trạng thái `Pending` ➔ `Video` ➔ `Ready` ➔ `Published`.
5. **Lớp kiểm duyệt độc lập AI Gatekeeper:** 5 tiêu chí ngôn ngữ khắt khe & quy tắc tự sửa lỗi / Strike 3.
6. **Chi tiết 3 GitHub Actions Workflows:** `ScriptNewIdeation.yml` (Sáng tạo), `Render.yml` (Manim 60fps), `ProductQC.yml` (Auto-QC OpenCV).
7. **Kiểm duyệt trực quan qua Telegram Bot:** Nút bấm tương tác Approve / Reset / Delete tức thì.
8. **Vận hành 100% Serverless Cloud & Cơ chế phục hồi Quota 6 Gemini Keys:** Cảnh báo Telegram khi dính 429 và tự động hồi phục đảm bảo đủ 5 dòng/ngày.

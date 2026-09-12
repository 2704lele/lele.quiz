# 🛡️ GATEKEEPERS ARCHITECTURE: LELE CHINESE QUIZ AUTOMATION SYSTEM

> **Tiêu chuẩn quy định:** `/home/vpsg16gb/Documents/Structure/04_PIPELINE_GATEKEEPER_DASHBOARD.md` & `06_SECURITY_AND_CODE_AUDITING_GUIDE.md`.  
> **Pipelines bảo vệ:**
> 1. `pinyinquiz` (Đoán Pinyin từ Chữ Hán, Sheet Tab: `pinyin`)
> 2. `vocabCNquiz` (Đoán Nghĩa Tiếng Việt từ Chữ Hán, Sheet Tab: `vocabCN`)
> 3. `vocabVNquiz` (Đoán Chữ Hán từ Nghĩa Tiếng Việt, Sheet Tab: `vocabVN`)
> 4. `multilevelsquiz` (1 Nghĩa Cốt Lõi ➔ 5 Cấp Độ HSK, Sheet Tab: `multilevels`)

---

## 🏛️ 5-TIER GATEKEEPER TOPOLOGY (GK0 – GK4)

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│              KHUNG 5 PHA GÁC CỔNG PHỔ QUÁT (UNIVERSAL 5 PHASES)              │
│                                                                             │
│  [GK0: Ingress & Quota Dispatcher] ➔ Colab Multi-Account Pool (3-Retry,     │
│                                      30m Cooldown, Fallback CPU, Blacklist)  │
│  [GK1: Raw Input QC (Linguistic)]  ➔ Gatekeeper 1 Pre-Render Defense        │
│  [GK2: Processing & Render QC]     ➔ Manim 1080x1920 60fps (Colab VM)       │
│  [GK3: Output Compliance & Drive]  ➔ GDrive Folder 1Y240J5..., Col K URLs    │
│  [GK4: Central Ledger & Invariants]➔ Google Sheets State DB (# == Row ID),   │
│                                      Strict 21px Row Height & Telegram Bot  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📑 DOMAIN IMPLEMENTATION MATRIX

| Pha Gác Cổng | `pinyinquiz` | `vocabCNquiz` | `vocabVNquiz` | `multilevelsquiz` |
| :--- | :--- | :--- | :--- | :--- |
| **GK0: Ingress & Quota Dispatcher** | • Colab Pool 5 tài khoản<br>• Tối đa 3 lần thử connect<br>• Fallback CPU tức thì<br>• Nghỉ Cooldown 30 phút<br>• Chặn `aleron.dt@gmail.com` | • Colab Pool 5 tài khoản<br>• Tối đa 3 lần thử connect<br>• Fallback CPU tức thì<br>• Nghỉ Cooldown 30 phút<br>• Chặn `aleron.dt@gmail.com` | • Colab Pool 5 tài khoản<br>• Tối đa 3 lần thử connect<br>• Fallback CPU tức thì<br>• Nghỉ Cooldown 30 phút<br>• Chặn `aleron.dt@gmail.com` | • Colab Pool 5 tài khoản<br>• Tối đa 3 lần thử connect<br>• Fallback CPU tức thì<br>• Nghỉ Cooldown 30 phút<br>• Chặn `aleron.dt@gmail.com` |
| **GK1: Raw Input QC (Linguistic)** | • 100% Chữ Hán Giản thể<br>• Khớp âm - dấu thanh 1:1<br>• Lọc từ trùng negative context | • 100% Chữ Hán Giản thể<br>• Nghĩa tiếng Việt chuẩn xác<br>• 1 chủ đề thống nhất | • Định nghĩa tiếng Việt súc tích<br>• Chữ Hán đối ứng chuẩn<br>• Không lỗi chính tả/ký tự lạ | • 1 Nghĩa cốt lõi qua 5 cấp độ<br>• Tiến trình HSK 1➔5 bậc thang<br>• Độ dài câu $\le 35$ ký tự |
| **GK2: Processing & Render Integrity** | • Manim 1080x1920 60fps<br>• Google Colab GPU T4/CPU<br>• Âm thanh Edge-TTS chuẩn | • Manim 1080x1920 60fps<br>• Google Colab GPU T4/CPU<br>• Âm thanh Edge-TTS chuẩn | • Manim 1080x1920 60fps<br>• Google Colab GPU T4/CPU<br>• Âm thanh Edge-TTS chuẩn | • Manim 1080x1920 60fps<br>• 5s Gamification Tick Countdown<br>• Đếm ngược và hiệu ứng swoosh |
| **GK3: Output Compliance & Storage** | • Video QC Inspector (Bitrate, FPS)<br>• Google Drive `1Y240J5...`<br>• Link Cột K Streamable | • Video QC Inspector (Bitrate, FPS)<br>• Google Drive `1Y240J5...`<br>• Link Cột K Streamable | • Video QC Inspector (Bitrate, FPS)<br>• Google Drive `1Y240J5...`<br>• Link Cột K Streamable | • 100% Zero Vietnamese TTS<br>• Chuông Ding + Chinese Voice<br>• Link Cột K Streamable |
| **GK4: Ledger & Invariants** | • Google Sheets Tab `pinyin`<br>• Invariant `# == Row ID`<br>• **Khóa chặt 21px Row Height**<br>• Telegram Status Alerts | • Google Sheets Tab `vocabCN`<br>• Invariant `# == Row ID`<br>• **Khóa chặt 21px Row Height**<br>• Telegram Status Alerts | • Google Sheets Tab `vocabVN`<br>• Invariant `# == Row ID`<br>• **Khóa chặt 21px Row Height**<br>• Telegram Status Alerts | • Google Sheets Tab `multilevels`<br>• Invariant `# == Row ID`<br>• **Khóa chặt 21px Row Height**<br>• Telegram Video & Thumbnail Upload |

---

## 🔒 SECURITY, ZERO-LEAK & ZERO-VPS COMPUTE
1. **Credentials Isolation:**
   - Tất cả Token và Service Account Google Cloud được lưu trữ tại `~/.cloud-profiles/lelehoctiengtrung/`.
   - Tuyệt đối 0% Plaintext Secrets tại thư mục làm việc của dự án.
2. **Zero-VPS Compute Architecture:**
   - 100% tác vụ render video Manim nặng nề được điều phối sang Google Colab Cloud VM (`colab exec`).
   - 0% CPU và 0 MB RAM tải nặng trên VPS host khi ở trạng thái Idle.
3. **Strict 21px Row Height Invariant:**
   - Bất biến chiều cao hàng **21 px** được duy trì và cưỡng chế tự động trên toàn bộ 4 tabs sau mỗi mẻ render.

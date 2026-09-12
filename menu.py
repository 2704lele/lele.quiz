#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive Simple Command Wizard for LeLe Chinese Quiz Automation System.
Allows executing all pipeline tasks with simple menu numbers (1, 2, 3...).
Integrated 100% with Google Colab CLI for cloud Manim video rendering and Auto-QC.
"""

import os
import sys

# Suppress bytecode generation across exFAT filesystem
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import time
import subprocess
from typing import List, Dict, Any, Tuple

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import requests
from pinyinquiz.src.pre_render_validator import PreRenderValidator as PinyinValidator
from vocabCNquiz.src.pre_render_validator import PreRenderValidator as VocabCNValidator
from vocabVNquiz.src.pre_render_validator import PreRenderValidator as VocabVNValidator
from multilevelsquiz.src.pre_render_validator import PreRenderValidator as MultilevelsValidator
from pinyinquiz.src.gsheet_manager import GSheetManager as PinyinGSheet
from vocabCNquiz.src.gsheet_manager import GSheetManager as VocabCNGSheet
from vocabVNquiz.src.gsheet_manager import GSheetManager as VocabVNGSheet
from multilevelsquiz.src.gsheet_manager import GSheetManager as MultilevelsGSheet
from monitor import fetch_tab_raw_values, count_tab_statuses, verify_tab_data
from colab.colab_orchestrator import ColabQuizOrchestrator

EDGE_ROUTERS = {
    "pinyin": "https://lele-pinyinquiz.hothihuong113.workers.dev",
    "vocabcn": "https://lele-vocabcnquiz.hothihuong113.workers.dev",
    "vocabvn": "https://lele-vocabvnquiz.hothihuong113.workers.dev",
    "multilevels": "https://lele-multilevelsquiz.hothihuong113.workers.dev"
}

VALIDATORS = {
    "pinyin": PinyinValidator(),
    "vocabcn": VocabCNValidator(),
    "vocabvn": VocabVNValidator(),
    "multilevels": MultilevelsValidator()
}


def clear_screen():
    print("\033[H\033[J", end="")


def print_banner():
    print("""
\033[1;36m===================================================================
🏮 LELE CHINESE QUIZ — MENU ĐIỀU HÀNH NHANH (1-CLICK COMMANDS)
===================================================================\033[0m
   \033[1;32m[1]\033[0m 📊 Xem bảng trạng thái nhanh 4 Pipelines (In-View Status)
   \033[1;32m[2]\033[0m 💡 Tự động sinh Idea mới (Auto Ideation Batch)
   \033[1;32m[3]\033[0m 📝 Đăng nhanh 1 dòng Idea thủ công vào Google Sheet
   \033[1;32m[4]\033[0m 🎬 Kích hoạt Render Manim (Google Colab GPU T4 — Zero VPS)
   \033[1;32m[5]\033[0m 🚀 Đăng Video dòng số X lên Mạng Xã Hội (Buffer 1: Shorts/TikTok/Fanpage)
   \033[1;32m[6]\033[0m 🔍 Kích hoạt QC kiểm tra Video (Google Colab Auto-QC)
   \033[1;32m[7]\033[0m 🔄 Đặt lại trạng thái dòng thành Pending (Re-render)
   \033[1;32m[8]\033[0m 🌐 Xem cấu hình 3 kênh Video & Buffer 1 Vault (In-View Social)
   \033[1;32m[9]\033[0m 🧪 Chạy bộ kiểm thử hệ thống (pytest)
   [1;32m[a][0m 🩺 Auto-Healing Engine (Diagnose & Self-Heal)
   \033[1;32m[s]\033[0m ☁️ Đồng bộ toàn bộ mã nguồn lên Google Drive (00.codebases)
   \033[1;32m[b]\033[0m 💾 Sao lưu Snapshot Google Sheets & Config Map (Backups)
   \033[1;32m[h]\033[0m 📏 Khóa chặt bất biến chiều cao dòng 21px (Row Height Enforcer)
   \033[1;32m[c]\033[0m ⚡ Quản lý Google Colab CLI Pool (Xem tài khoản, phiên, giải phóng VM)
   \033[1;31m[0]\033[0m ❌ Thoát
\033[1;36m-------------------------------------------------------------------\033[0m""")


def action_status():
    print("\n\033[1;33m⏳ Đang truy vấn dữ liệu từ Google Sheets State DB...\033[0m")
    cmd = [sys.executable, os.path.join(PROJECT_ROOT, "monitor.py"), "--status"]
    subprocess.run(cmd, cwd=PROJECT_ROOT)
    input("\n\033[2mBấm [Enter] để quay lại Menu...\033[0m")


def action_social():
    print("\n\033[1;33m⏳ Đang kiểm tra cấu hình Mạng Xã Hội & Buffer Vault...\033[0m")
    cmd = [sys.executable, os.path.join(PROJECT_ROOT, "monitor.py"), "--social"]
    subprocess.run(cmd, cwd=PROJECT_ROOT)
    input("\n\033[2mBấm [Enter] để quay lại Menu...\033[0m")


def action_auto_ideation():
    print("\n\033[1;33m--- [2] TỰ ĐỘNG SINH IDEA MỚI ---\033[0m")
    print("Chọn Pipeline mục tiêu:")
    print("  1) Tất cả 4 pipelines (pinyin, vocabCN, vocabVN, multilevels) [Mặc định]")
    print("  2) pinyinquiz (pinyin: Hanzi ➔ Đoán Pinyin)")
    print("  3) vocabCNquiz (vocabCN: Hanzi ➔ Đoán Nghĩa TV)")
    print("  4) vocabVNquiz (vocabVN: Nghĩa TV ➔ Đoán Hanzi)")
    print("  5) multilevelsquiz (multilevels: 1 Nghĩa ➔ 5 Cấp HSK)")

    choice = input("👉 Nhập lựa chọn [1-5, Enter=1]: ").strip()
    pl_map = {"1": "all", "2": "pinyin", "3": "vocabcn", "4": "vocabvn", "5": "multilevels"}
    target_pl = pl_map.get(choice, "all")

    count_in = input("👉 Số lượng batch cần sinh [Enter=1]: ").strip()
    count = count_in if count_in.isdigit() and int(count_in) > 0 else "1"

    print("\nChế độ chạy:")
    print("  1) Dry-run (Chạy thử & xem trước, không ghi vào Google Sheets)")
    print("  2) Commit (Ghi trực tiếp vào Google Sheets & gửi webhook) [Mặc định]")
    mode_in = input("👉 Nhập lựa chọn [1-2, Enter=2]: ").strip()
    is_dry = (mode_in == "1")

    cmd = [sys.executable, os.path.join(PROJECT_ROOT, "scripts", "generate_daily_batches.py"), "--pipeline", target_pl, "--count", count]
    if is_dry:
        cmd.append("--dry-run")

    print(f"\n\033[1;32m🚀 Bắt đầu thực thi: {target_pl.upper()} | Số lượng: {count} | Mode: {'DRY-RUN' if is_dry else 'COMMIT'}...\033[0m\n")
    subprocess.run(cmd, cwd=PROJECT_ROOT)
    input("\n\033[2mBấm [Enter] để quay lại Menu...\033[0m")


def action_manual_idea():
    print("\n\033[1;33m--- [3] ĐĂNG NHANH 1 DÒNG IDEA THỦ CÔNG ---\033[0m")
    print("Chọn Pipeline:")
    print("  1) pinyinquiz (tab 'pinyin') [Mặc định]")
    print("  2) vocabCNquiz (tab 'vocabCN')")
    print("  3) vocabVNquiz (tab 'vocabVN')")
    print("  4) multilevelsquiz (tab 'multilevels')")
    pl_in = input("👉 Nhập lựa chọn [1-4, Enter=1]: ").strip()
    pl_map = {"1": "pinyin", "2": "vocabcn", "3": "vocabvn", "4": "multilevels"}
    pipeline = pl_map.get(pl_in, "pinyin")

    print("\nBạn muốn nhập theo cách nào?")
    print("  1) Dán nhanh 1 dòng (Format: Chủ đề | Từ 1:Pinyin:Nghĩa | Từ 2:Pinyin:Nghĩa | ...)")
    print("  2) Nhập từng từ một cách tuần tự [Mặc định]")
    print("  3) Sử dụng dữ liệu mẫu (Quick Sample)")
    input_mode = input("👉 Nhập lựa chọn [1-3, Enter=2]: ").strip()

    topic = ""
    level = "HSK 1-2"
    words = []

    if input_mode == "3":
        topic = "HSK 1-2 • HOA QUẢ TƯƠI"
        level = "HSK 1-2"
        words = [
            {"hanzi": "苹果", "pinyin": "píngguǒ", "meaning": "quả táo"},
            {"hanzi": "香蕉", "pinyin": "xiāngjiāo", "meaning": "quả chuối"},
            {"hanzi": "西瓜", "pinyin": "xīguā", "meaning": "dưa hấu"},
            {"hanzi": "葡萄", "pinyin": "pútáo", "meaning": "quả nho"},
            {"hanzi": "草莓", "pinyin": "cǎoméi", "meaning": "dâu tây"}
        ]
        print(f"\nĐã nạp mẫu: Chủ đề = '{topic}', 5 từ hoa quả.")
    elif input_mode == "1":
        print("\nNhập chuỗi định dạng (Ví dụ: HSK 1-2 • HOA QUẢ | 苹果:píngguǒ:quả táo | 香蕉:xiāngjiāo:quả chuối | 西瓜:xīguā:dưa hấu | 葡萄:pútáo:quả nho | 草莓:cǎoméi:dâu tây):")
        line = input("👉 Dán vào đây: ").strip()
        parts = [p.strip() for p in line.split("|") if p.strip()]
        if len(parts) >= 6:
            topic = parts[0]
            for p in parts[1:6]:
                wparts = p.split(":")
                hz = wparts[0].strip() if len(wparts) > 0 else ""
                py = wparts[1].strip() if len(wparts) > 1 else ""
                mean = wparts[2].strip() if len(wparts) > 2 else ""
                words.append({"hanzi": hz, "pinyin": py, "meaning": mean})
        else:
            print("\033[1;31m❌ Định dạng không đủ 1 chủ đề và 5 từ. Hủy thao tác.\033[0m")
            input("\n\033[2mBấm [Enter] để quay lại Menu...\033[0m")
            return
    else:
        topic_in = input("👉 Nhập Chủ đề (Topic) [VD: HSK 1-2 • MÓN ĂN]: ").strip()
        topic = topic_in if topic_in else "HSK 1-2 • TỪ VỰNG HÀNG NGÀY"
        level_in = input("👉 Nhập Level [Enter=HSK 1-2]: ").strip()
        level = level_in if level_in else "HSK 1-2"

        print("\nNhập lần lượt 5 từ (Chữ Hán, Pinyin có dấu, Nghĩa tiếng Việt):")
        for i in range(1, 6):
            print(f"  [Từ #{i}]:")
            hz = input("    • Chữ Hán (Hanzi): ").strip()
            py = input("    • Pinyin (có dấu): ").strip()
            mean = input("    • Nghĩa tiếng Việt: ").strip()
            words.append({"hanzi": hz, "pinyin": py, "meaning": mean})

    # Chạy Gatekeeper 1
    print("\n\033[1;33m🔍 Đang chạy kiểm duyệt ngôn ngữ Gatekeeper 1...\033[0m")
    val = VALIDATORS.get(pipeline, VALIDATORS["pinyin"])
    batch_data = {"topic": topic, "level": level, "words": words}
    is_ok, errors = val.validate_batch(batch_data)

    if not is_ok:
        print("\033[1;31m❌ GATEKEEPER 1 TỪ CHỐI BATCH VÌ PHÁT HIỆN LỖI:\033[0m")
        for err in errors:
            print(f"  • \033[1;33m{err}\033[0m")
        print("\nVui lòng kiểm tra lại chữ Hán giản thể, thanh điệu Pinyin hoặc nghĩa tiếng Việt.")
        input("\n\033[2mBấm [Enter] để quay lại Menu...\033[0m")
        return

    print("\033[1;32m✅ GATEKEEPER 1 XÁC NHẬN: 100% ĐẠT TIÊU CHUẨN NGÔN NGỮ!\033[0m")
    print(f"  Chủ đề: {topic} ({level})")
    for i, w in enumerate(words, start=1):
        print(f"  #{i}: {w['hanzi']} | {w['pinyin']} | {w['meaning']}")

    confirm = input("\n👉 Bạn có muốn ghi ngay dòng này vào Google Sheets không? [Y/n]: ").strip().lower()
    if confirm in ["", "y", "yes"]:
        print("\n\033[1;33m⏳ Đang ghi vào Google Sheets...\033[0m")
        try:
            if pipeline == "vocabcn":
                mgr = VocabCNGSheet()
            elif pipeline == "vocabvn":
                mgr = VocabVNGSheet()
            elif pipeline == "multilevels":
                mgr = MultilevelsGSheet()
            else:
                mgr = PinyinGSheet()

            all_rows = mgr.worksheet.get_all_values()
            next_row_id = len(all_rows) + 1  # Invariant: # == Row ID

            w_cols = ["", "", "", "", ""]
            for idx, w in enumerate(words):
                if idx < 5:
                    w_cols[idx] = f"{w.get('hanzi', '')}|{w.get('pinyin', '')}||{w.get('meaning', '')}"

            created_at = time.strftime("%Y-%m-%d %H:%M:%S")
            sheet_row = [
                next_row_id,
                topic,
                level,
                "Pending",
                w_cols[0],
                w_cols[1],
                w_cols[2],
                w_cols[3],
                w_cols[4],
                "",
                "",
                "",
                "",
                "",
                created_at,
                "Manual Post via Menu Wizard"
            ]

            mgr.worksheet.append_row(sheet_row)
            print(f"\033[1;32m🎉 Đã ghi thành công Batch #{next_row_id} vào tab '{mgr.tab_name}' với trạng thái 'Pending'!\033[0m")
        except Exception as e:
            print(f"\033[1;31m❌ Lỗi khi ghi Google Sheet: {e}\033[0m")
    else:
        print("Đã hủy thao tác ghi Sheet.")

    input("\n\033[2mBấm [Enter] để quay lại Menu...\033[0m")


def action_trigger_render():
    print("\n\033[1;33m--- [4] KÍCH HOẠT RENDER MANIM (GOOGLE COLAB GPU T4 / CPU FALLBACK) ---\033[0m")
    row_id = input("👉 Nhập Batch ID / Row # cần Render [VD: 24, để trống = render tất cả Pending]: ").strip()
    if row_id and not row_id.isdigit():
        print("\033[1;31m❌ Row ID không hợp lệ.\033[0m")
        input("\n\033[2mBấm [Enter] để quay lại Menu...\033[0m")
        return

    print("Chọn Pipeline:")
    if not row_id:
        print("  0) TOÀN BỘ 4 TABS (Quét sạch tất cả hàng Pending liên hoàn) [Mặc định]")
        print("  1) pinyinquiz")
        print("  2) vocabCNquiz")
        print("  3) vocabVNquiz")
        print("  4) multilevelsquiz")
        pl_in = input("👉 Nhập lựa chọn [0-4, Enter=0]: ").strip()
        pl_map = {"0": "all", "": "all", "1": "pinyin", "2": "vocabcn", "3": "vocabvn", "4": "multilevels"}
    else:
        print("  1) pinyinquiz [Mặc định]")
        print("  2) vocabCNquiz")
        print("  3) vocabVNquiz")
        print("  4) multilevelsquiz")
        pl_in = input("👉 Nhập lựa chọn [1-4, Enter=1]: ").strip()
        pl_map = {"1": "pinyin", "2": "vocabcn", "3": "vocabvn", "4": "multilevels"}
    pipeline = pl_map.get(pl_in, "all" if not row_id else "pinyin")

    print("\nChọn Độ Phân Giải / Chất lượng:")
    print("  1) qh (1080x1920 60fps - Chuẩn Đăng Shorts/TikTok) [Mặc định]")
    print("  2) ql (480x854 - Test Siêu Tốc)")
    q_in = input("👉 Nhập lựa chọn [1-2, Enter=1]: ").strip()
    quality = "ql" if q_in == "2" else "qh"

    print(f"\n\033[1;33m⏳ Đang kích hoạt Google Colab Cloud Runner (GPU T4 / CPU Fallback)...\033[0m")
    try:
        orch = ColabQuizOrchestrator()
        if pipeline == "all" and not row_id:
            print("🚀 Chế độ Batch Continuity: Quét và render toàn bộ các dòng Pending trên cả 4 tabs...")
            success = orch.run_all_pending(quality=quality)
        else:
            success = orch.render_and_qc(pipeline=pipeline, row_id=row_id, quality=quality)

        if success:
            print("\n\033[1;32m🎉 Google Colab Cloud Runner đã hoàn tất Render Manim & Auto-QC (Zero VPS compute)!\033[0m")
        else:
            print("\n\033[1;31m❌ Tiến trình Render trên Google Colab không thành công hoặc còn dòng chưa xử lý.\033[0m")
    except Exception as e:
        print(f"\033[1;31m❌ Lỗi điều phối Colab: {e}\033[0m")

    input("\n\033[2mBấm [Enter] để quay lại Menu...\033[0m")


def action_publish_social():
    print("\n\033[1;33m--- [5] ĐĂNG VIDEO / BÀI VIẾT LÊN MẠNG XÃ HỘI (BUFFER OMNI-CHANNEL) ---\033[0m")
    row_id = input("👉 Nhập Batch ID / Row # cần đăng [VD: 2, 5, 24]: ").strip()
    if not row_id.isdigit() or int(row_id) <= 1:
        print("\033[1;31m❌ Row ID không hợp lệ (phải là số >= 2).\033[0m")
        input("\n\033[2mBấm [Enter] để quay lại Menu...\033[0m")
        return

    print("\nChọn Tab / Pipeline:")
    print("  1) pinyinquiz (tab 'pinyin') [Mặc định]")
    print("  2) vocabCNquiz (tab 'vocabCN')")
    print("  3) vocabVNquiz (tab 'vocabVN')")
    print("  4) multilevelsquiz (tab 'multilevels')")
    pl_in = input("👉 Nhập lựa chọn [1-4, Enter=1]: ").strip()
    pl_map = {"1": "pinyin", "2": "vocabcn", "3": "vocabvn", "4": "multilevels"}
    pipeline = pl_map.get(pl_in, "pinyin")

    print("\nChọn Kênh Đăng (Buffer 1 Video Pipeline):")
    print("  1) Cả 3 kênh: YouTube Shorts + TikTok + FB Fanpage [Mặc định]")
    print("  2) Chỉ YouTube Shorts")
    print("  3) Chỉ TikTok")
    print("  4) Chỉ Facebook Fanpage")
    ch_in = input("👉 Nhập lựa chọn [1-4, Enter=1]: ").strip()
    ch_map = {
        "1": "buffer1",
        "2": "youtube",
        "3": "tiktok",
        "4": "fb"
    }
    channels = ch_map.get(ch_in, "buffer1")

    print("\nChế độ thao tác:")
    print("  1) 🚀 Đăng Thật Ngay (Live Dispatch qua Buffer 1)")
    print("  2) 📱 Gửi Thẻ Duyệt Bài vào Telegram Bot (để bấm nút Đăng Ngay trên Telegram)")
    print("  3) 🔍 Xem trước / Chạy thử (Dry-run) [Mặc định]")
    mode_in = input("👉 Nhập lựa chọn [1-3, Enter=3]: ").strip()

    if mode_in == "2":
        cmd = [
            sys.executable,
            os.path.join(PROJECT_ROOT, "scripts", "telegram_interactive_bot.py"),
            "preview", pipeline, row_id
        ]
        print(f"\n\033[1;32m📱 Đang gửi Thẻ Duyệt Bài Tab '{pipeline}' Dòng #{row_id} vào Telegram Bot...\033[0m\n")
        subprocess.run(cmd, cwd=PROJECT_ROOT)
        print("\033[1;32m✔ Đã gửi bài vào Telegram! Bạn hãy mở app Telegram và bấm nút [Đăng Ngay] để xuất bản.\033[0m")
        input("\n\033[2mBấm [Enter] để quay lại Menu...\033[0m")
        return

    is_dry = (mode_in != "1")
    cmd = [
        sys.executable,
        os.path.join(PROJECT_ROOT, "scripts", "publish_social_batch.py"),
        "--tab", pipeline,
        "--id", row_id,
        "--channels", channels
    ]
    if is_dry:
        cmd.append("--dry-run")

    print(f"\n\033[1;32m🚀 Bắt đầu gửi lệnh đăng: Tab '{pipeline}' | Dòng #{row_id} | Kênh: {channels.upper()} | Mode: {'DRY-RUN' if is_dry else 'LIVE'}...\033[0m\n")
    subprocess.run(cmd, cwd=PROJECT_ROOT)
    input("\n\033[2mBấm [Enter] để quay lại Menu...\033[0m")


def action_trigger_qc():
    print("\n\033[1;33m--- [6] KÍCH HOẠT QC KIỂM TRA VIDEO (GOOGLE COLAB) ---\033[0m")
    row_id = input("👉 Nhập Batch ID / Row # cần QC [VD: 24, để trống = tất cả dòng Video]: ").strip()
    if row_id and not row_id.isdigit():
        print("\033[1;31m❌ Row ID không hợp lệ.\033[0m")
        input("\n\033[2mBấm [Enter] để quay lại Menu...\033[0m")
        return

    print("Chọn Pipeline:")
    print("  1) pinyinquiz [Mặc định]")
    print("  2) vocabCNquiz")
    print("  3) vocabVNquiz")
    print("  4) multilevelsquiz")
    pl_in = input("👉 Nhập lựa chọn [1-4, Enter=1]: ").strip()
    pl_map = {"1": "pinyin", "2": "vocabcn", "3": "vocabvn", "4": "multilevels"}
    pipeline = pl_map.get(pl_in, "pinyin")

    print(f"\n\033[1;33m⏳ Đang điều phối kiểm định QC lên Google Colab VM...\033[0m")
    try:
        orch = ColabQuizOrchestrator()
        success = orch.qc_only(pipeline=pipeline, row_id=row_id)
        if success:
            print("\033[1;32m✔ Đã hoàn thành kiểm định QC trên Colab!\033[0m")
        else:
            print("\033[1;31m❌ Kiểm định QC trên Colab thất bại.\033[0m")
    except Exception as e:
        print(f"\033[1;31m❌ Lỗi khi gửi trigger QC: {e}\033[0m")

    input("\n\033[2mBấm [Enter] để quay lại Menu...\033[0m")


def action_set_pending():
    print("\n\033[1;33m--- [7] ĐẶT LẠI TRẠNG THÁI DÒNG THÀNH PENDING (RE-RENDER) ---\033[0m")
    row_id = input("👉 Nhập Batch ID / Row # cần đặt lại [VD: 24]: ").strip()
    if not row_id.isdigit():
        print("\033[1;31m❌ Row ID không hợp lệ.\033[0m")
        input("\n\033[2mBấm [Enter] để quay lại Menu...\033[0m")
        return

    print("Chọn Pipeline:")
    print("  1) pinyinquiz [Mặc định]")
    print("  2) vocabCNquiz")
    print("  3) vocabVNquiz")
    print("  4) multilevelsquiz")
    pl_in = input("👉 Nhập lựa chọn [1-4, Enter=1]: ").strip()
    pl_map = {"1": "pinyin", "2": "vocabcn", "3": "vocabvn", "4": "multilevels"}
    pipeline = pl_map.get(pl_in, "pinyin")

    try:
        if pipeline == "vocabcn":
            mgr = VocabCNGSheet()
        elif pipeline == "vocabvn":
            mgr = VocabVNGSheet()
        elif pipeline == "multilevels":
            mgr = MultilevelsGSheet()
        else:
            mgr = PinyinGSheet()

        row_num = int(row_id)
        mgr.update_batch_status(row_num, "Pending")
        print(f"\033[1;32m🎉 Đã cập nhật dòng {row_num} trên tab '{mgr.tab_name}' thành 'Pending' thành công!\033[0m")
    except Exception as e:
        print(f"\033[1;31m❌ Lỗi khi cập nhật trạng thái: {e}\033[0m")

    input("\n\033[2mBấm [Enter] để quay lại Menu...\033[0m")


def action_colab_management():
    print("\n\033[1;33m--- [C] QUẢN LÝ GOOGLE COLAB POOL & VM RUNTIMES (30M COOLDOWN) ---\033[0m")
    orch = ColabQuizOrchestrator()
    accs = orch.get_pool_status()
    print("Danh sách tài khoản Google Colab trong Pool:")
    for a in accs:
        rem = a.get("cooldown_remaining_sec", 0)
        if rem > 0:
            mins = rem // 60
            secs = rem % 60
            cd_str = f" | Nghỉ Cooldown: {mins}m {secs}s còn lại"
        else:
            cd_str = " | Trạng thái: SẴN SÀNG"
        print(f"  • [{a['status']:<12}] Alias: {a['alias']:<10} Email: {a['email']:<26} Thành công: {a['success_count']:<2}{cd_str}")

    print("\nThao tác:")
    print("  1) Quay lại Menu [Mặc định]")
    print("  2) Dừng và giải phóng phiên Colab VM đang hoạt động (Stop Session)")
    print("  3) Quét và xem danh sách các dòng Pending trên 4 tabs Google Sheets")
    print("  4) Khóa chặt bất biến chiều cao dòng 21px trên toàn bộ 4 tabs")
    sub_choice = input("👉 Nhập lựa chọn [1-4, Enter=1]: ").strip()
    if sub_choice == "2":
        orch.stop_session()
        print("\033[1;32m✓ Đã gửi lệnh giải phóng phiên Colab VM.\033[0m")
    elif sub_choice == "3":
        pending = orch.find_pending_rows_across_tabs()
        total = sum(len(v) for v in pending.values())
        print(f"\n📊 Tổng số dòng Pending: {total}")
        for tab, rows in pending.items():
            print(f"  • Tab '{tab}': {len(rows)} dòng -> {rows}")
    elif sub_choice == "4":
        orch.enforce_row_height()
        print("\033[1;32m✓ Đã thực thi chuẩn hóa 21px row height trên toàn bộ 4 tabs.\033[0m")

    input("\n\033[2mBấm [Enter] để quay lại Menu...\033[0m")


def action_auto_heal():
    print("\n\033[1;33m--- [a] UNIVERSAL AUTO-HEALING ENGINE (DIAGNOSE & SELF-HEAL) ---\033[0m\n")
    print("Chọn chế độ:")
    print("  1) Chẩn đoán sức khỏe hệ thống (Read-Only Check — ./auto_heal.sh --check) [Mặc định]")
    print("  2) Kích hoạt Tự Phục Hồi toàn diện (Self-Healing Remediation — ./auto_heal.sh --heal)")
    print("  3) Xuất báo cáo chẩn đoán JSON (--check --json) [Machine-Readable]")
    print("  0) Quay lại Menu")
    sub_choice = input("👉 Nhập lựa chọn [0-3, Enter=1]: ").strip()

    if sub_choice == "2":
        cmd = [sys.executable, os.path.join(PROJECT_ROOT, "scripts", "auto_heal.py"), "--heal"]
        subprocess.run(cmd, cwd=PROJECT_ROOT)
    elif sub_choice == "3":
        cmd = [sys.executable, os.path.join(PROJECT_ROOT, "scripts", "auto_heal.py"), "--check", "--json"]
        subprocess.run(cmd, cwd=PROJECT_ROOT)
    elif sub_choice == "0":
        return
    else:
        cmd = [sys.executable, os.path.join(PROJECT_ROOT, "scripts", "auto_heal.py"), "--check"]
        subprocess.run(cmd, cwd=PROJECT_ROOT)

    input("\n\033[2mBấm [Enter] để quay lại Menu...\033[0m")


def action_sync_code():
    print("\n\033[1;33m--- [s] ĐỒNG BỘ TOÀN BỘ MÃ NGUỒN LÊN GOOGLE DRIVE (00.CODEBASES) ---\033[0m\n")
    cmd = [sys.executable, os.path.join(PROJECT_ROOT, "scripts", "sync_code_to_gdrive.py")]
    subprocess.run(cmd, cwd=PROJECT_ROOT)
    input("\n\033[2mBấm [Enter] để quay lại Menu...\033[0m")


def action_backup_sheet():
    print("\n\033[1;33m--- [b] SAO LƯU SNAPSHOT GOOGLE SHEETS & CONFIG MAP (BACKUPS) ---\033[0m\n")
    cmd = [sys.executable, os.path.join(PROJECT_ROOT, "scripts", "auto_backup.py")]
    subprocess.run(cmd, cwd=PROJECT_ROOT)
    input("\n\033[2mBấm [Enter] để quay lại Menu...\033[0m")


def action_enforce_row_height():
    print("\n\033[1;33m--- [h] KHÓA CHẶT BẤT BIẾN CHIỀU CAO DÒNG 21PX ---\033[0m\n")
    cmd = [sys.executable, os.path.join(PROJECT_ROOT, "scripts", "enforce_row_height_21px.py")]
    subprocess.run(cmd, cwd=PROJECT_ROOT)
    input("\n\033[2mBấm [Enter] để quay lại Menu...\033[0m")


def action_run_tests():
    print("\n\033[1;33m--- [9] CHẠY BỘ KIỂM THỬ HỆ THỐNG (PYTEST) ---\033[0m\n")
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]
    subprocess.run(cmd, cwd=PROJECT_ROOT)
    input("\n\033[2mBấm [Enter] để quay lại Menu...\033[0m")


def main():
    while True:
        clear_screen()
        print_banner()
        choice = input("👉 Nhập số lựa chọn của bạn [0-9, a, s, b, h, c]: ").strip().lower()

        if choice == "1":
            action_status()
        elif choice == "2":
            action_auto_ideation()
        elif choice == "3":
            action_manual_idea()
        elif choice == "4":
            action_trigger_render()
        elif choice == "5":
            action_publish_social()
        elif choice == "6":
            action_trigger_qc()
        elif choice == "7":
            action_set_pending()
        elif choice == "8":
            action_social()
        elif choice == "9":
            action_run_tests()
        elif choice in ["a", "heal", "autoheal"]:
            action_auto_heal()
        elif choice in ["s", "sync"]:
            action_sync_code()
        elif choice in ["b", "backup"]:
            action_backup_sheet()
        elif choice in ["h", "height"]:
            action_enforce_row_height()
        elif choice in ["c", "colab"]:
            action_colab_management()
        elif choice == "0":
            print("\n\033[1;32m👋 Đã thoát Menu Điều Hành. Chúc bạn một ngày làm việc hiệu quả!\033[0m\n")
            break
        else:
            print("\033[1;31m❌ Lựa chọn không hợp lệ, vui lòng nhập từ 0 đến 9 hoặc 'c'.\033[0m")
            time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n\033[1;33m👋 Đã dừng chương trình.\033[0m\n")

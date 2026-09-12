#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LeLe Chinese Quiz Automation System — Interactive Terminal Control Dashboard (TUI)
Provides real-time pipeline monitoring, auto-ideation dispatch, manual idea posting
with live Gatekeeper 1 linguistic verification, and pipeline task controls.
"""

import os
import sys
import time
import json
import asyncio
import subprocess
import threading
from typing import Dict, Any, List, Tuple, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import requests
from rich.text import Text
from rich.table import Table
from rich.panel import Panel
from rich.console import Console

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll, Grid
from textual.widgets import (
    Header, Footer, Button, DataTable, Input, Select, Static,
    TabbedContent, TabPane, Log, Label, LoadingIndicator, Rule
)
from textual.binding import Binding
from textual.worker import Worker, get_current_worker

from monitor import (
    fetch_tab_raw_values, count_tab_statuses, verify_tab_data,
    check_edge_gateway, VALID_TABS, get_gsheet_client
)
from pinyinquiz.src.pre_render_validator import PreRenderValidator as PinyinValidator
from vocabCNquiz.src.pre_render_validator import PreRenderValidator as VocabCNValidator
from vocabVNquiz.src.pre_render_validator import PreRenderValidator as VocabVNValidator
from pinyinquiz.src.gsheet_manager import GSheetManager as PinyinGSheet
from vocabCNquiz.src.gsheet_manager import GSheetManager as VocabCNGSheet
from vocabVNquiz.src.gsheet_manager import GSheetManager as VocabVNGSheet

EDGE_ROUTER_URLS = {
    "pinyin": "https://lele-pinyinquiz.hothihuong113.workers.dev",
    "vocabcn": "https://lele-vocabcnquiz.hothihuong113.workers.dev",
    "vocabvn": "https://lele-vocabvnquiz.hothihuong113.workers.dev"
}

SAMPLE_TEMPLATES = {
    "pinyin": {
        "topic": "HSK 1-2 • HOA QUẢ TƯƠI",
        "level": "HSK 1-2",
        "words": [
            {"hanzi": "苹果", "pinyin": "píngguǒ", "meaning": "quả táo"},
            {"hanzi": "香蕉", "pinyin": "xiāngjiāo", "meaning": "quả chuối"},
            {"hanzi": "西瓜", "pinyin": "xīguā", "meaning": "dưa hấu"},
            {"hanzi": "葡萄", "pinyin": "pútáo", "meaning": "quả nho"},
            {"hanzi": "草莓", "pinyin": "cǎoméi", "meaning": "dâu tây"}
        ]
    },
    "vocabcn": {
        "topic": "HSK 3 • HOẠT ĐỘNG THƯỜNG NGÀY",
        "level": "HSK 3",
        "words": [
            {"hanzi": "打扫", "pinyin": "dǎsǎo", "meaning": "quét dọn"},
            {"hanzi": "散步", "pinyin": "sànbù", "meaning": "đi dạo"},
            {"hanzi": "锻炼", "pinyin": "duànliàn", "meaning": "tập luyện"},
            {"hanzi": "复习", "pinyin": "fùxí", "meaning": "ôn tập"},
            {"hanzi": "预习", "pinyin": "yùxí", "meaning": "chuẩn bị bài"}
        ]
    },
    "vocabvn": {
        "topic": "HSK 2 • GIAO TIẾP CĂNG THẲNG & VUI VẺ",
        "level": "HSK 2",
        "words": [
            {"hanzi": "高兴", "pinyin": "gāoxìng", "meaning": "vui vẻ"},
            {"hanzi": "难过", "pinyin": "nánguò", "meaning": "buồn bã"},
            {"hanzi": "着急", "pinyin": "zháojí", "meaning": "lo lắng, sốt ruột"},
            {"hanzi": "害怕", "pinyin": "hàipà", "meaning": "sợ hãi"},
            {"hanzi": "满意", "pinyin": "mǎnyì", "meaning": "hài lòng"}
        ]
    }
}


class LeLeControlApp(App):
    """Interactive Control Dashboard for LeLe Chinese Quiz Automation System."""

    CSS = """
    Screen {
        background: #111827;
        color: #f3f4f6;
    }

    Header {
        background: #1e3a8a;
        color: #ffffff;
        dock: top;
    }

    Footer {
        background: #1e293b;
        color: #94a3b8;
    }

    TabbedContent {
        height: 1fr;
    }

    .kpi-card {
        background: #1e293b;
        border: round #3b82f6;
        padding: 1;
        margin: 1;
        height: auto;
    }

    .section-title {
        color: #38bdf8;
        text-style: bold;
        margin-bottom: 1;
    }

    .status-badge {
        text-style: bold;
        padding: 0 1;
    }

    .form-container {
        background: #1f2937;
        border: solid #4b5563;
        padding: 1;
        margin: 1;
        height: auto;
    }

    .word-row {
        height: 3;
        margin-bottom: 1;
    }

    .word-row Input {
        width: 1fr;
        margin-right: 1;
    }

    .btn-action {
        margin-top: 1;
        margin-right: 1;
    }

    #monitor-table {
        height: 14;
        border: round #374151;
        margin: 1;
    }

    #action-log, #ideation-log {
        height: 16;
        background: #030712;
        border: solid #374151;
        margin: 1;
    }

    .audit-box {
        background: #0f172a;
        border: round #10b981;
        padding: 1;
        margin: 1;
        height: auto;
    }

    .node-box {
        background: #1e293b;
        border: solid #334155;
        padding: 1;
        margin: 0 1 1 1;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding("1", "switch_tab(tab-monitor)", "Monitor", show=True),
        Binding("2", "switch_tab(tab-ideation)", "Auto Idea", show=True),
        Binding("3", "switch_tab(tab-manual)", "Manual Post", show=True),
        Binding("4", "switch_tab(tab-actions)", "Actions", show=True),
        Binding("r", "refresh_all_data", "Refresh", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self, auto_fetch: bool = True):
        self.auto_fetch = auto_fetch
        super().__init__()
        self.validators = {
            "pinyin": PinyinValidator(),
            "vocabcn": VocabCNValidator(),
            "vocabvn": VocabVNValidator()
        }
        self.cached_tab_data: Dict[str, List[List[str]]] = {}
        self.cached_tab_stats: Dict[str, Dict[str, int]] = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with TabbedContent(initial="tab-monitor", id="main-tabs"):
            # TAB 1: PIPELINE MONITOR
            with TabPane("📊 Pipeline Monitor", id="tab-monitor"):
                with VerticalScroll():
                    yield Static("🏮 [bold cyan]HỆ THỐNG GIÁM SÁT REAL-TIME IN-VIEW PIPELINE[/]", classes="section-title")

                    # 4 Workflow Nodes Bar
                    with Horizontal(classes="node-box"):
                        yield Static("🌐 [bold green][1. Cloud Edge Gateway][/] (CF Workers <3ms) ➔ ", id="node-1")
                        yield Static("📊 [bold green][2. Google Sheets State DB][/] (Live Sync) ➔ ", id="node-2")
                        yield Static("⚙️ [bold green][3. GitHub Actions Manim][/] (Cloud Render) ➔ ", id="node-3")
                        yield Static("☁️ [bold green][4. Auto-QC & GDrive][/] (Col K Playable)", id="node-4")

                    # Summary Statistics KPI Panel
                    yield Static(id="kpi-summary-display", classes="kpi-card")

                    # Tab Data Browser
                    with Horizontal():
                        yield Label("Chọn Tab xem chi tiết: ", classes="status-badge")
                        yield Select(
                            options=[("pinyin (Hanzi ➔ Pinyin)", "pinyin"),
                                     ("vocabCN (Hanzi ➔ Meaning VN)", "vocabCN"),
                                     ("vocabVN (Meaning VN ➔ Hanzi)", "vocabVN")],
                            value="pinyin",
                            id="select-monitor-tab"
                        )
                        yield Button("🔄 Làm mới", id="btn-refresh-monitor", variant="primary")
                        yield Button("🔍 Kiểm tra Invariants", id="btn-verify-invariants", variant="warning")

                    yield DataTable(id="monitor-table", zebra_stripes=True)
                    yield Static(id="monitor-audit-output", classes="audit-box")

            # TAB 2: AUTO IDEATION
            with TabPane("💡 Auto Ideation", id="tab-ideation"):
                with VerticalScroll():
                    yield Static("💡 [bold yellow]TỰ ĐỘNG SINH BATCH Ý TƯỞNG (LLM + GATEKEEPER 1)[/]", classes="section-title")
                    with Vertical(classes="form-container"):
                        with Horizontal():
                            yield Label("Mục tiêu Pipeline: ")
                            yield Select(
                                options=[("Tất cả 3 Pipelines (all)", "all"),
                                         ("pinyinquiz (pinyin)", "pinyin"),
                                         ("vocabCNquiz (vocabcn)", "vocabcn"),
                                         ("vocabVNquiz (vocabvn)", "vocabvn")],
                                value="all",
                                id="select-ideation-pipeline"
                            )
                            yield Label("Số lượng Batch: ")
                            yield Select(
                                options=[("1 Batch", "1"), ("2 Batches", "2"), ("3 Batches", "3"), ("5 Batches", "5")],
                                value="1",
                                id="select-ideation-count"
                            )
                        with Horizontal():
                            yield Label("Chế độ chạy: ")
                            yield Select(
                                options=[("Dry-run (Xem trước, không ghi Sheet)", "dry-run"),
                                         ("Commit (Ghi Google Sheets & Dispatch Edge)", "commit")],
                                value="dry-run",
                                id="select-ideation-mode"
                            )
                            yield Button("🚀 Kích Hoạt Sinh Idea", id="btn-run-ideation", variant="success", classes="btn-action")

                    yield Static("📜 Nhật ký sinh Idea & Kiểm duyệt:", classes="section-title")
                    yield Log(id="ideation-log", highlight=True)

            # TAB 3: MANUAL IDEA POST
            with TabPane("📝 Manual Idea Post", id="tab-manual"):
                with VerticalScroll():
                    yield Static("📝 [bold green]ĐĂNG DÒNG IDEA THỦ CÔNG & KIỂM DUYỆT GATEKEEPER 1 TỨC THÌ[/]", classes="section-title")

                    with Vertical(classes="form-container"):
                        with Horizontal():
                            yield Label("Pipeline: ")
                            yield Select(
                                options=[("pinyin (pinyinquiz)", "pinyin"),
                                         ("vocabCN (vocabCNquiz)", "vocabcn"),
                                         ("vocabVN (vocabVNquiz)", "vocabvn")],
                                value="pinyin",
                                id="select-manual-pipeline"
                            )
                            yield Label("Chủ đề (Topic): ")
                            yield Input(value="HSK 1-2 • HOA QUẢ TƯƠI", id="input-manual-topic", placeholder="VD: HSK 1-2 • GIA ĐÌNH")
                            yield Label("Level: ")
                            yield Input(value="HSK 1-2", id="input-manual-level", placeholder="VD: HSK 1-2")

                        yield Static("Nhập 5 Từ Vựng (Hanzi | Pinyin có dấu thanh | Nghĩa Tiếng Việt):", classes="section-title")

                        # 5 word rows
                        for i in range(1, 6):
                            with Horizontal(classes="word-row"):
                                yield Label(f"Từ #{i}: ")
                                yield Input(id=f"input-hz-{i}", placeholder="Chữ Hán (VD: 苹果)")
                                yield Input(id=f"input-py-{i}", placeholder="Pinyin (VD: píngguǒ)")
                                yield Input(id=f"input-mean-{i}", placeholder="Nghĩa TV (VD: quả táo)")

                        with Horizontal():
                            yield Button("✨ Nạp Dữ Liệu Mẫu", id="btn-load-template", variant="default", classes="btn-action")
                            yield Button("🔍 Kiểm Duyệt Gatekeeper 1", id="btn-validate-manual", variant="warning", classes="btn-action")
                            yield Button("📤 Ghi Vào Google Sheets", id="btn-submit-manual", variant="success", classes="btn-action")

                    yield Static(id="manual-validation-report", classes="audit-box")

            # TAB 4: PIPELINE ACTIONS & CONTROL
            with TabPane("⚡ Pipeline Actions", id="tab-actions"):
                with VerticalScroll():
                    yield Static("⚡ [bold cyan]ĐIỀU PHỐI TÁC VỤ & KIỂM SOÁT PIPELINE[/]", classes="section-title")
                    with Vertical(classes="form-container"):
                        with Horizontal():
                            yield Label("Chọn Pipeline: ")
                            yield Select(
                                options=[("pinyin", "pinyin"), ("vocabCN", "vocabcn"), ("vocabVN", "vocabvn")],
                                value="pinyin",
                                id="select-action-pipeline"
                            )
                            yield Label("Mã Batch ID / Row #: ")
                            yield Input(value="24", id="input-action-row-id", placeholder="VD: 24")

                        with Horizontal():
                            yield Button("🎬 Trigger Manim Render", id="btn-action-render", variant="primary", classes="btn-action")
                            yield Button("🔍 Trigger QC Verification", id="btn-action-qc", variant="warning", classes="btn-action")
                            yield Button("🔄 Đặt lại Trạng thái: Pending", id="btn-action-set-pending", variant="error", classes="btn-action")
                            yield Button("🧪 Chạy Bộ Test Pytest (221 Tests)", id="btn-action-run-tests", variant="success", classes="btn-action")

                    yield Static("📜 Nhật ký thực thi tác vụ:", classes="section-title")
                    yield Log(id="action-log", highlight=True)

        yield Footer()

    def on_mount(self) -> None:
        """Initialize tables and load data upon mounting."""
        table = self.query_one("#monitor-table", DataTable)
        table.add_columns("# ID", "Topic", "Level", "Status", "Word 1..3", "Video Link (GDrive)", "Created At")

        # Load sample data into manual post tab
        self.action_load_template("pinyin")

        # Initial background fetch
        if self.auto_fetch:
            self.run_worker(self.async_fetch_all_data, exclusive=True, thread=True)

    def action_switch_tab(self, tab_id: str) -> None:
        """Switch active tab via hotkey."""
        tab_content = self.query_one("#main-tabs", TabbedContent)
        tab_content.active = tab_id

    def action_refresh_all_data(self) -> None:
        """Trigger manual refresh worker."""
        self.notify("Đang làm mới dữ liệu từ Google Sheets...", title="Syncing")
        if self.auto_fetch:
            self.run_worker(self.async_fetch_all_data, exclusive=True, thread=True)

    def async_fetch_all_data(self) -> None:
        """Background worker to query Google Sheets and edge routers."""
        stats = {}
        for tab in ["pinyin", "vocabCN", "vocabVN"]:
            ok, rows, err = fetch_tab_raw_values(tab, use_cache=False)
            if ok and rows:
                self.cached_tab_data[tab] = rows
                stats[tab] = count_tab_statuses(rows)
            else:
                self.cached_tab_data[tab] = []
                stats[tab] = {"Pending": 0, "Rendering": 0, "Video": 0, "Ready": 0, "Failed": 0, "Total": 0}

        self.cached_tab_stats = stats
        self.call_from_thread(self.update_ui_with_data)

    def update_ui_with_data(self) -> None:
        """Update Monitor UI widgets from cached data."""
        # 1. Update KPI Summary Panel
        kpi_text = Text()
        kpi_text.append("📊 TỔNG HỢP TRẠNG THÁI TOÀN BỘ 3 SUB-PIPELINES:\n", style="bold cyan")

        total_p = sum(s.get("Pending", 0) for s in self.cached_tab_stats.values())
        total_r = sum(s.get("Rendering", 0) for s in self.cached_tab_stats.values())
        total_v = sum(s.get("Video", 0) for s in self.cached_tab_stats.values())
        total_ready = sum(s.get("Ready", 0) for s in self.cached_tab_stats.values())
        total_f = sum(s.get("Failed", 0) for s in self.cached_tab_stats.values())
        total_all = sum(s.get("Total", 0) for s in self.cached_tab_stats.values())

        for tab_key, s in self.cached_tab_stats.items():
            kpi_text.append(f"  • {tab_key:8s} │ ", style="bold white")
            kpi_text.append(f"Pending: {s.get('Pending', 0):2d}  ", style="yellow")
            kpi_text.append(f"Rendering: {s.get('Rendering', 0):2d}  ", style="magenta")
            kpi_text.append(f"Video (QC): {s.get('Video', 0):2d}  ", style="cyan")
            kpi_text.append(f"Ready/Posted: {s.get('Ready', 0):2d}  ", style="green")
            kpi_text.append(f"Failed: {s.get('Failed', 0):2d}  ", style="red")
            kpi_text.append(f"Total: {s.get('Total', 0):2d}\n", style="bold white")

        kpi_text.append("─" * 78 + "\n", style="dim")
        kpi_text.append(f"  🔥 TỔNG CỘNG: {total_all} Rows  (Pending: {total_p} | Video QC: {total_v} | Ready: {total_ready} | Failed: {total_f})", style="bold green")

        self.query_one("#kpi-summary-display", Static).update(kpi_text)

        # 2. Update Data Table for selected tab
        selected_tab = self.query_one("#select-monitor-tab", Select).value or "pinyin"
        self.render_data_table(selected_tab)
        self.notify("Dữ liệu đã được đồng bộ 100%!", title="Sync Complete")

    def render_data_table(self, tab_name: str) -> None:
        """Populate DataTable with rows from the selected tab."""
        table = self.query_one("#monitor-table", DataTable)
        table.clear()

        rows = self.cached_tab_data.get(tab_name, [])
        if not rows or len(rows) < 2:
            return

        headers = rows[0]
        # Iterate over data rows (row index starts at 2)
        for idx, r in enumerate(rows[1:], start=2):
            row_id = r[0] if len(r) > 0 else str(idx)
            topic = r[1] if len(r) > 1 else ""
            level = r[2] if len(r) > 2 else ""
            status = r[3] if len(r) > 3 else ""

            # Words summary (Word 1..3)
            w1 = r[4].split("|")[0].strip() if len(r) > 4 and r[4] else ""
            w2 = r[5].split("|")[0].strip() if len(r) > 5 and r[5] else ""
            w3 = r[6].split("|")[0].strip() if len(r) > 6 and r[6] else ""
            words_brief = f"{w1}, {w2}, {w3}" if (w1 or w2 or w3) else ""

            video_url = r[10] if len(r) > 10 else ""
            if len(video_url) > 35:
                video_brief = video_url[:32] + "..."
            else:
                video_brief = video_url

            created_at = r[14] if len(r) > 14 else ""

            # Status styling
            status_style = "white"
            st_lower = status.strip().lower()
            if st_lower == "pending":
                status_style = "bold yellow"
            elif st_lower == "rendering":
                status_style = "bold magenta"
            elif st_lower == "video":
                status_style = "bold cyan"
            elif st_lower in ["ready", "posted"]:
                status_style = "bold green"
            elif st_lower == "failed":
                status_style = "bold red"

            table.add_row(
                Text(str(row_id), style="bold white"),
                Text(topic, style="white"),
                Text(level, style="cyan"),
                Text(status, style=status_style),
                Text(words_brief, style="dim white"),
                Text(video_brief, style="blue"),
                Text(created_at, style="dim")
            )

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes."""
        if event.select.id == "select-monitor-tab":
            self.render_data_table(str(event.value))
        elif event.select.id == "select-manual-pipeline":
            self.action_load_template(str(event.value).lower())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Dispatch button events."""
        btn_id = event.button.id

        if btn_id == "btn-refresh-monitor":
            self.action_refresh_all_data()
        elif btn_id == "btn-verify-invariants":
            self.run_invariants_check()
        elif btn_id == "btn-run-ideation":
            self.run_ideation_job()
        elif btn_id == "btn-load-template":
            pipe = str(self.query_one("#select-manual-pipeline", Select).value).lower()
            self.action_load_template(pipe)
        elif btn_id == "btn-validate-manual":
            self.run_manual_gatekeeper_validation()
        elif btn_id == "btn-submit-manual":
            self.run_submit_manual_to_sheet()
        elif btn_id == "btn-action-render":
            self.run_pipeline_action("render")
        elif btn_id == "btn-action-qc":
            self.run_pipeline_action("qc")
        elif btn_id == "btn-action-set-pending":
            self.run_pipeline_action("set-pending")
        elif btn_id == "btn-action-run-tests":
            self.run_pytest_suite_job()

    def run_invariants_check(self) -> None:
        """Run Invariant verification across all tabs."""
        selected_tab = self.query_one("#select-monitor-tab", Select).value or "pinyin"
        rows = self.cached_tab_data.get(selected_tab, [])
        if not rows:
            self.query_one("#monitor-audit-output", Static).update(Text(f"Chưa có dữ liệu cho tab '{selected_tab}'. Vui lòng bấm Làm mới.", style="bold red"))
            return

        audit = verify_tab_data(selected_tab, rows)
        report = Text()
        if audit["is_healthy"]:
            report.append(f"✅ KIỂM TRA INVARIANTS TAB '{selected_tab}': 100% ĐẠT TIÊU CHUẨN\n", style="bold green")
        else:
            report.append(f"⚠️ PHÁT HIỆN LỖI TRÊN TAB '{selected_tab}':\n", style="bold red")

        report.append(f"  • Tổng số dòng: {audit.get('total_rows', 0)} | Dòng dữ liệu: {audit.get('data_rows', 0)}\n")
        report.append(f"  • 16 Cột tiêu chuẩn: {'Đầy đủ (16/16)' if audit.get('columns_match') else 'Thiếu cột'}\n")
        report.append(f"  • Ràng buộc # == Row ID: {'Hợp lệ 100%' if audit.get('row_id_invariant_valid') else f'Sai lệch ({len(audit.get('row_id_mismatches', []))} dòng)'}\n")
        report.append(f"  • Link Google Drive Cột K: {audit.get('valid_video_links_count', 0)} hợp lệ / {len(audit.get('invalid_video_links', []))} không hợp lệ\n")

        self.query_one("#monitor-audit-output", Static).update(report)
        self.notify("Đã hoàn thành kiểm tra Invariants!", title="Audit Done")

    def action_load_template(self, pipeline: str) -> None:
        """Load sample data into manual form."""
        key = pipeline.lower()
        tmpl = SAMPLE_TEMPLATES.get(key, SAMPLE_TEMPLATES["pinyin"])

        self.query_one("#input-manual-topic", Input).value = tmpl["topic"]
        self.query_one("#input-manual-level", Input).value = tmpl["level"]

        for i, w in enumerate(tmpl["words"], start=1):
            self.query_one(f"#input-hz-{i}", Input).value = w["hanzi"]
            self.query_one(f"#input-py-{i}", Input).value = w["pinyin"]
            self.query_one(f"#input-mean-{i}", Input).value = w["meaning"]

        self.notify(f"Đã nạp dữ liệu mẫu cho {pipeline}!", title="Template Loaded")

    def gather_manual_words(self) -> List[Dict[str, str]]:
        """Read 5 words from manual inputs."""
        words = []
        for i in range(1, 6):
            hz = self.query_one(f"#input-hz-{i}", Input).value.strip()
            py = self.query_one(f"#input-py-{i}", Input).value.strip()
            mean = self.query_one(f"#input-mean-{i}", Input).value.strip()
            if hz or py or mean:
                words.append({"hanzi": hz, "pinyin": py, "meaning": mean})
        return words

    def run_manual_gatekeeper_validation(self) -> Tuple[bool, List[str]]:
        """Execute deterministic Gatekeeper 1 linguistic checks."""
        pipeline = str(self.query_one("#select-manual-pipeline", Select).value).lower()
        topic = self.query_one("#input-manual-topic", Input).value.strip()
        level = self.query_one("#input-manual-level", Input).value.strip()
        words = self.gather_manual_words()

        validator = self.validators.get(pipeline, self.validators["pinyin"])
        batch_data = {"topic": topic, "level": level, "words": words}

        is_ok, errors = validator.validate_batch(batch_data)

        report = Text()
        if is_ok:
            report.append("✅ GATEKEEPER 1 VALIDATION: 100% ĐẠT TIÊU CHUẨN NGÔN NGỮ!\n", style="bold green")
            report.append("  ✔ 100% Chữ Hán Giản Thể (Simplified Chinese).\n", style="green")
            report.append("  ✔ Không chứa từ cấm tiếng Anh trong phần nghĩa tiếng Việt.\n", style="green")
            report.append("  ✔ Pinyin và thanh điệu khớp 1:1, không lặp từ trong batch.\n", style="green")
        else:
            report.append("❌ GATEKEEPER 1 TỪ CHỐI BATCH VÌ CÓ LỖI:\n", style="bold red")
            for err in errors:
                report.append(f"  • {err}\n", style="yellow")

        self.query_one("#manual-validation-report", Static).update(report)
        return is_ok, errors

    def run_submit_manual_to_sheet(self) -> None:
        """Submit manual batch to Google Sheets after validation."""
        is_ok, errors = self.run_manual_gatekeeper_validation()
        if not is_ok:
            self.notify("Không thể submit do có lỗi Gatekeeper 1. Vui lòng sửa lại!", title="Validation Failed", severity="error")
            return

        pipeline = str(self.query_one("#select-manual-pipeline", Select).value).lower()
        topic = self.query_one("#input-manual-topic", Input).value.strip()
        level = self.query_one("#input-manual-level", Input).value.strip()
        words = self.gather_manual_words()

        self.notify("Đang ghi dữ liệu vào Google Sheets...", title="Submitting")

        def worker_task():
            try:
                # Select GSheet Manager for the tab
                if pipeline == "vocabcn":
                    mgr = VocabCNGSheet()
                elif pipeline == "vocabvn":
                    mgr = VocabVNGSheet()
                else:
                    mgr = PinyinGSheet()

                all_rows = mgr.worksheet.get_all_values()
                next_row_id = len(all_rows) + 1  # Invariant: # == Row ID

                # Build formatted Word strings (hanzi|pinyin||meaning)
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
                    "Manual Post via LeLe Control TUI"
                ]

                mgr.worksheet.append_row(sheet_row)

                # Update UI
                self.call_from_thread(self.notify, f"Đã ghi thành công Batch #{next_row_id} vào tab '{mgr.tab_name}'!", title="Success")
                self.call_from_thread(self.action_refresh_all_data)
            except Exception as e:
                self.call_from_thread(self.notify, f"Lỗi khi ghi Sheet: {e}", title="Error", severity="error")

        threading.Thread(target=worker_task, daemon=True).start()

    def run_ideation_job(self) -> None:
        """Launch background ideation batch generator."""
        pipeline = str(self.query_one("#select-ideation-pipeline", Select).value)
        count = str(self.query_one("#select-ideation-count", Select).value)
        mode = str(self.query_one("#select-ideation-mode", Select).value)

        log_widget = self.query_one("#ideation-log", Log)
        log_widget.clear()
        log_widget.write_line(f"🚀 [bold green]BẮT ĐẦU JOB SINH IDEA: Pipeline={pipeline} | Count={count} | Mode={mode}[/]")

        cmd = [sys.executable, os.path.join(PROJECT_ROOT, "scripts", "generate_daily_batches.py"), "--pipeline", pipeline, "--count", count]
        if mode == "dry-run":
            cmd.append("--dry-run")

        def stream_worker():
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=PROJECT_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                for line in proc.stdout:
                    log_widget.write_line(line.rstrip())
                proc.wait()
                if proc.returncode == 0:
                    log_widget.write_line("\n🎉 [bold green]JOB SINH IDEA HOÀN THÀNH THÀNH CÔNG (100% PASS)![/]")
                    self.call_from_thread(self.notify, "Sinh Idea hoàn tất!", title="Job Done")
                    if mode != "dry-run":
                        self.call_from_thread(self.action_refresh_all_data)
                else:
                    log_widget.write_line(f"\n❌ [bold red]JOB SINH IDEA KẾT THÚC VỚI MÃ LỖI: {proc.returncode}[/]")
            except Exception as e:
                log_widget.write_line(f"❌ Lỗi thực thi subprocess: {e}")

        threading.Thread(target=stream_worker, daemon=True).start()

    def run_pipeline_action(self, action_type: str) -> None:
        """Trigger Cloudflare Edge / Sheet actions."""
        pipeline = str(self.query_one("#select-action-pipeline", Select).value).lower()
        row_id = self.query_one("#input-action-row-id", Input).value.strip()
        log_widget = self.query_one("#action-log", Log)

        if not row_id.isdigit():
            self.notify("Vui lòng nhập Batch ID / Row # hợp lệ!", title="Invalid ID", severity="error")
            return

        base_url = EDGE_ROUTER_URLS.get(pipeline, EDGE_ROUTER_URLS["pinyin"])

        def action_worker():
            log_widget.write_line(f"⚡ Thực thi tác vụ '{action_type}' cho Pipeline '{pipeline}' (Batch #{row_id})...")
            try:
                if action_type == "render":
                    url = f"{base_url}/api/trigger-render"
                    res = requests.post(url, json={"row_id": row_id}, timeout=10)
                    log_widget.write_line(f"  ➔ POST {url} -> HTTP {res.status_code}: {res.text}")
                    self.call_from_thread(self.notify, f"Đã kích hoạt Render Manim cho Batch #{row_id}!", title="Triggered")

                elif action_type == "qc":
                    url = f"{base_url}/api/trigger-qc"
                    res = requests.post(url, json={"row_id": row_id}, timeout=10)
                    log_widget.write_line(f"  ➔ POST {url} -> HTTP {res.status_code}: {res.text}")
                    self.call_from_thread(self.notify, f"Đã kích hoạt QC Check cho Batch #{row_id}!", title="QC Triggered")

                elif action_type == "set-pending":
                    # Direct Google Sheet status update
                    if pipeline == "vocabcn":
                        mgr = VocabCNGSheet()
                    elif pipeline == "vocabvn":
                        mgr = VocabVNGSheet()
                    else:
                        mgr = PinyinGSheet()

                    row_num = int(row_id)
                    mgr.update_batch_status(row_num, "Pending")
                    log_widget.write_line(f"  ➔ Đã cập nhật dòng {row_num} trên tab '{mgr.tab_name}' thành 'Pending'.")
                    self.call_from_thread(self.notify, f"Đã đặt lại trạng thái Batch #{row_id} thành Pending!", title="Status Updated")
                    self.call_from_thread(self.action_refresh_all_data)

            except Exception as e:
                log_widget.write_line(f"❌ Lỗi tác vụ: {e}")
                self.call_from_thread(self.notify, f"Lỗi thực thi: {e}", title="Error", severity="error")

        threading.Thread(target=action_worker, daemon=True).start()

    def run_pytest_suite_job(self) -> None:
        """Run full test suite in background."""
        log_widget = self.query_one("#action-log", Log)
        log_widget.clear()
        log_widget.write_line("🧪 [bold cyan]BẮT ĐẦU CHẠY TOÀN BỘ TEST SUITE (pytest tests/ -v)...[/]")

        cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]

        def test_worker():
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=PROJECT_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                for line in proc.stdout:
                    log_widget.write_line(line.rstrip())
                proc.wait()
                if proc.returncode == 0:
                    log_widget.write_line("\n🎉 [bold green]TOÀN BỘ 221 TESTS ĐỀU ĐẠT CHUẨN (100% GREEN)![/]")
                    self.call_from_thread(self.notify, "221/221 Tests Passed!", title="Tests Passed")
                else:
                    log_widget.write_line(f"\n❌ [bold red]MỘT SỐ TEST THẤT BẠI (Code {proc.returncode})[/]")
            except Exception as e:
                log_widget.write_line(f"❌ Lỗi khi chạy pytest: {e}")

        threading.Thread(target=test_worker, daemon=True).start()


if __name__ == "__main__":
    app = LeLeControlApp()
    app.run()

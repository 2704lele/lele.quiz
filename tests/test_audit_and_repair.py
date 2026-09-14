#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_audit_and_repair.py
Unit & Mock Integration Tests for Historical Deduplication & In-Place Repair Engine.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.linguistic_qc import GlobalHanziFrequencyMatrix, normalize_topic_string, clean_quiz_topic
from scripts.audit_and_repair_historical_duplicates import (
    audit_and_repair_tab,
    generate_fresh_batch_for_tab,
    STANDARD_COLUMNS,
)


def test_audit_detects_historical_duplicates_and_spirit_issues():
    """Verify audit_and_repair_tab accurately detects duplicate topics and spirit violations."""
    mock_ws = MagicMock()
    mock_ss = MagicMock()
    mock_ss.worksheet.return_value = mock_ws

    # Simulate 6 rows in pinyin tab:
    # Row 1: Headers
    # Row 2: Original "Đồ Ăn & Thức Uống" (Published)
    # Row 3: "Phương Tiện Giao Thông" (Published)
    # Row 4: "Thử thách Phân biệt Thanh điệu" (Ready) -> Invalid spirit!
    # Row 5: "Đồ Ăn & Thức Uống" (Ready) -> Duplicate of Row 2!
    # Row 6: "Thời Tiết Bốn Mùa" (Pending) -> Valid
    sample_rows = [
        STANDARD_COLUMNS,
        ["#2", "Đồ Ăn & Thức Uống", "HSK 1", "Published", "苹果 | píng guǒ | quả táo", "香蕉 | xiāng jiāo | quả chuối", "西瓜 | xī guā | dưa hấu", "葡萄 | pú tao | nho", "草莓 | cǎo méi | dâu tây", "YOUTUBE SHORTS TIKTOK FACEBOOK REELS", "", "", "", "", "2026-09-01", "Notes"],
        ["#3", "Phương Tiện Giao Thông", "HSK 2", "Published", "飞机 | fēi jī | máy bay", "火车 | huǒ chē | tàu hỏa", "汽车 | qì chē | ô tô", "轮船 | lún chuán | tàu thủy", "自行车 | zì xíng chē | xe đạp", "YOUTUBE SHORTS TIKTOK FACEBOOK REELS", "", "", "", "", "2026-09-01", "Notes"],
        ["#4", "Thử thách Phân biệt Thanh điệu", "HSK 1", "Ready", "妈 | mā | mẹ", "麻 | má | cây gai", "马 | mǎ | ngựa", "骂 | mà | mắng", "吗 | ma | không", "YOUTUBE SHORTS TIKTOK FACEBOOK REELS", "", "", "", "", "2026-09-02", "Notes"],
        ["#5", "Đồ Ăn & Thức Uống", "HSK 1", "Ready", "米饭 | mǐ fàn | cơm", "面条 | miàn tiáo | mì", "包子 | bāo zi | bánh bao", "饺子 | jiǎo zi | sủi cảo", "面包 | miàn bāo | bánh mì", "YOUTUBE SHORTS TIKTOK FACEBOOK REELS", "", "", "", "", "2026-09-03", "Notes"],
        ["#6", "Thời Tiết Bốn Mùa", "HSK 2", "Pending", "晴天 | qíng tiān | trời nắng", "下雨 | xià yǔ | trời mưa", "刮风 | guā fēng | nổi gió", "下雪 | xià xuě | tuyết rơi", "阴天 | yīn tiān | trời râm", "YOUTUBE SHORTS TIKTOK FACEBOOK REELS", "", "", "", "", "2026-09-04", "Notes"],
    ]
    mock_ws.get_all_values.return_value = sample_rows

    matrix = GlobalHanziFrequencyMatrix(spreadsheet_client=None)
    rotator = MagicMock()

    # Run in dry-run mode
    res = audit_and_repair_tab(
        ss=mock_ss,
        tab="pinyin",
        rotator=rotator,
        matrix=matrix,
        dry_run=True,
        fix_spirit=True
    )

    assert res["tab"] == "pinyin"
    assert res["scanned_rows"] == 5
    # Duplicate detected at Row 5 (matching Row 2)
    assert len(res["duplicates_found"]) == 1
    assert res["duplicates_found"][0]["row_idx"] == 5
    assert res["duplicates_found"][0]["matches_row"] == 2

    # Invalid spirit detected at Row 4
    assert len(res["invalid_spirit_found"]) == 1
    assert res["invalid_spirit_found"][0]["row_idx"] == 4
    assert "thanh điệu" in res["invalid_spirit_found"][0]["errors"][0].lower()


def test_in_place_repair_preserves_row_id_and_structure():
    """Verify that in-place repair updates the exact cell range without deleting rows."""
    mock_ws = MagicMock()
    mock_ss = MagicMock()
    mock_ss.worksheet.return_value = mock_ws

    sample_rows = [
        STANDARD_COLUMNS,
        ["#2", "Đồ Ăn & Thức Uống", "HSK 1", "Published", "苹果 | píng guǒ | quả táo", "香蕉 | xiāng jiāo | quả chuối", "西瓜 | xī guā | dưa hấu", "葡萄 | pú tao | nho", "草莓 | cǎo méi | dâu tây", "YOUTUBE SHORTS TIKTOK FACEBOOK REELS", "", "", "", "", "2026-09-01", "Notes"],
        ["#3", "Đồ Ăn & Thức Uống", "HSK 1", "Ready", "米饭 | mǐ fàn | cơm", "面条 | miàn tiáo | mì", "包子 | bāo zi | bánh bao", "饺子 | jiǎo zi | sủi cảo", "面包 | miàn bāo | bánh mì", "YOUTUBE SHORTS TIKTOK FACEBOOK REELS", "", "", "", "", "2026-09-02", "Notes"],
    ]
    mock_ws.get_all_values.return_value = sample_rows

    matrix = GlobalHanziFrequencyMatrix(spreadsheet_client=None)
    rotator = MagicMock()

    # Mock AI response for fresh batch
    rotator.generate_quiz_ideas.return_value = ([{
        "topic": "Đồ Dùng Học Tập",
        "level": "HSK 1",
        "words": [
            {"hanzi": "书包", "pinyin": "shū bāo", "meaning": "cặp sách"},
            {"hanzi": "铅笔", "pinyin": "qiān bǐ", "meaning": "bút chì"},
            {"hanzi": "橡皮", "pinyin": "xiàng pí", "meaning": "cục tẩy"},
            {"hanzi": "尺子", "pinyin": "chǐ zi", "meaning": "thước kẻ"},
            {"hanzi": "本子", "pinyin": "běn zi", "meaning": "quyển vở"}
        ]
    }], "mock-gemini")

    # Run in live repair mode
    res = audit_and_repair_tab(
        ss=mock_ss,
        tab="pinyin",
        rotator=rotator,
        matrix=matrix,
        dry_run=False,
        fix_spirit=True
    )

    assert len(res["repaired_rows"]) == 1
    rep = res["repaired_rows"][0]
    assert rep["row_idx"] == 3
    assert rep["new_topic"] == "Đồ Dùng Học Tập"

    # Verify ws.update was called on exact row range "A3:P3"
    mock_ws.update.assert_called_once()
    call_args = mock_ws.update.call_args
    called_range = call_args.kwargs.get("range_name") or (call_args.args[0] if call_args.args else None)
    called_data = call_args.kwargs.get("values") or (call_args.args[1] if len(call_args.args) > 1 else None)

    assert called_range == "A3:P3"
    assert len(called_data) == 1
    row_cells = called_data[0]
    assert len(row_cells) == 16
    assert row_cells[0] == "#3"  # Preserved Row ID!
    assert row_cells[1] == "Đồ Dùng Học Tập"
    assert row_cells[3] == "Pending"  # Status reset to Pending

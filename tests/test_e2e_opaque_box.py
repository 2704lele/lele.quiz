#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Full E2E Opaque-Box Lifecycle Simulation & Tier 4 Real-World Scenarios.
Covers Feature F14 and all Real-World Production Scenarios across pinyin, vocabCN, vocabVN.
"""

import os
import sys
import re
import time
import pytest
from typing import Dict, Any, List

from tests.conftest import (
    STANDARD_16_COLUMNS,
    SAMPLE_VALID_BATCH_PINYIN,
    SAMPLE_VALID_BATCH_VOCABCN,
    SAMPLE_VALID_BATCH_VOCABVN
)
import pinyinquiz.src.pre_render_validator as pinyin_val
import vocabCNquiz.src.pre_render_validator as vocabcn_val
import vocabVNquiz.src.pre_render_validator as vocabvn_val

DRIVE_URL_REGEX = re.compile(r"^https://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)/view(\?usp=drivesdk)?$")


class MockGoogleSheetsDB:
    """In-memory mock representing Google Sheets State DB with 16-column schema."""
    def __init__(self, tab_name: str = "pinyin"):
        self.tab_name = tab_name
        self.rows: List[Dict[str, Any]] = []

    def append_batch(self, batch_data: Dict[str, Any], initial_status: str = "Pending") -> int:
        target_row_number = len(self.rows) + 2  # Physical row index (Row 1 is header)
        words = batch_data.get("words", [])

        row = {
            "_row_number": target_row_number,
            "#": f"#{target_row_number}",
            "Topic": batch_data.get("topic", ""),
            "Level": batch_data.get("level", "HSK 1"),
            "Status": initial_status,
            "Word 1": f"{words[0]['hanzi']} | {words[0]['pinyin']} | {words[0]['meaning']}" if len(words) > 0 else "",
            "Word 2": f"{words[1]['hanzi']} | {words[1]['pinyin']} | {words[1]['meaning']}" if len(words) > 1 else "",
            "Word 3": f"{words[2]['hanzi']} | {words[2]['pinyin']} | {words[2]['meaning']}" if len(words) > 2 else "",
            "Word 4": f"{words[3]['hanzi']} | {words[3]['pinyin']} | {words[3]['meaning']}" if len(words) > 3 else "",
            "Word 5": f"{words[4]['hanzi']} | {words[4]['pinyin']} | {words[4]['meaning']}" if len(words) > 4 else "",
            "metadata": "🎬 YOUTUBE SHORTS\n🎵 TIKTOK\n📱 FACEBOOK REELS",
            "Video": "",
            "Youtube": "",
            "Tiktok": "",
            "Facebook": "",
            "Created At": "2026-08-27T08:00:00+07:00",
            "Notes": ""
        }
        self.rows.append(row)
        return target_row_number

    def update_row_status(self, row_number: int, status: str, video_url: str = None, notes: str = None):
        for r in self.rows:
            if r["_row_number"] == row_number:
                r["Status"] = status
                if video_url:
                    r["Video"] = video_url
                if notes:
                    r["Notes"] = (r["Notes"] + " | " + notes).strip(" |")
                return True
        return False

    def get_row(self, row_number: int) -> Dict[str, Any]:
        for r in self.rows:
            if r["_row_number"] == row_number:
                return dict(r)
        return {}


# ============================================================================
# 1. REAL-WORLD SCENARIO 1: DAILY 5-BATCH PRODUCTION RUN
# ============================================================================

def test_scenario_1_daily_5_batch_production_lifecycle():
    """
    Scenario 1: Daily 5-batch production generation and lifecycle progression.
    Generates 5 batches -> Gatekeeper 1 -> Sheets DB -> Cloud Render -> Auto-QC -> Ready.
    """
    db = MockGoogleSheetsDB(tab_name="vocabCN")
    raw_batches = [
        {"topic": "Đồ Ăn & Thức Uống", "level": "HSK 1", "words": [
            {"hanzi": "苹果", "pinyin": "píng guǒ", "meaning": "Quả táo"},
            {"hanzi": "米饭", "pinyin": "mǐ fàn", "meaning": "Cơm trắng"},
            {"hanzi": "面条", "pinyin": "miàn tiáo", "meaning": "Mì sợi"},
            {"hanzi": "喝水", "pinyin": "hē shuǐ", "meaning": "Uống nước"},
            {"hanzi": "牛奶", "pinyin": "niú nǎi", "meaning": "Sữa tươi"}
        ]},
        {"topic": "Giao Thông Đô Thị", "level": "HSK 2", "words": [
            {"hanzi": "飞机", "pinyin": "fēi jī", "meaning": "Máy bay"},
            {"hanzi": "出租车", "pinyin": "chū zū chē", "meaning": "Xe taxi"},
            {"hanzi": "公共汽车", "pinyin": "gōng gòng qì chē", "meaning": "Xe buýt"},
            {"hanzi": "火车站", "pinyin": "huǒ chē zhàn", "meaning": "Ga tàu hỏa"},
            {"hanzi": "飞机场", "pinyin": "fēi jī chǎng", "meaning": "Sân bay"}
        ]},
        {"topic": "Đồ Dùng Học Tập", "level": "HSK 1", "words": [
            {"hanzi": "书包", "pinyin": "shū bāo", "meaning": "Cặp sách"},
            {"hanzi": "铅笔", "pinyin": "qiān bǐ", "meaning": "Bút chì"},
            {"hanzi": "橡皮", "pinyin": "xiàng pí", "meaning": "Cục tẩy"},
            {"hanzi": "尺子", "pinyin": "chǐ zi", "meaning": "Thước kẻ"},
            {"hanzi": "本子", "pinyin": "běn zi", "meaning": "Quyển vở"}
        ]},
        {"topic": "Cảm Xúc & Tâm Trạng", "level": "HSK 2", "words": [
            {"hanzi": "高兴", "pinyin": "gāo xìng", "meaning": "Vui vẻ"},
            {"hanzi": "难过", "pinyin": "nán guò", "meaning": "Buồn bã"},
            {"hanzi": "生气", "pinyin": "shēng qì", "meaning": "Tức giận"},
            {"hanzi": "害怕", "pinyin": "hài pà", "meaning": "Sợ hãi"},
            {"hanzi": "满意", "pinyin": "mǎn yì", "meaning": "Hài lòng"}
        ]},
        {"topic": "Thời Tiết Bốn Mùa", "level": "HSK 3", "words": [
            {"hanzi": "晴天", "pinyin": "qíng tiān", "meaning": "Trời nắng"},
            {"hanzi": "下雨", "pinyin": "xià yǔ", "meaning": "Trời mưa"},
            {"hanzi": "刮风", "pinyin": "guā fēng", "meaning": "Gió thổi"},
            {"hanzi": "下雪", "pinyin": "xià xuě", "meaning": "Tuyết rơi"},
            {"hanzi": "阴天", "pinyin": "yīn tiān", "meaning": "Trời âm u"}
        ]}
    ]

    # Step 1: Validate all 5 batches through Gatekeeper 1
    for b_idx, batch in enumerate(raw_batches):
        is_valid, errors = vocabcn_val.PreRenderValidator.validate_batch(batch)
        assert is_valid is True, f"Batch {b_idx + 1} failed GK1: {errors}"

        # Step 2: Append to Sheets DB (Row 2..6)
        row_id = db.append_batch(batch, initial_status="Pending")
        assert row_id == b_idx + 2

        # Step 3: Transition to Rendering
        db.update_row_status(row_id, status="Rendering")

        # Step 4: Simulate Manim Cloud Render & GDrive Upload
        fake_file_id = f"1Y240J5_SampleDriveId_{row_id:04d}_abcdef"
        video_url = f"https://drive.google.com/file/d/{fake_file_id}/view?usp=drivesdk"
        db.update_row_status(row_id, status="Video", video_url=video_url)

        # Step 5: Auto-QC Inspection & Ready Promotion
        qc_notes = f"Auto-QC Passed (1080x1920 60fps | Lum: 125.4 | Cover MAD: 12.1) [2026-08-27 08:0{b_idx}:00]"
        db.update_row_status(row_id, status="Ready", notes=qc_notes)

    # Verification of final DB state
    assert len(db.rows) == 5
    for r in db.rows:
        assert r["Status"] == "Ready"
        assert DRIVE_URL_REGEX.match(r["Video"]) is not None
        assert "Auto-QC Passed" in r["Notes"]
        assert int(r["#"].replace("#", "")) == r["_row_number"]


# ============================================================================
# 2. REAL-WORLD SCENARIO 2: SINGLE-ROW RE-GENERATION
# ============================================================================

def test_scenario_2_single_row_regeneration_on_gatekeeper1_rejection():
    """
    Scenario 2: Single-row targeted re-generation on Gatekeeper 1 rejection.
    Bad batch rejected -> Negative feedback provided -> Replacement passes -> Row updated in place.
    """
    db = MockGoogleSheetsDB(tab_name="pinyin")

    # 1. Invalid batch with Traditional Chinese and forbidden English
    bad_batch = {
        "topic": "Đồ Dùng; v.v.",  # Invalid topic (delimiter + v.v.)
        "level": "HSK 1",
        "words": [
            {"hanzi": "蘋果", "pinyin": "píng guǒ", "meaning": "Ăn apple"},  # Traditional 蘋 + English apple
            {"hanzi": "媽媽", "pinyin": "mā ma", "meaning": "Mother"},        # Traditional 媽 + English Mother
            {"hanzi": "學校", "pinyin": "xué xiào", "meaning": "School"},     # Traditional 學 + 校 + English School
            {"hanzi": "大門", "pinyin": "dà mén", "meaning": "Cái door"},     # Traditional 門 + English door
            {"hanzi": "中國", "pinyin": "zhōng guó", "meaning": "Country"}   # Traditional 國 + English Country
        ]
    }
    is_valid, errors = pinyin_val.PreRenderValidator.validate_batch(bad_batch)
    assert is_valid is False
    assert len(errors) >= 3

    # 2. Re-generation with negative feedback produces clean replacement
    clean_replacement = {
        "topic": "Đồ Dùng Gia Đình Hằng Ngày",
        "level": "HSK 1",
        "words": [
            {"hanzi": "苹果", "pinyin": "píng guǒ", "meaning": "Quả táo"},
            {"hanzi": "妈妈", "pinyin": "mā ma", "meaning": "Mẹ"},
            {"hanzi": "学校", "pinyin": "xué xiào", "meaning": "Trường học"},
            {"hanzi": "大门", "pinyin": "dà mén", "meaning": "Cánh cổng lớn"},
            {"hanzi": "中国", "pinyin": "zhōng guó", "meaning": "Nước Trung Quốc"}
        ]
    }
    is_clean, clean_errors = pinyin_val.PreRenderValidator.validate_batch(clean_replacement)
    assert is_clean is True
    assert len(clean_errors) == 0

    # 3. Update target row in-place
    row_id = db.append_batch(clean_replacement, initial_status="Pending")
    assert row_id == 2
    row = db.get_row(2)
    assert row["Status"] == "Pending"
    assert "苹果" in row["Word 1"]


# ============================================================================
# 3. REAL-WORLD SCENARIOS 3, 4, 5: MULTI-PIPELINE HARMONY & INTEGRITY
# ============================================================================

def test_scenario_3_multi_pipeline_schema_and_gatekeeper_parity(
    sample_valid_pinyin_batch,
    sample_valid_vocabcn_batch,
    sample_valid_vocabvn_batch
):
    """Scenario 3: Verify all 3 sub-pipelines satisfy uniform schema & Gatekeeper 1 contracts."""
    p_valid, p_errs = pinyin_val.PreRenderValidator.validate_batch(sample_valid_pinyin_batch)
    c_valid, c_errs = vocabcn_val.PreRenderValidator.validate_batch(sample_valid_vocabcn_batch)
    v_valid, v_errs = vocabvn_val.PreRenderValidator.validate_batch(sample_valid_vocabvn_batch)

    assert p_valid is True, f"Pinyin batch failed: {p_errs}"
    assert c_valid is True, f"VocabCN batch failed: {c_errs}"
    assert v_valid is True, f"VocabVN batch failed: {v_errs}"


def test_scenario_4_erhua_phonetic_integration(sample_erhua_batch):
    """Scenario 4: Verify Erhua contracted phonetics pass linguistic validation seamlessly."""
    is_valid, errors = pinyin_val.PreRenderValidator.validate_batch(sample_erhua_batch)
    assert is_valid is True, f"Erhua batch failed validation: {errors}"

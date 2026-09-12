#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared fixtures and testing helpers for LeLe Chinese Quiz E2E Test Suite.
Provides opaque-box fixtures, mock payloads, schema constants, and test helpers.
"""

import os
import sys
import pytest
from typing import Dict, Any, List

# Ensure quiz root and sub-pipeline packages are importable
QUIZ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if QUIZ_ROOT not in sys.path:
    sys.path.insert(0, QUIZ_ROOT)

for pipeline_dir in ["pinyinquiz", "vocabCNquiz", "vocabVNquiz"]:
    p_path = os.path.join(QUIZ_ROOT, pipeline_dir)
    if p_path not in sys.path:
        sys.path.insert(0, p_path)

STANDARD_16_COLUMNS = [
    "#",
    "Topic",
    "Level",
    "Status",
    "Word 1",
    "Word 2",
    "Word 3",
    "Word 4",
    "Word 5",
    "metadata",
    "Video",
    "Youtube",
    "Tiktok",
    "Facebook",
    "Created At",
    "Notes"
]

SAMPLE_VALID_BATCH_PINYIN: Dict[str, Any] = {
    "id": "101",
    "topic": "Đồ Ăn & Thức Uống Hằng Ngày",
    "level": "HSK 1",
    "words": [
        {"hanzi": "苹果", "pinyin": "píng guǒ", "meaning": "Quả táo"},
        {"hanzi": "米饭", "pinyin": "mǐ fàn", "meaning": "Cơm trắng"},
        {"hanzi": "面条", "pinyin": "miàn tiáo", "meaning": "Mì sợi dai"},
        {"hanzi": "喝水", "pinyin": "hē shuǐ", "meaning": "Uống nước lọc"},
        {"hanzi": "牛奶", "pinyin": "niú nǎi", "meaning": "Sữa bò tươi"}
    ]
}

SAMPLE_VALID_BATCH_VOCABCN: Dict[str, Any] = {
    "id": "102",
    "topic": "Giao Thông & Đi Lại",
    "level": "HSK 2",
    "words": [
        {"hanzi": "飞机", "pinyin": "fēi jī", "meaning": "Máy bay"},
        {"hanzi": "出租车", "pinyin": "chū zū chē", "meaning": "Xe taxi"},
        {"hanzi": "公共汽车", "pinyin": "gōng gòng qì chē", "meaning": "Xe buýt công cộng"},
        {"hanzi": "火车站", "pinyin": "huǒ chē zhàn", "meaning": "Ga tàu hỏa"},
        {"hanzi": "飞机场", "pinyin": "fēi jī chǎng", "meaning": "Sân bay quốc tế"}
    ]
}

SAMPLE_VALID_BATCH_VOCABVN: Dict[str, Any] = {
    "id": "103",
    "topic": "Đồ Dùng Học Tập & Văn Phòng",
    "level": "HSK 1",
    "words": [
        {"hanzi": "书包", "pinyin": "shū bāo", "meaning": "Cặp sách"},
        {"hanzi": "铅笔", "pinyin": "qiān bǐ", "meaning": "Bút chì"},
        {"hanzi": "橡皮", "pinyin": "xiàng pí", "meaning": "Cục tẩy"},
        {"hanzi": "尺子", "pinyin": "chǐ zi", "meaning": "Cây thước kẻ"},
        {"hanzi": "本子", "pinyin": "běn zi", "meaning": "Quyển vở"}
    ]
}

SAMPLE_ERHUA_BATCH: Dict[str, Any] = {
    "id": "104",
    "topic": "Từ Ngữ Uốn Lưỡi Erhua",
    "level": "HSK 2",
    "words": [
        {"hanzi": "哪儿", "pinyin": "nǎr", "meaning": "Ở đâu"},
        {"hanzi": "这儿", "pinyin": "zhèr", "meaning": "Ở đây"},
        {"hanzi": "那儿", "pinyin": "nàr", "meaning": "Ở đó"},
        {"hanzi": "玩儿", "pinyin": "wánr", "meaning": "Chơi đùa"},
        {"hanzi": "花儿", "pinyin": "huār", "meaning": "Bông hoa"}
    ]
}


@pytest.fixture
def standard_16_columns() -> List[str]:
    return list(STANDARD_16_COLUMNS)


@pytest.fixture
def sample_valid_pinyin_batch() -> Dict[str, Any]:
    return dict(SAMPLE_VALID_BATCH_PINYIN)


@pytest.fixture
def sample_valid_vocabcn_batch() -> Dict[str, Any]:
    return dict(SAMPLE_VALID_BATCH_VOCABCN)


@pytest.fixture
def sample_valid_vocabvn_batch() -> Dict[str, Any]:
    return dict(SAMPLE_VALID_BATCH_VOCABVN)


@pytest.fixture
def sample_erhua_batch() -> Dict[str, Any]:
    return dict(SAMPLE_ERHUA_BATCH)


def pytest_sessionfinish(session, exitstatus):
    """Ensure exFAT partition remains 100% clean of bytecode and cache after test run."""
    import shutil
    for root, dirs, files in os.walk(QUIZ_ROOT, topdown=False):
        for f in files:
            if f.endswith(".pyc"):
                try:
                    os.remove(os.path.join(root, f))
                except Exception:
                    pass
        for d in dirs:
            if d in ("__pycache__", ".pytest_cache"):
                try:
                    shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                except Exception:
                    pass

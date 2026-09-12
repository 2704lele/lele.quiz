import os
import sys
import pytest

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from src.gsheet_manager import GSheetManager, STANDARD_COLUMNS

def test_standard_columns():
    """Verify that the standard schema has exactly 16 columns in correct order."""
    expected = [
        "#", "Topic", "Level", "Status", "Word 1", "Word 2", "Word 3",
        "Word 4", "Word 5", "metadata", "Video", "Youtube", "Tiktok",
        "Facebook", "Created At", "Notes"
    ]
    assert STANDARD_COLUMNS == expected
    assert len(STANDARD_COLUMNS) == 16

def test_parse_word_entry():
    """Test word parsing utility for standard and extended formats."""
    gm = GSheetManager()
    
    # 3-part format: hanzi | pinyin | meaning
    res3 = gm.parse_word_entry("爸爸 | bà ba | Bố / Ba")
    assert res3["hanzi"] == "爸爸"
    assert res3["pinyin"] == "bà ba"
    assert res3["meaning"] == "Bố / Ba"
    
    # 4-part format: hanzi | pinyin | hidden | meaning
    res4 = gm.parse_word_entry("书包 | shū bāo | sh_ b__ | Cặp sách")
    assert res4["hanzi"] == "书包"
    assert res4["pinyin"] == "shū bāo"
    assert res4["hidden_pinyin"] == "sh_ b__"
    assert res4["meaning"] == "Cặp sách"
    
    # Empty entry
    empty = gm.parse_word_entry("")
    assert empty["hanzi"] == ""
    assert empty["pinyin"] == ""

def test_live_vocabcn_sheet_state():
    """Verify live Google Sheets tab vocabCN audit and cleanup invariants."""
    gm = GSheetManager()
    ws = gm.worksheet
    
    # 1. Total populated rows must be at least 3 (Header + Row 2 + Row 3 + optional Row 4+)
    all_values = ws.get_all_values()
    assert len(all_values) >= 3, f"Expected at least 3 populated rows, got {len(all_values)}"
    
    # 2. Header Row
    header = all_values[0]
    assert header == STANDARD_COLUMNS
    
    # 3. Row 2: #2, Gia Đình Thân Yêu, Video, valid video link
    row_2 = all_values[1]
    assert row_2[0] == "#2"
    assert row_2[1] == "Gia Đình Thân Yêu"
    assert row_2[2] == "HSK 1"
    assert row_2[3] == "Video"
    assert "https://drive.google.com/file/d/" in row_2[10]
    
    # 4. Row 3: #3, Đồ Dùng Học Tập, Ready, valid video link
    row_3 = all_values[2]
    assert row_3[0] == "#3"
    assert row_3[1] == "Đồ Dùng Học Tập"
    assert row_3[2] == "HSK 1"
    assert row_3[3] == "Ready"
    assert "https://drive.google.com/file/d/" in row_3[10]

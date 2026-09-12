import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import menu


def test_menu_constants():
    assert "pinyin" in menu.EDGE_ROUTERS
    assert "vocabcn" in menu.EDGE_ROUTERS
    assert "vocabvn" in menu.EDGE_ROUTERS
    assert "pinyin" in menu.VALIDATORS
    assert "vocabcn" in menu.VALIDATORS
    assert "vocabvn" in menu.VALIDATORS


def test_menu_banner_output(capsys):
    menu.print_banner()
    captured = capsys.readouterr()
    assert "LELE CHINESE QUIZ" in captured.out
    assert "[1]" in captured.out
    assert "[4]" in captured.out
    assert "[5]" in captured.out
    assert "Mạng Xã Hội" in captured.out


def test_publish_social_batch_dry_run():
    from scripts.publish_social_batch import publish_row_to_social
    res = publish_row_to_social("pinyin", 2, channels="all", dry_run=True)
    assert res["status"] == "success"
    assert res["row_id"] == 2
    assert res["tab"] == "pinyin"
    assert len(res["channels"]) > 0

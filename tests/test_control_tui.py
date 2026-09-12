import os
import sys
import asyncio
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from control_tui import LeLeControlApp, SAMPLE_TEMPLATES, EDGE_ROUTER_URLS


def test_control_tui_app_instantiation():
    app = LeLeControlApp(auto_fetch=False)
    assert app is not None
    assert "pinyin" in app.validators
    assert "vocabcn" in app.validators
    assert "vocabvn" in app.validators


def test_sample_templates_integrity():
    for pipe in ["pinyin", "vocabcn", "vocabvn"]:
        assert pipe in SAMPLE_TEMPLATES
        tmpl = SAMPLE_TEMPLATES[pipe]
        assert "topic" in tmpl
        assert "level" in tmpl
        assert len(tmpl["words"]) == 5
        for w in tmpl["words"]:
            assert "hanzi" in w
            assert "pinyin" in w
            assert "meaning" in w


def test_edge_router_urls_mapping():
    assert "pinyin" in EDGE_ROUTER_URLS
    assert "vocabcn" in EDGE_ROUTER_URLS
    assert "vocabvn" in EDGE_ROUTER_URLS
    assert EDGE_ROUTER_URLS["pinyin"].startswith("https://")


def test_control_tui_widgets_composition():
    async def _runner():
        app = LeLeControlApp(auto_fetch=False)
        async with app.run_test() as pilot:
            assert app.query_one("#main-tabs") is not None
            assert app.query_one("#monitor-table") is not None
            assert app.query_one("#select-monitor-tab") is not None
            assert app.query_one("#select-ideation-pipeline") is not None
            assert app.query_one("#select-manual-pipeline") is not None
            assert app.query_one("#btn-validate-manual") is not None
            assert app.query_one("#btn-submit-manual") is not None
            assert app.query_one("#btn-action-render") is not None
            assert app.query_one("#btn-action-qc") is not None

    asyncio.run(_runner())


def test_control_tui_manual_validation_pass_and_fail():
    async def _runner():
        app = LeLeControlApp(auto_fetch=False)
        async with app.run_test() as pilot:
            # 1. Clean template passes Gatekeeper 1
            app.action_load_template("pinyin")
            is_ok, errors = app.run_manual_gatekeeper_validation()
            assert is_ok is True
            assert len(errors) == 0

            # 2. Traditional Chinese rejected
            from textual.widgets import Input
            app.query_one("#input-hz-1", Input).value = "蘋果"  # Traditional
            is_ok, errors = app.run_manual_gatekeeper_validation()
            assert is_ok is False
            assert any("phồn thể" in e.lower() or "traditional" in e.lower() or "giản thể" in e.lower() for e in errors)

    asyncio.run(_runner())

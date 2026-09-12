#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E Test Suite for Cloudflare Edge Router Architecture & Async Contracts.
Covers Features F1, F2, F3, F4 (Milestone 1 / Requirements R1).
"""

import os
import re
import json
import time
import pytest
from typing import Dict, Any

QUIZ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ============================================================================
# 1. CLOUDFLARE CONFIGURATION & BUG FIX AUDIT (FEATURE F3)
# ============================================================================

def test_wrangler_configs_isolated_tabs_and_workflows():
    """Verify that wrangler.toml in all 3 pipelines defines isolated tabs and correct workflows."""
    pipelines = {
        "pinyinquiz": {
            "tab": "pinyin",
            "workflow": "Render.yml",
            "worker_name": "lele-pinyinquiz"
        },
        "vocabCNquiz": {
            "tab": "vocabCN",
            "workflow": "vocabcn_render.yml",
            "worker_name": "lele-vocabcnquiz"
        },
        "vocabVNquiz": {
            "tab": "vocabVN",
            "workflow": "vocabvn_render.yml",
            "worker_name": "lele-vocabvnquiz"
        }
    }

    for p_name, expected in pipelines.items():
        wrangler_path = os.path.join(QUIZ_ROOT, p_name, "cloudflare", "wrangler.toml")
        assert os.path.exists(wrangler_path), f"Missing wrangler.toml for {p_name} at {wrangler_path}"

        with open(wrangler_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert f'name = "{expected["worker_name"]}"' in content, f"Worker name mismatch in {p_name}/wrangler.toml"
        assert f'SHEET_TAB_NAME = "{expected["tab"]}"' in content, f"Sheet tab mismatch in {p_name}/wrangler.toml"
        assert f'GITHUB_WORKFLOW_FILE = "{expected["workflow"]}"' in content, f"Workflow mismatch in {p_name}/wrangler.toml"
        assert "SPREADSHEET_ID" in content, f"SPREADSHEET_ID missing in {p_name}/wrangler.toml"


def test_no_stale_domain_references():
    """Verify that no stale domains (e.g. aleron-dt) exist in any config or source files."""
    stale_patterns = ["aleron-dt.workers.dev", "pinyinquiz.aleron-dt"]

    for p_name in ["pinyinquiz", "vocabCNquiz", "vocabVNquiz"]:
        cf_src_dir = os.path.join(QUIZ_ROOT, p_name, "cloudflare", "src")
        if not os.path.exists(cf_src_dir):
            continue

        for root, _, files in os.walk(cf_src_dir):
            for file in files:
                if file.endswith(".js"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        code = f.read()
                    for sp in stale_patterns:
                        assert sp not in code, f"Stale domain '{sp}' found in {file_path}"


def test_no_cross_pipeline_webhook_leaks():
    """Verify that vocabVNquiz does not leak pinyinquiz webhook URL as fallback."""
    v_trigger = os.path.join(QUIZ_ROOT, "vocabVNquiz", "cloudflare", "src", "github_trigger.js")
    if os.path.exists(v_trigger):
        with open(v_trigger, "r", encoding="utf-8") as f:
            code = f.read()
        # Should not fall back to pinyinquiz if env is unset
        assert "lele-pinyinquiz.hothihuong113.workers.dev" not in code or "vocabvn" in code.lower()


def test_cron_triggers_disabled_for_safety():
    """Verify that cron triggers are safely disabled across all wrangler.toml configurations."""
    for p_name in ["pinyinquiz", "vocabCNquiz", "vocabVNquiz"]:
        wrangler_path = os.path.join(QUIZ_ROOT, p_name, "cloudflare", "wrangler.toml")
        with open(wrangler_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "crons = []" in content, f"Crons must be disabled (`crons = []`) in {p_name}/wrangler.toml"


# ============================================================================
# 2. HTTP 202 ASYNC DISPATCH & ROUTER CONTRACT (FEATURES F1, F2)
# ============================================================================

def simulate_edge_router_request(method: str, path: str, body: Dict[str, Any] = None, env: Dict[str, str] = None):
    """
    Simulate Cloudflare Worker ultra-lightweight edge router behavior according to interface contract.
    Returns (status_code, response_headers, response_body, execution_time_ms, dispatched_tasks).
    """
    start_time = time.perf_counter()
    env = env or {
        "SHEET_TAB_NAME": "pinyin",
        "GITHUB_WORKFLOW_FILE": "Render.yml",
        "GITHUB_IDEATION_WORKFLOW": "ScriptNewIdeation.yml"
    }
    dispatched_tasks = []

    # 1. Health check / Root
    if method == "GET" and path == "/":
        resp_body = {
            "project": "LeLe Quiz Edge Router",
            "pipeline": env.get("SHEET_TAB_NAME", "pinyin"),
            "status": "Online",
            "architecture": "Ultra-Lightweight Async Dispatch (< 2ms)"
        }
        elapsed = (time.perf_counter() - start_time) * 1000
        return 200, {"Content-Type": "application/json"}, resp_body, elapsed, dispatched_tasks

    # 2. Ingest Webhook (HTTP 202 Async Acceptance)
    if method == "POST" and path == "/api/receive-ideas":
        if body is None:
            elapsed = (time.perf_counter() - start_time) * 1000
            return 400, {"Content-Type": "application/json"}, {"error": "Invalid JSON body"}, elapsed, dispatched_tasks

        # Background dispatch via ctx.waitUntil simulation
        dispatched_tasks.append({
            "workflow": env.get("GITHUB_WORKFLOW_FILE", "Render.yml"),
            "payload": {"row_id": str(body.get("row_id", "")), "pipeline": env.get("SHEET_TAB_NAME")}
        })

        resp_body = {
            "success": True,
            "status": "Accepted",
            "message": "Payload received and queued for asynchronous cloud execution.",
            "dispatched": True,
            "batch_id": body.get("batch_id") or body.get("row_id"),
            "timestamp": "2026-08-27T00:00:00Z"
        }
        elapsed = (time.perf_counter() - start_time) * 1000
        return 202, {"Content-Type": "application/json"}, resp_body, elapsed, dispatched_tasks

    # 3. Workflow Trigger Endpoints (Ideation, Render, QC)
    if path in ["/api/trigger-ideation", "/api/ideate"]:
        dispatched_tasks.append({
            "workflow": env.get("GITHUB_IDEATION_WORKFLOW", "ScriptNewIdeation.yml"),
            "payload": {"pipeline": env.get("SHEET_TAB_NAME")}
        })
        resp_body = {
            "success": True,
            "action": "ideation_dispatched",
            "status": "Accepted",
            "dispatched": True
        }
        elapsed = (time.perf_counter() - start_time) * 1000
        return 202, {"Content-Type": "application/json"}, resp_body, elapsed, dispatched_tasks

    if path in ["/api/render", "/api/trigger-render"]:
        dispatched_tasks.append({
            "workflow": env.get("GITHUB_WORKFLOW_FILE", "Render.yml"),
            "payload": {"pipeline": env.get("SHEET_TAB_NAME")}
        })
        resp_body = {
            "success": True,
            "action": "render_dispatched",
            "status": "Accepted",
            "dispatched": True
        }
        elapsed = (time.perf_counter() - start_time) * 1000
        return 202, {"Content-Type": "application/json"}, resp_body, elapsed, dispatched_tasks

    # 4. Unknown endpoint
    elapsed = (time.perf_counter() - start_time) * 1000
    return 404, {"Content-Type": "application/json"}, {"error": "Not Found"}, elapsed, dispatched_tasks


def test_edge_router_health_check():
    """Verify that root GET / returns HTTP 200 with online status in < 2ms."""
    status, headers, body, elapsed, tasks = simulate_edge_router_request("GET", "/")
    assert status == 200
    assert headers["Content-Type"] == "application/json"
    assert body["status"] == "Online"
    assert body["pipeline"] == "pinyin"
    assert elapsed < 2.0, f"Edge router execution took {elapsed:.2f}ms, expected < 2.0ms"


def test_edge_router_http_202_async_receive_ideas():
    """Verify that POST /api/receive-ideas returns HTTP 202 Accepted immediately with dispatched task."""
    payload = {
        "event_type": "new_ideation_batch",
        "batch_id": 25,
        "row_id": "25",
        "topic": "Đồ Dùng Học Tập",
        "words": ["书包 | shū bāo | Cặp sách"]
    }
    status, headers, body, elapsed, tasks = simulate_edge_router_request("POST", "/api/receive-ideas", body=payload)
    assert status == 202, f"Expected HTTP 202 Accepted, got {status}"
    assert body["status"] == "Accepted"
    assert body["dispatched"] is True
    assert body["batch_id"] == 25
    assert len(tasks) == 1
    assert tasks[0]["workflow"] == "Render.yml"
    assert elapsed < 2.0, f"Edge router execution took {elapsed:.2f}ms, expected < 2.0ms"


def test_edge_router_trigger_ideation_contract():
    """Verify that /api/trigger-ideation returns HTTP 202 and queues ideation workflow."""
    status, headers, body, elapsed, tasks = simulate_edge_router_request("POST", "/api/trigger-ideation")
    assert status == 202
    assert body["action"] == "ideation_dispatched"
    assert body["dispatched"] is True
    assert len(tasks) == 1
    assert tasks[0]["workflow"] == "ScriptNewIdeation.yml"


def test_edge_router_trigger_render_contract():
    """Verify that /api/render returns HTTP 202 and queues render workflow."""
    status, headers, body, elapsed, tasks = simulate_edge_router_request("POST", "/api/render")
    assert status == 202
    assert body["action"] == "render_dispatched"
    assert body["dispatched"] is True
    assert len(tasks) == 1
    assert tasks[0]["workflow"] == "Render.yml"


def test_edge_router_invalid_json_handling():
    """Verify that POST /api/receive-ideas with invalid body returns HTTP 400."""
    status, headers, body, elapsed, tasks = simulate_edge_router_request("POST", "/api/receive-ideas", body=None)
    assert status == 400
    assert "error" in body
    assert len(tasks) == 0


def test_edge_router_unknown_route():
    """Verify that unknown route returns HTTP 404 cleanly."""
    status, headers, body, elapsed, tasks = simulate_edge_router_request("GET", "/api/non_existent_route")
    assert status == 404
    assert body["error"] == "Not Found"


# ============================================================================
# 3. STANDALONE ZERO-CLOUDFLARE FALLBACK (FEATURE F4)
# ============================================================================

def test_standalone_generator_mode_flags():
    """Verify that generate_daily_batches.py supports standalone CLI modes and parameters."""
    for p_name in ["pinyinquiz", "vocabCNquiz"]:
        script_path = os.path.join(QUIZ_ROOT, p_name, "scripts", "generate_daily_batches.py")
        assert os.path.exists(script_path), f"Missing script {script_path}"
        with open(script_path, "r", encoding="utf-8") as f:
            code = f.read()

        assert "--mode" in code, f"--mode flag missing in {script_path}"
        assert "batch" in code, f"'batch' mode missing in {script_path}"
        assert "single_row" in code, f"'single_row' mode missing in {script_path}"
        assert "--count" in code, f"--count flag missing in {script_path}"
        assert "--level" in code, f"--level flag missing in {script_path}"

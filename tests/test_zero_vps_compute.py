#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E Test Suite for Zero-VPS Compute Enforcement Invariant.
Covers Feature F11 (Milestone 4 / Requirements R4).
Verifies that 0% Manim rendering compute executes on the local VPS host.
"""

import os
import subprocess
import pytest

QUIZ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_no_active_manim_processes_on_vps():
    """Verify that no Manim rendering processes are currently running on the VPS host."""
    try:
        ps_output = subprocess.check_output(["ps", "aux"], text=True)
    except Exception as e:
        pytest.skip(f"Unable to run ps aux: {e}")

    # Check for active Manim processes
    for line in ps_output.splitlines():
        if "manim" in line.lower() and "pytest" not in line.lower() and "test_zero_vps" not in line.lower():
            # Check if it's an actual rendering process rather than editor/indexer
            if "render" in line.lower() or "scene" in line.lower() or "-qh" in line.lower():
                pytest.fail(f"Zero-VPS compute violation! Detected active Manim render process on host: {line}")


def test_no_active_ffmpeg_render_processes_on_vps():
    """Verify that no heavy video encoding ffmpeg processes are running on the VPS host."""
    try:
        ps_output = subprocess.check_output(["ps", "aux"], text=True)
    except Exception as e:
        pytest.skip(f"Unable to run ps aux: {e}")

    for line in ps_output.splitlines():
        if "ffmpeg" in line.lower() and "partial_movie_files" in line.lower():
            pytest.fail(f"Zero-VPS compute violation! Detected active FFmpeg rendering process on host: {line}")


def test_rendering_engine_isolated_to_cloud_workflows():
    """Verify that Manim render pipelines are configured for cloud runners."""
    # Check that cloud workflows exist or render engine specifies GitHub Actions runner commands
    for p_name in ["pinyinquiz", "vocabCNquiz", "vocabVNquiz"]:
        wrangler_path = os.path.join(QUIZ_ROOT, p_name, "cloudflare", "wrangler.toml")
        if os.path.exists(wrangler_path):
            with open(wrangler_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "GITHUB_WORKFLOW_FILE" in content, f"Cloud workflow binding missing in {p_name}/wrangler.toml"

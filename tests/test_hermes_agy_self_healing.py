#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Hermes to Antigravity CLI Self-Healing Bridge.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

QUIZ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if QUIZ_ROOT not in sys.path:
    sys.path.insert(0, QUIZ_ROOT)

from scripts.hermes_agy_repair import HermesAgyRepairBridge, trigger_agy_self_heal


class TestHermesAgySelfHealing(unittest.TestCase):

    def setUp(self):
        self.bridge = HermesAgyRepairBridge(workspace_dir=QUIZ_ROOT)

    def test_format_repair_prompt_contains_all_invariants(self):
        error_msg = "ValidationError: Found English character in Vietnamese definition"
        prompt = self.bridge.format_repair_prompt(
            error_context=error_msg,
            failing_file="vocabCNquiz/src/gsheet_manager.py",
            task_goal="Fix regex parser to eliminate false positive English detection",
            row_id=12,
            tab_name="vocabCN"
        )

        # Verify all invariants and critical parameters
        self.assertIn("HERMES AUTONOMOUS SELF-HEALING DISPATCH", prompt)
        self.assertIn(error_msg, prompt)
        self.assertIn("vocabCNquiz/src/gsheet_manager.py", prompt)
        self.assertIn("Impacted Row ID: 12", prompt)
        self.assertIn("Impacted Google Sheets Tab: vocabCN", prompt)
        self.assertIn("ZERO-VPS BAN", prompt)
        self.assertIn("Sheet Row Number == Batch ID (#)", prompt)
        self.assertIn("https://drive.google.com/file/d/{FILE_ID}/view?usp=drivesdk", prompt)
        self.assertIn("100% Simplified Chinese", prompt)
        self.assertIn("100% concise Vietnamese", prompt)
        self.assertIn("pytest tests/", prompt)

    @patch("subprocess.run")
    def test_dispatch_repair_success(self, mock_subprocess_run):
        # Mock AGY CLI execution success
        mock_agy_proc = MagicMock()
        mock_agy_proc.returncode = 0
        mock_agy_proc.stdout = "Applied targeted bugfix in parser.py\n236 passed in 12s"
        mock_agy_proc.stderr = ""

        # Mock Pytest verification run success
        mock_pytest_proc = MagicMock()
        mock_pytest_proc.returncode = 0
        mock_pytest_proc.stdout = "236 passed in 5.2s"
        mock_pytest_proc.stderr = ""

        mock_subprocess_run.side_effect = [mock_agy_proc, mock_pytest_proc]

        res = self.bridge.dispatch_repair(
            error_context="DivisionByZero in scene generator",
            failing_file="src/scene_generator.py",
            task_goal="Prevent division by zero when word length is 1"
        )

        self.assertTrue(res["success"])
        self.assertEqual(res["agy_exit_code"], 0)
        self.assertTrue(res["pytest_passed"])
        self.assertIn("236 passed", res["pytest_summary"])

    @patch("subprocess.run")
    def test_dispatch_repair_agy_failure(self, mock_subprocess_run):
        mock_agy_proc = MagicMock()
        mock_agy_proc.returncode = 1
        mock_agy_proc.stdout = "Failed to apply edit"
        mock_agy_proc.stderr = "SyntaxError in fix"

        mock_pytest_proc = MagicMock()
        mock_pytest_proc.returncode = 1
        mock_pytest_proc.stdout = "1 failed, 235 passed"
        mock_pytest_proc.stderr = ""

        mock_subprocess_run.side_effect = [mock_agy_proc, mock_pytest_proc]

        res = self.bridge.dispatch_repair(
            error_context="Some error",
            failing_file="src/config.py"
        )

        self.assertFalse(res["success"])
        self.assertEqual(res["agy_exit_code"], 1)
        self.assertFalse(res["pytest_passed"])

    def test_trigger_agy_self_heal_function(self):
        with patch.object(HermesAgyRepairBridge, "dispatch_repair") as mock_dispatch:
            mock_dispatch.return_value = {"success": True, "pytest_passed": True}
            res = trigger_agy_self_heal("test error", failing_file="test.py")
            self.assertTrue(res["success"])
            mock_dispatch.assert_called_once()


if __name__ == "__main__":
    unittest.main()

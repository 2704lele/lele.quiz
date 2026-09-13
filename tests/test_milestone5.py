import os
import sys
import yaml
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.run_morning_audit import (
    CANONICAL_DRIVE_SUBFOLDERS,
    GDRIVE_ROOT_FOLDER_ID,
    audit_google_drive_storage,
    get_drive_service,
    get_telegram_creds,
)
from scripts.enforce_row_height_21px import audit_and_enforce_row_height, TARGET_ROW_HEIGHT_PX


def test_workflow_03_structure_and_dependencies():
    """Verify that 03_quiz_morning_audit.yml has correct schedule, rich in pip install, and zero-leak vault."""
    wf_path = os.path.join(PROJECT_ROOT, ".github", "workflows", "03_quiz_morning_audit.yml")
    assert os.path.exists(wf_path), f"Workflow file not found: {wf_path}"

    with open(wf_path, "r", encoding="utf-8") as f:
        content = f.read()
        parsed = yaml.safe_load(content)

    # Verify schedule trigger (05:01 AM GMT+7 -> 22:01 UTC)
    on_block = parsed.get("on") or parsed.get(True)
    cron_expr = on_block["schedule"][0]["cron"]
    assert cron_expr == "1 22 * * *", f"Expected cron '1 22 * * *', got '{cron_expr}'"

    # Verify rich in pip install
    assert "rich" in content, "Workflow missing 'rich' in pip install step"

    # Verify zero-leak vault step
    assert "Configure Zero-Leak Vault Credentials" in content, "Missing Zero-Leak Vault step"
    assert "chmod 600" in content, "Missing chmod 600 permission hardening"


def test_gdrive_storage_purity_live():
    """Verify Google Drive storage purity: strictly 5 canonical subfolders, 0 orphan files."""
    drive_service = get_drive_service()
    assert drive_service is not None, "Failed to initialize Google Drive service"

    audit_res = audit_google_drive_storage(service=drive_service, root_folder_id=GDRIVE_ROOT_FOLDER_ID, assert_purity=True)
    assert audit_res["status"] == "PASSED"
    assert audit_res["folder_count"] == 5
    assert audit_res["orphan_count"] == 0
    assert audit_res["missing_canonical"] == []
    assert audit_res["unexpected_folders"] == []


def test_row_height_invariant_enforcement():
    """Verify that audit_and_enforce_row_height verifies 100% of rows at 21px."""
    res = audit_and_enforce_row_height(TARGET_ROW_HEIGHT_PX)
    for tab, info in res.items():
        assert info["all_target"] is True, f"Tab {tab} has rows not meeting 21px invariant: {info}"


def test_telegram_credential_resolution_and_format():
    """Verify that Telegram credentials are dynamically resolved and non-empty."""
    token, chat_id = get_telegram_creds()
    assert token, "Telegram bot token should be resolved"
    assert chat_id, "Telegram chat ID should be resolved"
    assert ":" in token, "Telegram bot token format invalid (expected '<bot_id>:<hash>')"
    assert chat_id.lstrip("-").isdigit(), "Telegram chat ID should be numeric"

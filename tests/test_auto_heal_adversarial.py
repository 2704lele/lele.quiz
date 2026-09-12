# -*- coding: utf-8 -*-
"""
Empirical Adversarial Stress Suite for Auto-Healing Engine (Milestone M2).
Author: challenger_m2_1

Adversarially tests:
1. CLI modes (--check, --heal, --check --json, --heal --json)
2. Stdout JSON purity (no ANSI codes, no logger bleed, pure jq parseable)
3. Invalid flags and CLI edge handling
4. Missing vault files & credential corruption handling (GDrive, Buffer, Colab)
5. Network error simulations (HTTP 503, socket timeouts)
6. Hung VM detection (>4800s) and verification of colab stop -s execution
7. Blacklist enforcement against aleron.dt@gmail.com
8. GSheets schema corruption and 21px enforcement
"""

import os
import sys
import json
import time
import re
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from google.oauth2.credentials import Credentials as UserCreds
import pytest

QUIZ_ROOT = Path(__file__).resolve().parent.parent
if str(QUIZ_ROOT) not in sys.path:
    sys.path.insert(0, str(QUIZ_ROOT))

from scripts.auto_heal import (
    AutoHealEngine,
    TARGET_GDRIVE_FOLDERS,
    BUFFER_1_TARGET_CHANNELS,
    STANDARD_16_COLUMNS,
    COLAB_EXECUTION_TIMEOUT_SEC
)

ANSI_ESCAPE_RE = re.compile(r'\[[0-9;]*[a-zA-Z]')


def test_cli_json_purity_stdout_check_mode():
    """Verify ./auto_heal.sh --check --json emits 100% clean JSON on stdout with 0 ANSI codes."""
    wrapper_path = QUIZ_ROOT / 'auto_heal.sh'
    res = subprocess.run(
        [str(wrapper_path), '--check', '--json'],
        cwd=QUIZ_ROOT,
        capture_output=True,
        text=True
    )
    assert res.returncode in (0, 1), f'Unexpected return code {res.returncode}: {res.stderr}'

    # Verify stdout has NO ANSI escape sequences
    ansi_matches = ANSI_ESCAPE_RE.findall(res.stdout)
    assert len(ansi_matches) == 0, f'Found ANSI escape codes in stdout: {ansi_matches}'

    # Verify stdout is strictly valid JSON
    assert res.stdout.strip().startswith('{'), 'stdout must start with {'
    assert res.stdout.strip().endswith('}'), 'stdout must end with }'
    data = json.loads(res.stdout)
    assert 'overall_healthy' in data
    assert 'subsystems' in data
    assert len(data['subsystems']) == 5

    # Verify stderr received the logs, not stdout
    assert '[AutoHeal]' in res.stderr or '[INFO]' in res.stderr or 'file_cache' in res.stderr
    assert '[AutoHeal]' not in res.stdout


def test_cli_json_purity_stdout_heal_mode():
    """Verify ./auto_heal.sh --heal --json emits 100% clean JSON on stdout with 0 ANSI codes."""
    wrapper_path = QUIZ_ROOT / 'auto_heal.sh'
    res = subprocess.run(
        [str(wrapper_path), '--heal', '--json'],
        cwd=QUIZ_ROOT,
        capture_output=True,
        text=True
    )
    assert res.returncode in (0, 1), f'Unexpected return code {res.returncode}: {res.stderr}'

    ansi_matches = ANSI_ESCAPE_RE.findall(res.stdout)
    assert len(ansi_matches) == 0, f'Found ANSI escape codes in stdout: {ansi_matches}'

    data = json.loads(res.stdout)
    assert data['mode'] == 'heal'
    assert 'subsystems' in data


def test_cli_invalid_flag_rejection():
    """Verify invalid flags produce exit code 2 and helpful error without crashing."""
    wrapper_path = QUIZ_ROOT / 'auto_heal.sh'
    res = subprocess.run(
        [str(wrapper_path), '--invalid-flag-xyz'],
        cwd=QUIZ_ROOT,
        capture_output=True,
        text=True
    )
    assert res.returncode == 2
    assert 'unrecognized arguments' in res.stderr.lower()
    assert res.stdout == ''


def test_missing_user_oauth2_graceful_fallback(tmp_path):
    """Simulate missing user_oauth2.json: engine must fallback to Service Account without crashing."""
    engine = AutoHealEngine(workspace_dir=QUIZ_ROOT)
    fake_oauth_path = tmp_path / 'non_existent_oauth.json'

    with patch('scripts.auto_heal.USER_OAUTH_PATH', fake_oauth_path):
        res = engine.diagnose_and_heal_gdrive(heal=False)
        assert res['oauth_user_token']['status'] == 'MISSING'
        # Service account should still be available and queried
        assert res['service_account']['status'] == 'AVAILABLE'
        # Status degrades to WARNING because user oauth is missing, but SA is active
        assert res['status'] == 'WARNING'
        assert len(res['target_folders']) == 6


def test_missing_all_google_credentials(tmp_path):
    """Simulate complete credential loss: engine must report status ERROR gracefully."""
    engine = AutoHealEngine(workspace_dir=QUIZ_ROOT)
    fake_path = tmp_path / 'non_existent.json'

    with patch('scripts.auto_heal.USER_OAUTH_PATH', fake_path),          patch('scripts.auto_heal.SA_PATH', fake_path):
        res = engine.diagnose_and_heal_gdrive(heal=False)
        assert res['status'] == 'ERROR'
        assert any('Failed to establish any Google Drive API connection' in err for err in res['errors'])


def test_corrupted_buffer_credentials_handling(tmp_path):
    """Simulate corrupted Buffer credentials.json (invalid JSON). Engine must report CORRUPT_JSON."""
    engine = AutoHealEngine(workspace_dir=QUIZ_ROOT)
    bad_buf = tmp_path / 'corrupted_buf.json'
    bad_buf.write_text('{broken json: 123', encoding='utf-8')

    with patch('scripts.auto_heal.BUFFER_CREDS_PATH', bad_buf):
        res = engine.diagnose_and_heal_buffer_social(heal=False)
        assert res['status'] == 'ERROR'
        assert res['credentials_file'] == 'CORRUPT_JSON'
        assert any('Error reading Buffer credentials' in err for err in res['errors'])


def test_missing_colab_registry_handling(tmp_path):
    """Simulate missing Colab registry.json: engine reports ERROR gracefully."""
    engine = AutoHealEngine(workspace_dir=QUIZ_ROOT)
    fake_reg = tmp_path / 'non_existent_registry.json'

    with patch('scripts.auto_heal.COLAB_REGISTRY_PATH', fake_reg):
        res = engine.diagnose_and_heal_colab_pool(heal=False)
        assert res['status'] == 'ERROR'
        assert any('Colab registry missing' in err for err in res['errors'])


def test_gdrive_network_error_simulation():
    """Simulate network error / 503 during GDrive folder querying."""
    engine = AutoHealEngine(workspace_dir=QUIZ_ROOT)

    mock_service = MagicMock()
    mock_service.files().get().execute.side_effect = ConnectionResetError('Connection reset by peer')

    with patch('scripts.auto_heal.USER_OAUTH_PATH', Path('/tmp/dummy_oauth')),          patch('scripts.auto_heal.build', return_value=mock_service),          patch('scripts.auto_heal.UserCreds') as MockUserCreds:
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.expired = False
        MockUserCreds.return_value = mock_creds

        with patch.object(Path, 'exists', return_value=True),              patch('builtins.open', MagicMock()):
            res = engine.diagnose_and_heal_gdrive(heal=False)
            assert res['status'] == 'ERROR'
            for k in TARGET_GDRIVE_FOLDERS.keys():
                assert res['target_folders'][k]['accessible'] is False


def test_hung_colab_session_detection_and_stop_invocation(tmp_path):
    """
    Adversarial verification of hung VM release:
    - Session duration = 5000s (> 4800s threshold)
    - In --check mode: detected=1, released=0, colab stop NOT called
    - In --heal mode: detected=1, released=1, colab stop -s <sess> IS called
    - Session is removed from sessions.json
    """
    engine = AutoHealEngine(workspace_dir=QUIZ_ROOT)

    with patch('scripts.auto_heal.ColabAccountManager') as MockMgr:
        mock_mgr = MagicMock()
        MockMgr.return_value = mock_mgr

        # colab sessions reports hung_worker_sess
        mock_mgr.run_colab_command.return_value = (0, '[hung_worker_sess] https://colab...', '')

        # Set up profile directory with aged sessions.json
        prof_dir = tmp_path / 'gmail_1'
        cli_dir = prof_dir / '.config' / 'colab-cli'
        cli_dir.mkdir(parents=True, exist_ok=True)
        sess_file = cli_dir / 'sessions.json'
        sess_file.write_text(json.dumps({'hung_worker_sess': {'name': 'hung_worker_sess'}}), encoding='utf-8')

        # Set mtime to 5000s ago
        old_mtime = time.time() - 5000
        os.utime(sess_file, (old_mtime, old_mtime))
        mock_mgr.get_account_profile_dir.return_value = prof_dir

        # 1. Test in --check mode: must detect but NOT release
        res_check = engine.diagnose_and_heal_colab_pool(heal=False)
        assert res_check['hung_sessions_detected'] >= 1
        assert res_check['hung_sessions_released'] == 0
        mock_mgr.run_colab_command.assert_any_call('gmail_1', ['sessions'], timeout=30)
        # colab stop should NOT have been invoked
        stop_calls = [c for c in mock_mgr.run_colab_command.call_args_list if 'stop' in c[0][1]]
        assert len(stop_calls) == 0

        # 2. Test in --heal mode: must detect AND release
        res_heal = engine.diagnose_and_heal_colab_pool(heal=True)
        assert res_heal['hung_sessions_detected'] >= 1
        assert res_heal['hung_sessions_released'] >= 1
        mock_mgr.run_colab_command.assert_any_call('gmail_1', ['stop', '-s', 'hung_worker_sess'], timeout=30)

        # Check sessions.json purged
        updated_sessions = json.loads(sess_file.read_text(encoding='utf-8'))
        assert 'hung_worker_sess' not in updated_sessions


def test_recent_colab_session_not_stopped(tmp_path):
    """Verify that recent active sessions (age < 4800s) are NOT stopped."""
    engine = AutoHealEngine(workspace_dir=QUIZ_ROOT)

    with patch('scripts.auto_heal.ColabAccountManager') as MockMgr:
        mock_mgr = MagicMock()
        MockMgr.return_value = mock_mgr
        mock_mgr.run_colab_command.return_value = (0, '[normal_worker] https://colab...', '')

        prof_dir = tmp_path / 'gmail_1'
        cli_dir = prof_dir / '.config' / 'colab-cli'
        cli_dir.mkdir(parents=True, exist_ok=True)
        sess_file = cli_dir / 'sessions.json'
        sess_file.write_text(json.dumps({'normal_worker': {'name': 'normal_worker'}}), encoding='utf-8')

        # Set mtime to 600s ago (10 minutes < 80 minutes)
        fresh_mtime = time.time() - 600
        os.utime(sess_file, (fresh_mtime, fresh_mtime))
        mock_mgr.get_account_profile_dir.return_value = prof_dir

        res = engine.diagnose_and_heal_colab_pool(heal=True)
        assert res['hung_sessions_detected'] == 0
        assert res['hung_sessions_released'] == 0
        stop_calls = [c for c in mock_mgr.run_colab_command.call_args_list if 'stop' in c[0][1]]
        assert len(stop_calls) == 0


def test_blacklist_aleron_dt_detection_and_purge(tmp_path):
    """Verify aleron.dt blacklist detection and remediation."""
    engine = AutoHealEngine(workspace_dir=QUIZ_ROOT)

    fake_reg = tmp_path / 'registry.json'
    fake_reg.write_text(json.dumps({
        'accounts': {
            'gmail_1': {'email': 'hothihuong113@gmail.com', 'status': 'READY'},
            'gmail_bad': {'email': 'aleron.dt@gmail.com', 'status': 'READY'}
        }
    }), encoding='utf-8')

    with patch('scripts.auto_heal.COLAB_REGISTRY_PATH', fake_reg),          patch('scripts.auto_heal.ColabAccountManager') as MockMgr:
        mock_mgr = MagicMock()
        mock_mgr.run_colab_command.return_value = (0, '', '')
        MockMgr.return_value = mock_mgr

        # Check mode: flag as error
        res_check = engine.diagnose_and_heal_colab_pool(heal=False)
        assert res_check['blacklist_enforced'] is False
        assert res_check['status'] == 'ERROR'
        assert any('aleron.dt' in err for err in res_check['errors'])
        mock_mgr.remove_account.assert_not_called()

        # Heal mode: purge blacklisted account
        res_heal = engine.diagnose_and_heal_colab_pool(heal=True)
        assert res_heal['blacklist_enforced'] is False
        mock_mgr.remove_account.assert_called_with('gmail_bad')


def test_gsheets_corrupted_headers_healing():
    """Verify that corrupt Google Sheets headers trigger ERROR in check, and are repaired in heal."""
    engine = AutoHealEngine(workspace_dir=QUIZ_ROOT)

    mock_service = MagicMock()
    bad_headers = [['#', 'Topic', 'Level', 'Status']]
    mock_service.spreadsheets().values().batchGet().execute.return_value = {
        'valueRanges': [{'range': 'pinyin!A1:P1', 'values': bad_headers}]
    }

    with patch('scripts.auto_heal.get_sheets_service', return_value=mock_service),          patch('scripts.auto_heal.audit_and_enforce_row_height', return_value={}):

        # Check mode: should report ERROR
        res_check = engine.diagnose_and_heal_gsheets(heal=False)
        assert res_check['status'] == 'ERROR'
        assert res_check['tabs_columns_check']['pinyin']['valid'] is False

        # Heal mode: should call update with STANDARD_16_COLUMNS
        res_heal = engine.diagnose_and_heal_gsheets(heal=True)
        assert res_heal['tabs_columns_check']['pinyin']['healed'] is True
        mock_service.spreadsheets().values().update.assert_called_once()


def test_status_monotonicity_gsheets_corrupted_header_and_row_height():
    """Verify status monotonicity: corrupted header (ERROR) is not masked by row height warning (WARNING)."""
    engine = AutoHealEngine(workspace_dir=QUIZ_ROOT)

    mock_service = MagicMock()
    bad_headers = [['#', 'Topic', 'Level', 'Status']]
    mock_service.spreadsheets().values().batchGet().execute.return_value = {
        'valueRanges': [{'range': 'pinyin!A1:P1', 'values': bad_headers}]
    }
    mock_audit = {
        'pinyin': {'total_rows': 10, 'non_target_rows': 2, 'all_target': False}
    }

    with patch('scripts.auto_heal.get_sheets_service', return_value=mock_service),          patch('scripts.auto_heal.audit_and_enforce_row_height', return_value=mock_audit):
        res = engine.diagnose_and_heal_gsheets(heal=False)
        assert res['status'] == 'ERROR', f"Expected ERROR but got {res['status']}"
        assert res['row_height_21px']['non_target_rows'] == 2
        assert any('headers do not match standard 16 columns schema' in err for err in res['errors'])
        assert any('deviate from the 21px height invariant' in err for err in res['errors'])


def test_status_monotonicity_code_sync_missing_script_and_stray_pyc(tmp_path):
    """Verify status monotonicity: missing sync script (ERROR) is not masked by stray pyc warning (WARNING)."""
    scripts_dir = tmp_path / 'scripts'
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / 'auto_backup.py').write_text('# valid', encoding='utf-8')
    (tmp_path / 'stray.pyc').write_text('stray', encoding='utf-8')

    engine = AutoHealEngine(workspace_dir=tmp_path)
    res = engine.diagnose_and_heal_code_sync_and_hygiene(heal=False)
    assert res['status'] == 'ERROR', f"Expected ERROR but got {res['status']}"
    assert res['exfat_bytecode_hygiene']['stray_pyc_count'] >= 1
    assert any('Script missing' in err for err in res['errors'])
    assert any('Found 1 .pyc files' in err for err in res['errors'])


def test_oauth_token_persistence_in_heal_mode(tmp_path):
    """
    Adversarial verification of OAuth token persistence (Defect 2):
    1. Check mode: refresh occurs in memory only, disk file remains untouched.
    2. Heal mode: refreshed access_token and expiry are saved to disk with chmod 600.
    3. Subsequent diagnosis detects valid credentials on disk without needing refresh.
    """
    fake_oauth = tmp_path / "user_oauth2.json"
    initial_content = {
        "client_id": "test-client-id.apps.googleusercontent.com",
        "client_secret": "test-secret",
        "refresh_token": "test-refresh-token",
        "token_uri": "https://oauth2.googleapis.com/token",
        "scopes": ["https://www.googleapis.com/auth/drive"]
    }
    fake_oauth.write_text(json.dumps(initial_content), encoding="utf-8")
    fake_oauth.chmod(0o600)

    engine = AutoHealEngine(workspace_dir=QUIZ_ROOT)

    mock_drive_service = MagicMock()
    mock_drive_service.files().get().execute.return_value = {
        "id": "test_id",
        "name": "test_folder",
        "mimeType": "application/vnd.google-apps.folder",
        "trashed": False
    }

    # 1. Check mode: refresh occurs in memory only, disk file remains untouched
    with patch("scripts.auto_heal.USER_OAUTH_PATH", fake_oauth),          patch("scripts.auto_heal.build", return_value=mock_drive_service),          patch.object(UserCreds, "refresh", autospec=True) as mock_ref_check:

        def side_effect_check(self, req):
            self.token = "ya29.test_token_check"
            self.expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
        mock_ref_check.side_effect = side_effect_check

        res_check = engine.diagnose_and_heal_gdrive(heal=False)
        assert res_check["oauth_user_token"]["refreshed"] is True
        mock_ref_check.assert_called_once()

        data_check = json.loads(fake_oauth.read_text(encoding="utf-8"))
        assert "access_token" not in data_check
        assert "expiry" not in data_check

    # 2. Heal mode: refreshed access_token and expiry are persisted to disk with chmod 600
    with patch("scripts.auto_heal.USER_OAUTH_PATH", fake_oauth),          patch("scripts.auto_heal.build", return_value=mock_drive_service),          patch.object(UserCreds, "refresh", autospec=True) as mock_ref_heal:

        def side_effect_heal(self, req):
            self.token = "ya29.test_token_healed"
            self.expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
        mock_ref_heal.side_effect = side_effect_heal

        res_heal = engine.diagnose_and_heal_gdrive(heal=True)
        assert res_heal["oauth_user_token"]["refreshed"] is True
        mock_ref_heal.assert_called_once()

        data_heal = json.loads(fake_oauth.read_text(encoding="utf-8"))
        assert data_heal.get("access_token") == "ya29.test_token_healed"
        assert data_heal.get("token") == "ya29.test_token_healed"
        assert "expiry" in data_heal

        mode = oct(fake_oauth.stat().st_mode & 0o777)
        assert mode == oct(0o600)
        assert any("token refreshed and persisted to disk" in a for a in engine.actions_taken)

    # 3. Subsequent check mode: credentials on disk are already valid (0 redundant roundtrips)
    with patch("scripts.auto_heal.USER_OAUTH_PATH", fake_oauth),          patch("scripts.auto_heal.build", return_value=mock_drive_service),          patch.object(UserCreds, "refresh", autospec=True) as mock_ref_subsequent:

        res_subsequent = engine.diagnose_and_heal_gdrive(heal=False)
        mock_ref_subsequent.assert_not_called()
        assert res_subsequent["oauth_user_token"]["valid"] is True
        assert res_subsequent["oauth_user_token"]["refreshed"] is False


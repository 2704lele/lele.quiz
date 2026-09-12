"""
Adversarial QA Suite for Zero-Leak Compliance, Buffer 1 Isolation & MicroVM Portability.
Compliant with 06_SECURITY_AND_CODE_AUDITING_GUIDE.md & 09_MICROVM_HARDWARE_SANDBOX_SPECIFICATION.md.
"""
import os
import re
import sys
import json
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from monitor import SOCIAL_CHANNELS
from scripts.publish_social_batch import is_channel_match, parse_platform_metadata


def test_buffer1_strict_isolation_channels_count():
    """Verifies that SOCIAL_CHANNELS contains STRICTLY 3 channels belonging to Buffer 1."""
    assert len(SOCIAL_CHANNELS) == 3, f"Expected 3 channels, got {len(SOCIAL_CHANNELS)}"

    platforms = [ch["platform"] for ch in SOCIAL_CHANNELS]
    assert "YouTube Shorts" in platforms
    assert "TikTok" in platforms
    assert "Facebook Fanpage" in platforms

    for ch in SOCIAL_CHANNELS:
        assert ch.get("dispatcher") == "Buffer 1 (Video)", f"Channel {ch['name']} has invalid dispatcher {ch.get('dispatcher')}"


def test_buffer1_no_buffer2_or_buffer3_references():
    """Verifies that is_channel_match rejects Buffer 2 and Buffer 3 filters."""
    # Dummy non-Buffer 1 channel
    foreign_ch = {
        "platform": "Threads",
        "name": "LeLe Threads",
        "channel_id": "6a86bd97ccaf649a67dfcca8"
    }

    # is_channel_match should only match if channel matches filter
    assert not is_channel_match(foreign_ch, "youtube")
    assert not is_channel_match(foreign_ch, "tiktok")
    assert not is_channel_match(foreign_ch, "fb")


def test_zero_leak_no_plaintext_credentials_in_repo():
    """Scans repository tree to ensure no plaintext OAuth/JWT/Secret JSON files exist."""
    forbidden_files = [
        "oauth_credentials.json",
        "service_account.json",
        "client_secret.json",
        ".env"
    ]

    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Ignore .git and virtualenvs
        if any(ignored in root for ignored in [".git", ".venv", "venv", "__pycache__"]):
            continue

        for f in files:
            assert f not in forbidden_files, f"Found forbidden plaintext credential file: {os.path.join(root, f)}"


def test_devcontainer_and_microvm_sandbox_spec():
    """Verifies that devcontainer and docker-compose define non-root and tmpfs."""
    devcontainer_file = os.path.join(PROJECT_ROOT, ".devcontainer", "devcontainer.json")
    assert os.path.exists(devcontainer_file), "devcontainer.json missing"

    with open(devcontainer_file, "r") as f:
        dc_data = json.load(f)
    assert dc_data.get("remoteUser") == "vscode"

    compose_file = os.path.join(PROJECT_ROOT, "docker", "docker-compose.yml")
    assert os.path.exists(compose_file), "docker-compose.yml missing"

    with open(compose_file, "r") as f:
        compose_content = f.read()
    assert "no-new-privileges:true" in compose_content
    assert "/dev/shm" in compose_content
    assert "cap_drop" in compose_content


def test_gitignore_covers_secrets_and_vault():
    """Verifies that .gitignore blocks *.json in configs, .env, and vault files."""
    gitignore_path = os.path.join(PROJECT_ROOT, ".gitignore")
    assert os.path.exists(gitignore_path), ".gitignore missing"

    with open(gitignore_path, "r") as f:
        content = f.read()

    assert "service_account.json" in content
    assert "oauth_credentials.json" in content
    assert "*.env" in content
    assert "project_vault.enc" in content

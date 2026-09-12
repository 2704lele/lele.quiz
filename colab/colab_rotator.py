#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Colab Account Rotation Pool Manager for LeLe Storybook & Quiz Video Engine.
Manages a pool of Google Colab user profiles to rotate across multiple Gmail accounts,
handling quota limits, 30-minute cool-downs (1800s), and running colab commands with isolated environments.

STRICT POLICY:
The account "aleron.dt@gmail.com" is PERMANENTLY FORBIDDEN and BLACKLISTED from Colab use.
"""

import os
import sys
import json
import time
import shutil
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("lelestory.omni.colab_rotator")

PROFILES_BASE_DIR = os.path.expanduser("~/.config/colab_profiles")
REGISTRY_FILE = os.path.join(PROFILES_BASE_DIR, "registry.json")
COLAB_EXECUTABLE = os.path.expanduser("~/.local/bin/colab")

# User Mandate: aleron.dt@gmail.com must NEVER be used in Colab under any circumstances
BLACKLISTED_EMAILS = {
    "aleron.dt@gmail.com",
    "aleron.dt"
}

# Strict User Policy: No email can be reused within 30 minutes (1800s)
DEFAULT_COOLDOWN_SECONDS = 1800


class ColabAccountManager:
    """Manages multi-account profiles and rotation for google-colab-cli."""

    def __init__(self, base_dir: str = PROFILES_BASE_DIR):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.base_dir / "registry.json"
        self._ensure_registry()
        self._enforce_blacklist()

    def _ensure_registry(self) -> None:
        if not self.registry_path.exists():
            default_data = {
                "version": 1,
                "accounts": {},
                "last_active_account": None,
                "blacklisted_emails": list(BLACKLISTED_EMAILS)
            }
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=2)

    def _read_registry(self) -> Dict[str, Any]:
        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read registry: {e}. Reinitializing.")
            self._ensure_registry()
            with open(self.registry_path, "r", encoding="utf-8") as f:
                return json.load(f)

    def _write_registry(self, data: Dict[str, Any]) -> None:
        temp_file = self.registry_path.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        temp_file.replace(self.registry_path)

    def _enforce_blacklist(self) -> None:
        """Strictly inspects existing registry to purge any blacklisted accounts."""
        reg = self._read_registry()
        accounts = reg.get("accounts", {})
        purged = []
        for alias, info in list(accounts.items()):
            email = (info.get("email") or "").strip().lower()
            if any(b in email for b in BLACKLISTED_EMAILS) or any(b in alias.lower() for b in BLACKLISTED_EMAILS):
                logger.critical(f"ENFORCEMENT: Blacklisted email detected ({email}) in alias {alias}! Purging profile!")
                del accounts[alias]
                purged.append(alias)
                prof_dir = self.get_account_profile_dir(alias)
                if prof_dir.exists():
                    shutil.rmtree(prof_dir)

        if purged:
            reg["accounts"] = accounts
            if reg.get("last_active_account") in purged:
                reg["last_active_account"] = None
            self._write_registry(reg)

    def get_account_profile_dir(self, alias: str) -> Path:
        """Returns the isolated home directory path for a profile."""
        return self.base_dir / alias

    def list_accounts(self) -> List[Dict[str, Any]]:
        """Lists all registered Colab accounts with token readiness and cooldown state."""
        self._enforce_blacklist()
        reg = self._read_registry()
        accounts = []
        now = time.time()

        for alias, info in reg.get("accounts", {}).items():
            profile_dir = self.get_account_profile_dir(alias)
            token_file = profile_dir / ".config" / "colab-cli" / "token.json"
            has_token = token_file.exists() and token_file.stat().st_size > 0

            status = info.get("status", "UNCONFIGURED")
            cooldown_until = info.get("cooldown_until", 0)

            if cooldown_until > now:
                status = "COOLING_DOWN"
            elif has_token:
                status = "READY"
            else:
                status = "NO_TOKEN"

            accounts.append({
                "alias": alias,
                "email": info.get("email", "Unknown"),
                "status": status,
                "cooldown_remaining_sec": max(0, int(cooldown_until - now)),
                "success_count": info.get("success_count", 0),
                "failure_count": info.get("failure_count", 0),
                "last_used": info.get("last_used", None),
                "profile_dir": str(profile_dir)
            })
        return accounts

    def register_account(self, alias: str, email: str = "") -> Path:
        """Creates directory structure for a new account profile, strictly checking blacklist."""
        clean_email = email.strip().lower()
        if any(b in clean_email for b in BLACKLISTED_EMAILS):
            raise PermissionError(
                f"STRICT POLICY VIOLATION: Account {email} is PERMANENTLY BLACKLISTED and forbidden from Colab!"
            )

        profile_dir = self.get_account_profile_dir(alias)
        (profile_dir / ".config" / "colab-cli").mkdir(parents=True, exist_ok=True)

        reg = self._read_registry()
        reg["accounts"][alias] = {
            "email": email,
            "status": "REGISTERED",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_used": None,
            "cooldown_until": 0,
            "success_count": 0,
            "failure_count": 0
        }
        self._write_registry(reg)
        logger.info(f"Registered Colab account: {alias} at {profile_dir}")
        return profile_dir

    def verify_account_token_email(self, alias: str) -> Optional[str]:
        """
        Inspects the token for account alias to ensure it does not belong to a blacklisted user.
        If blacklisted, purges it immediately.
        """
        profile_dir = self.get_account_profile_dir(alias)
        token_file = profile_dir / ".config" / "colab-cli" / "token.json"
        if not token_file.exists():
            return None

        detected_email = ""
        try:
            with open(token_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                import base64
                id_token = data.get("id_token")
                if id_token and "." in id_token:
                    payload = id_token.split(".")[1]
                    padded = payload + "=" * (-len(payload) % 4)
                    claims = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8", errors="ignore"))
                    detected_email = (claims.get("email") or "").strip().lower()
        except Exception:
            pass

        if not detected_email:
            code, stdout, _ = self.run_colab_command(alias, ["whoami"], timeout=10)
            if code == 0 and "email:" in stdout.lower():
                for line in stdout.splitlines():
                    if "email:" in line.lower():
                        detected_email = line.split(":", 1)[1].strip().lower()
                        break

        if any(b in detected_email for b in BLACKLISTED_EMAILS):
            logger.critical(f"FATAL: Token for account {alias} belongs to BLACKLISTED EMAIL {detected_email}! Deleting!")
            self.remove_account(alias)
            raise PermissionError(f"CRITICAL ERROR: Account {detected_email} is BLACKLISTED and cannot be used!")

        if detected_email:
            reg = self._read_registry()
            if alias in reg["accounts"]:
                reg["accounts"][alias]["email"] = detected_email
                self._write_registry(reg)

        return detected_email

    def remove_account(self, alias: str) -> bool:
        """Removes an account profile and deletes its directory."""
        reg = self._read_registry()
        if alias in reg["accounts"]:
            del reg["accounts"][alias]
            if reg.get("last_active_account") == alias:
                reg["last_active_account"] = None
            self._write_registry(reg)

        profile_dir = self.get_account_profile_dir(alias)
        if profile_dir.exists():
            shutil.rmtree(profile_dir)
        logger.info(f"Removed Colab account: {alias}")
        return True

    def mark_cooldown(
        self,
        alias: str,
        duration_seconds: int = DEFAULT_COOLDOWN_SECONDS,
        reason: str = "Connection/Quota Limit"
    ) -> None:
        """
        Places an account in cooldown.
        Strict User Policy: Cooldown is 30 minutes (1800s).
        """
        reg = self._read_registry()
        if alias in reg["accounts"]:
            reg["accounts"][alias]["status"] = "COOLING_DOWN"
            reg["accounts"][alias]["cooldown_until"] = time.time() + duration_seconds
            reg["accounts"][alias]["last_error"] = reason
            reg["accounts"][alias]["failure_count"] = reg["accounts"][alias].get("failure_count", 0) + 1
            self._write_registry(reg)
            logger.warning(f"Account {alias} entered COOLING_DOWN for {duration_seconds}s. Reason: {reason}")

    def mark_success(
        self,
        alias: str,
        cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS
    ) -> None:
        """
        Records successful job execution for an account.
        Strict User Policy: After successful use, account MUST enter 30-minute cooldown (1800s)
        so that no email is reused within 30 minutes.
        """
        reg = self._read_registry()
        if alias in reg["accounts"]:
            now_iso = datetime.now(timezone.utc).isoformat()
            reg["accounts"][alias]["last_used"] = now_iso
            reg["accounts"][alias]["success_count"] = reg["accounts"][alias].get("success_count", 0) + 1
            reg["last_active_account"] = alias

            if cooldown_seconds > 0:
                reg["accounts"][alias]["status"] = "COOLING_DOWN"
                reg["accounts"][alias]["cooldown_until"] = time.time() + cooldown_seconds
                logger.info(f"Account {alias} finished successfully. Resting for {cooldown_seconds}s (30m policy).")
            else:
                reg["accounts"][alias]["status"] = "READY"
                reg["accounts"][alias]["cooldown_until"] = 0

            self._write_registry(reg)

    def select_active_account(self) -> Optional[str]:
        """
        Picks the best available non-blacklisted account that is READY (cooldown_remaining_sec == 0).
        Sorts by least failures, then least recently used.
        """
        accounts = self.list_accounts()
        ready_accounts = [a for a in accounts if a["status"] == "READY"]

        if not ready_accounts:
            return None

        # Prefer accounts with fewer failures, then more successes, or least recently used
        ready_accounts.sort(key=lambda a: (a["failure_count"], -a["success_count"]))
        return ready_accounts[0]["alias"]

    def get_earliest_available_account(self) -> Tuple[Optional[str], int]:
        """Returns the alias of the account that will become available earliest and seconds remaining."""
        accounts = self.list_accounts()
        if not accounts:
            return None, 0

        ready = [a for a in accounts if a["status"] == "READY"]
        if ready:
            return ready[0]["alias"], 0

        accounts.sort(key=lambda a: a["cooldown_remaining_sec"])
        return accounts[0]["alias"], accounts[0]["cooldown_remaining_sec"]

    def run_colab_command(
        self,
        account_alias: str,
        cmd_args: List[str],
        timeout: Optional[int] = None,
        capture_output: bool = True
    ) -> Tuple[int, str, str]:
        """Executes a colab CLI command in the isolated context of the specified account."""
        reg = self._read_registry()
        acct_email = (reg.get("accounts", {}).get(account_alias, {}).get("email") or "").lower()
        if any(b in acct_email for b in BLACKLISTED_EMAILS):
            raise PermissionError(f"STRICT POLICY: Refusing execution with blacklisted email: {acct_email}")

        profile_dir = self.get_account_profile_dir(account_alias)
        env = os.environ.copy()
        env["HOME"] = str(profile_dir)
        local_bin = os.path.expanduser("~/.local/bin")
        env["PATH"] = f"{local_bin}:{env.get('PATH', '')}"

        executable = COLAB_EXECUTABLE if os.path.exists(COLAB_EXECUTABLE) else "colab"
        full_cmd = [executable, "--auth", "oauth2"] + cmd_args

        cmd_str = " ".join(full_cmd)
        logger.info(f"[{account_alias}] Running: {cmd_str}")
        try:
            res = subprocess.run(
                full_cmd,
                env=env,
                capture_output=capture_output,
                text=True,
                timeout=timeout
            )
            return res.returncode, res.stdout or "", res.stderr or ""
        except subprocess.TimeoutExpired:
            logger.error(f"[{account_alias}] Command timed out after {timeout}s: {cmd_str}")
            return -1, "", f"TimeoutExpired after {timeout}s"
        except Exception as e:
            logger.error(f"[{account_alias}] Execution error: {e}")
            return -1, "", str(e)


if __name__ == "__main__":
    mgr = ColabAccountManager()
    accs = mgr.list_accounts()
    print(f"Colab Account Pool: {len(accs)} account(s) registered.")
    print(f"Permanent Blacklist: {list(BLACKLISTED_EMAILS)}")
    for a in accs:
        print(f"  - [{a['status']}] {a['alias']} ({a['email']}) | Success: {a['success_count']} | Cooldown: {a['cooldown_remaining_sec']}s")

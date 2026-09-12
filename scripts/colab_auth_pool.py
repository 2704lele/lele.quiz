#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive CLI Tool to Add & Manage Colab Account Pool for Quiz System.
Facilitates one-time OAuth authentication for each Gmail account with isolated token storage
and strict blacklist enforcement (aleron.dt@gmail.com is forbidden).
"""

import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path

# Add quiz/colab to path
QUIZ_ROOT = Path(__file__).resolve().parent.parent
COLAB_DIR = QUIZ_ROOT / "colab"
if str(COLAB_DIR) not in sys.path:
    sys.path.insert(0, str(COLAB_DIR))
if str(QUIZ_ROOT) not in sys.path:
    sys.path.insert(0, str(QUIZ_ROOT))

from colab_rotator import ColabAccountManager, BLACKLISTED_EMAILS


def cmd_list(mgr: ColabAccountManager):
    accs = mgr.list_accounts()
    print("\n=======================================================")
    print(f"  Google Colab Account Pool ({len(accs)} account(s) registered)")
    print("=======================================================")
    print(f"  [STRICT POLICY] Blacklisted: {list(BLACKLISTED_EMAILS)}")
    print("-------------------------------------------------------")
    if not accs:
        print("  (Chưa có tài khoản nào được đăng ký. Dùng lệnh `add <alias>` để thêm)")
    for a in accs:
        cooldown_str = f" | Cooldown: {a['cooldown_remaining_sec']}s" if a['cooldown_remaining_sec'] > 0 else ""
        print(f"  * [{a['status']:<12}] Alias: {a['alias']:<15} Email: {a['email']:<25} Success: {a['success_count']}{cooldown_str}")
    print("=======================================================\n")


def cmd_add(mgr: ColabAccountManager, alias: str):
    alias = alias.strip().lower()
    if not alias:
        print("❌ Error: Alias cannot be empty.")
        return

    profile_dir = mgr.get_account_profile_dir(alias)
    token_file = profile_dir / ".config" / "colab-cli" / "token.json"

    if token_file.exists():
        resp = input(f"Tài khoản '{alias}' đã có token. Bạn có muốn cấp quyền lại (re-auth) không? [y/N]: ").strip().lower()
        if resp != "y":
            print("Hủy bỏ thao tác.")
            return
        token_file.unlink(missing_ok=True)

    mgr.register_account(alias)
    print(f"\n🔐 Đang khởi tạo phiên xác thực OAuth2 cho profile: '{alias}'...")

    env = os.environ.copy()
    env["HOME"] = str(profile_dir)
    local_bin = os.path.expanduser("~/.local/bin")
    env["PATH"] = f"{local_bin}:{env.get('PATH', '')}"

    colab_bin = os.path.expanduser("~/.local/bin/colab")
    if not os.path.exists(colab_bin):
        colab_bin = "colab"

    # Trigger oauth authentication flow via colab CLI
    cmd = [colab_bin, "--auth", "oauth2", "sessions"]
    try:
        proc = subprocess.run(cmd, env=env)
        if proc.returncode == 0 or token_file.exists():
            print("\n🔍 Đang kiểm tra token email...")
            try:
                email = mgr.verify_account_token_email(alias)
                print(f"🎉 Thành công! Đã thêm tài khoản: {alias} ({email}) vào Pool Colab.")
            except Exception as e:
                print(f"⚠️ Đã lưu token nhưng không thể phân tích email: {e}")
        else:
            print(f"❌ Xác thực không thành công (exit code {proc.returncode}).")
    except Exception as exc:
        print(f"❌ Lỗi khi khởi chạy colab-cli: {exc}")


def cmd_remove(mgr: ColabAccountManager, alias: str):
    alias = alias.strip().lower()
    accs = {a["alias"]: a for a in mgr.list_accounts()}
    if alias not in accs:
        print(f"❌ Không tìm thấy tài khoản '{alias}' trong registry.")
        return

    confirm = input(f"Bạn có chắc chắn muốn xóa tài khoản '{alias}' ({accs[alias]['email']})? [y/N]: ").strip().lower()
    if confirm == "y":
        mgr.remove_account(alias)
        print(f"✓ Đã xóa tài khoản '{alias}'.")
    else:
        print("Hủy bỏ thao tác.")


def main():
    parser = argparse.ArgumentParser(description="Colab Multi-Account Pool Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    subparsers.add_parser("list", help="List all registered accounts")

    parser_add = subparsers.add_parser("add", help="Add / authenticate a new Colab account")
    parser_add.add_argument("alias", help="Account alias (e.g. gmail_1, gmail_2)")

    parser_rm = subparsers.add_parser("remove", help="Remove an account")
    parser_rm.add_argument("alias", help="Account alias to remove")

    args = parser.parse_args()
    mgr = ColabAccountManager()

    if args.command == "add":
        cmd_add(mgr, args.alias)
    elif args.command == "remove":
        cmd_remove(mgr, args.alias)
    else:
        cmd_list(mgr)


if __name__ == "__main__":
    main()

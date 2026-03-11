"""
CLI-only test script for token minting and .env updates.

Run from project root:
  python testing/test_update_tokens.py mint-app
  python testing/test_update_tokens.py verify
  python testing/test_update_tokens.py refresh-user
  python testing/test_update_tokens.py exchange [code]

Default environment is production. Use --sandbox for sandbox.
"""

import os
import sys

# Ensure project root is on path when run as python testing/test_update_tokens.py
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from dotenv import load_dotenv

# Load .env from project root
_env_path = os.path.join(_project_root, '.env')
load_dotenv(_env_path)


def _verify_env():
    """Read .env and report which token keys are set (non-empty)."""
    if not os.path.isfile(_env_path):
        print(".env not found at project root.")
        return
    with open(_env_path, 'r', encoding='utf-8') as f:
        content = f.read()
    keys = ('application_token', 'user_token', 'refresh_token', 'auth_code')
    for key in keys:
        for line in content.splitlines():
            line = line.strip()
            if line.startswith(key + '='):
                value = line[len(key) + 1:].strip()
                status = "set" if value else "empty"
                preview = (value[:20] + "...") if len(value) > 20 else value
                print(f"  {key}: {status} ({preview})")
                break
        else:
            print(f"  {key}: not present")


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Test token minting and .env updates (CLI only, default: production)."
    )
    parser.add_argument(
        "command",
        choices=["mint-app", "verify", "refresh-user", "exchange"],
        help="mint-app: mint application token and save to .env; verify: show .env token keys; refresh-user: refresh user token; exchange: exchange auth code for user token"
    )
    parser.add_argument(
        "code",
        nargs="?",
        default=None,
        help="For exchange: authorization code from consent redirect (optional; will prompt if omitted)"
    )
    parser.add_argument(
        "--sandbox",
        action="store_true",
        help="Use sandbox environment instead of production"
    )
    args = parser.parse_args()
    environment = "sandbox" if args.sandbox else "production"

    from backend.refreshToken import (
        mint_application_token,
        exchange_code_for_user_token,
        refresh_user_token,
    )

    if args.command == "mint-app":
        print(f"Minting application token ({environment})...")
        result = mint_application_token(environment=environment)
        if result:
            print("Application token minted and written to .env.")
            _verify_env()
        else:
            print("Mint failed. Check credentials and network.")
            sys.exit(1)

    elif args.command == "verify":
        print("Current .env token keys:")
        _verify_env()

    elif args.command == "refresh-user":
        print(f"Refreshing user token ({environment})...")
        try:
            result = refresh_user_token(environment=environment)
            if result:
                print("User token refreshed and written to .env.")
                _verify_env()
            else:
                print("Refresh failed. Check refresh_token and credentials.")
                sys.exit(1)
        except ValueError as e:
            print(e)
            sys.exit(1)

    elif args.command == "exchange":
        code = args.code
        if not code:
            code = input("Enter authorization code from consent redirect: ").strip()
        if not code:
            print("No code provided.")
            sys.exit(1)
        print(f"Exchanging code for user token ({environment})...")
        result = exchange_code_for_user_token(code, environment=environment)
        if result:
            print("User token and refresh_token written to .env.")
            _verify_env()
        else:
            print("Exchange failed. Check code, redirect_uri, and credentials.")
            sys.exit(1)


if __name__ == "__main__":
    main()

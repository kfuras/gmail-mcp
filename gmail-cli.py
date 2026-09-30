#!/usr/bin/env python3
"""Thin CLI over GmailService — headless-friendly wrapper around the same code
the MCP server uses (auth.py/config.py/gmail.py). Lets scheduled jobs call
Gmail from a shell instead of registering the MCP server, which needs a
desktop client to talk to. Uses the existing OAuth tokens in
credentials/tokens/<account>.json (portable Google refresh tokens — no re-auth
needed on a new host).

All output is JSON on stdout. Errors go to stderr with a non-zero exit code.

Examples:
  gmail-cli.py search --account personal --query "from:receipts newer_than:14d" --max 20
  gmail-cli.py get-message --account personal --id <MSG_ID>
  gmail-cli.py list-attachments --account personal --id <MSG_ID>
  gmail-cli.py save-attachment --account personal --id <MSG_ID> \
      --attachment-id <ATT_ID> --out /tmp/attachments/invoice.pdf
  gmail-cli.py profile --account personal
"""
import argparse
import json
import sys
from pathlib import Path

# Import the MCP server's own modules (this file lives next to them).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from auth import AuthManager  # noqa: E402
from config import (  # noqa: E402
    get_client_secret_path,
    get_credentials_dir,
    load_config,
)
from gmail import GmailService  # noqa: E402


def _service(account: str) -> GmailService:
    config = load_config()
    auth = AuthManager(get_credentials_dir(config), get_client_secret_path(config))
    creds = auth.get_credentials(account)
    if creds is None:
        raise SystemExit(
            f"No credentials for account '{account}'. "
            f"Expected a token at credentials/tokens/{account}.json."
        )
    return GmailService(creds, account)


def _emit(obj) -> None:
    json.dump(obj, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Headless Gmail CLI (wraps GmailService).")
    ap.add_argument("--account", default="personal", help="Account name from config.json (default: personal)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("search", help="Search messages (Gmail query syntax).")
    p.add_argument("--query", required=True)
    p.add_argument("--max", type=int, default=20)
    p.add_argument("--body", action="store_true", help="Include message bodies.")

    p = sub.add_parser("get-message", help="Fetch one message by id (full).")
    p.add_argument("--id", required=True)

    p = sub.add_parser("get-thread", help="Fetch a thread by id.")
    p.add_argument("--id", required=True)

    p = sub.add_parser("list-attachments", help="List attachments in a message.")
    p.add_argument("--id", required=True)

    p = sub.add_parser("save-attachment", help="Download one attachment to disk.")
    p.add_argument("--id", required=True)
    p.add_argument("--attachment-id", required=True)
    p.add_argument("--out", required=True)

    sub.add_parser("profile", help="Show the account profile (verifies auth).")

    p = sub.add_parser("list-labels", help="List labels.")

    args = ap.parse_args()
    svc = _service(args.account)

    if args.cmd == "search":
        _emit(svc.search_messages(args.query, max_results=args.max, include_body=args.body))
    elif args.cmd == "get-message":
        _emit(svc.get_message(args.id))
    elif args.cmd == "get-thread":
        _emit(svc.get_thread(args.id))
    elif args.cmd == "list-attachments":
        _emit(svc.list_attachments(args.id))
    elif args.cmd == "save-attachment":
        _emit(svc.save_attachment(args.id, args.attachment_id, args.out))
    elif args.cmd == "profile":
        _emit(svc.get_profile())
    elif args.cmd == "list-labels":
        _emit(svc.list_labels())


if __name__ == "__main__":
    main()

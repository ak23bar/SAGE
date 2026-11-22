"""Run the local personal SAGE control plane from the repository root."""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from .control import approve, inspect, propose


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(".local/sage.sqlite3"))
    sub = parser.add_subparsers(dest="command", required=True)
    proposal = sub.add_parser("propose")
    proposal.add_argument("packet", type=Path)
    proposal.add_argument("operation")
    for name in ("approve", "inspect"):
        sub.add_parser(name).add_argument("run_id")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.command == "propose":
        if args.packet.stat().st_size > 65536:
            raise ValueError("packet exceeds 64 KiB")
        result = propose(args.db, json.loads(args.packet.read_text(encoding="utf-8-sig")), args.operation)
    elif args.command == "approve":
        result = approve(args.db, args.run_id)
    else:
        result = inspect(args.db, args.run_id)
    output = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        if args.out.resolve() == args.db.resolve():
            raise ValueError("receipt path must differ from the ledger")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, sqlite3.Error) as exc:
        sys.exit(str(exc))

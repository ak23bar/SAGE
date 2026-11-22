"""Exercise the two local CLIs in fresh processes using disposable operator state."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SAGE = Path(__file__).resolve().parents[1]


def call(cwd, *args):
    return subprocess.check_output([sys.executable, *map(str, args)], cwd=cwd, encoding="utf-8")


def main():
    source = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else SAGE.parent / "SEEM"
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        seem = root / "SEEM"
        seem.mkdir()
        for name in ("seem.py", "sources.toml"):
            shutil.copyfile(source / name, seem / name)
        shutil.copytree(source / "vault", seem / "vault", ignore=shutil.ignore_patterns("Sessions", ".obsidian"))
        packet = root / "packet.json"
        call(seem, "seem.py", "packet", "--out", packet)
        cli = ("-m", "apps.personal", "--db", root / "test.db")
        ask = json.loads(call(SAGE, *cli, "propose", packet, "save-brief"))
        if ask["state"] != "awaiting-approval":
            raise ValueError("expected a pending test proposal")
        run = ask["run_id"]
        verified = json.loads(call(SAGE, *cli, "approve", run))
        receipt = root / "receipt.json"
        call(SAGE, *cli, "--out", receipt, "inspect", run)
        replay = json.loads(receipt.read_text(encoding="utf-8"))
        if verified != replay or [e["event"] for e in replay["events"]] != ["ask", "approved", "verified"]:
            raise ValueError("receipt replay mismatch")
        call(seem, "seem.py", "capture", receipt)
        if run not in call(seem, "seem.py", "resume"):
            raise ValueError("fresh session could not find captured run")
        print(f"PASS: proposed, approved in disposable ledger, verified, captured, resumed. Run {run}")


if __name__ == "__main__":
    main()

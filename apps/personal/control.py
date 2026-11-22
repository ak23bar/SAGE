"""Personal SAGE ledger. All effects of the two local operations fit in one transaction."""

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9-]{0,63}$")]


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Note(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: Identifier
    source: str = Field(min_length=1, max_length=1024)
    text: str = Field(min_length=1, max_length=16384)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def check_hash(self):
        if digest(self.text) != self.sha256:
            raise ValueError("note digest mismatch")
        return self


class Packet(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    version: Literal["seem.packet.v1"] = Field(alias="schema")
    project: Literal["sage-personal"]
    profile: Identifier
    notes: list[Note] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def check_ids(self):
        if len({note.id for note in self.notes}) != len(self.notes):
            raise ValueError("duplicate source identifier")
        return self


@contextmanager
def ledger(path: Path) -> Iterator[sqlite3.Connection]:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY, packet TEXT NOT NULL, operation TEXT NOT NULL,
            state TEXT NOT NULL, brief TEXT)""")
        db.execute("""CREATE TABLE IF NOT EXISTS events (
            seq INTEGER PRIMARY KEY, run TEXT NOT NULL, event TEXT NOT NULL,
            at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')))""")
        yield db
        db.commit()
    finally:
        db.close()


def render(packet: Packet, operation: str) -> str:
    if operation == "preview":
        return "\n".join(f"{n.id}: {n.source}" for n in packet.notes)
    return "\n\n".join(f"## {n.id}\n{n.text.rstrip()}\n\nSource: {n.source}" for n in packet.notes)


def identity(payload: str, operation: str) -> str:
    return digest(canonical(["personal.policy.v1", digest(payload), operation]))


def receipt(db: sqlite3.Connection, run_id: str) -> dict:
    row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if row is None:
        raise ValueError("unknown run")
    packet = Packet.model_validate_json(row["packet"])
    if identity(row["packet"], row["operation"]) != run_id:
        raise ValueError("stored proposal digest mismatch")
    events = [dict(e) for e in db.execute("SELECT event, at FROM events WHERE run=? ORDER BY seq", (run_id,))]
    expected_history = {
        ("preview", "verified"): ["allow", "verified"],
        ("save-brief", "awaiting-approval"): ["ask"],
        ("save-brief", "verified"): ["ask", "approved", "verified"],
    }.get((row["operation"], row["state"]))
    if row["operation"] not in ("preview", "save-brief") and row["state"] == "denied":
        expected_history = ["deny"]
    if [e["event"] for e in events] != expected_history:
        raise ValueError("stored history conflicts with policy")
    result = {
        "schema": "sage.receipt.v1",
        "project": packet.project,
        "run_id": run_id,
        "packet_sha256": digest(row["packet"]),
        "policy": "personal.policy.v1",
        "operation": row["operation"],
        "state": row["state"],
        "events": events,
    }
    if row["state"] == "verified":
        expected = render(packet, row["operation"])
        if expected != row["brief"]:
            raise ValueError("stored brief failed verification")
        result.update(brief=expected, brief_sha256=digest(expected))
    if row["state"] == "awaiting-approval":
        result["proposed_brief"] = render(packet, row["operation"])
    return result


def event(db: sqlite3.Connection, run_id: str, name: str) -> None:
    db.execute("INSERT INTO events(run,event) VALUES(?,?)", (run_id, name))


def finish(db: sqlite3.Connection, run_id: str, packet: Packet, operation: str) -> None:
    db.execute("UPDATE runs SET state='verified',brief=? WHERE id=?", (render(packet, operation), run_id))
    event(db, run_id, "verified")


def propose(path: Path, data: dict, operation: str) -> dict:
    packet = Packet.model_validate(data)
    payload = canonical(packet.model_dump(by_alias=True))
    if not 1 <= len(operation) <= 80 or len(payload.encode()) > 65536:
        raise ValueError("proposal exceeds input bounds")
    run_id = identity(payload, operation)
    with ledger(path) as db:
        if not db.execute("SELECT 1 FROM runs WHERE id=?", (run_id,)).fetchone():
            decision = {"preview": "allow", "save-brief": "ask"}.get(operation, "deny")
            state = {"allow": "ready", "ask": "awaiting-approval", "deny": "denied"}[decision]
            db.execute("INSERT INTO runs VALUES(?,?,?,?,NULL)", (run_id, payload, operation, state))
            event(db, run_id, decision)
            if decision == "allow":
                finish(db, run_id, packet, operation)
        return receipt(db, run_id)


def approve(path: Path, run_id: str) -> dict:
    with ledger(path) as db:
        current = receipt(db, run_id)
        if current["operation"] != "save-brief" or current["state"] not in ("awaiting-approval", "verified"):
            raise ValueError("only an eligible save-brief proposal can be approved")
        if current["state"] == "awaiting-approval":
            payload = db.execute("SELECT packet FROM runs WHERE id=?", (run_id,)).fetchone()[0]
            event(db, run_id, "approved")
            finish(db, run_id, Packet.model_validate_json(payload), "save-brief")
        return receipt(db, run_id)


def inspect(path: Path, run_id: str) -> dict:
    if not path.is_file():
        raise ValueError("ledger does not exist")
    with ledger(path) as db:
        return receipt(db, run_id)

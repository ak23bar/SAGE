import asyncio
import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from apps.personal.claude import select_operation
from apps.personal.control import Packet, approve, inspect, propose


def packet():
    body = "Resume from the reviewed decision."
    return {
        "schema": "seem.packet.v1",
        "project": "sage-personal",
        "profile": "handoff",
        "notes": [
            {"id": "goal", "source": "repo:plan", "text": body, "sha256": hashlib.sha256(body.encode()).hexdigest()}
        ],
    }


def test_wait_then_resume_once(tmp_path):
    db = tmp_path / "state.db"
    pending = propose(db, packet(), "save-brief")
    assert pending["state"] == "awaiting-approval"
    assert "brief" not in pending
    assert pending == propose(db, packet(), "save-brief")
    receipt = approve(db, pending["run_id"])
    assert receipt == approve(db, pending["run_id"]) == inspect(db, pending["run_id"])
    assert receipt["state"] == "verified"
    assert "repo:plan" in receipt["brief"]
    assert [e["event"] for e in receipt["events"]] == ["ask", "approved", "verified"]


def test_other_operations_and_bad_inputs(tmp_path):
    db = tmp_path / "state.db"
    assert propose(db, packet(), "preview")["state"] == "verified"
    denied = propose(db, packet(), "publish")
    assert denied["state"] == "denied"
    with pytest.raises(ValueError):
        approve(db, denied["run_id"])
    bad = packet()
    bad["notes"][0]["text"] += "extra"
    with pytest.raises(ValueError):
        propose(db, bad, "preview")
    bad = packet()
    bad["project"] = "another-project"
    with pytest.raises(ValueError):
        propose(db, bad, "preview")


def test_concurrent_approval_and_damaged_history(tmp_path):
    db = tmp_path / "state.db"
    run = propose(db, packet(), "save-brief")["run_id"]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: approve(db, run), range(8)))
    assert all(item == results[0] for item in results)
    with sqlite3.connect(db) as conn:
        conn.execute("DELETE FROM events WHERE event='approved'")
    with pytest.raises(ValueError, match="history"):
        inspect(db, run)


@pytest.mark.parametrize("reply", ['{"operation":"save-brief"}', '{"operation":"approve"}', "bad json"])
def test_claude_proposal_contract(monkeypatch, reply):
    sdk = pytest.importorskip("claude_agent_sdk", reason="install the personal-claude extra for the SDK contract")

    async def fake_query(*, prompt, options):
        assert options.tools == [] and options.mcp_servers == {} and options.setting_sources == []
        assert options.permission_mode == "dontAsk" and options.max_turns == 1
        assert "repo:plan" in prompt
        yield sdk.ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id="fixture",
            result=reply,
        )

    monkeypatch.setattr(sdk, "query", fake_query)
    task = select_operation(Packet.model_validate(packet()), "save a brief")
    if reply == '{"operation":"save-brief"}':
        assert asyncio.run(task) == "save-brief"
    else:
        with pytest.raises(ValueError):
            asyncio.run(task)

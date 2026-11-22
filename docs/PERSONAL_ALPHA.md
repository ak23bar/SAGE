# SAGE personal alpha | Claude Code pickup

Start with a single deliverable: a fresh worker can turn a reviewed project packet into a source-linked brief, find the authorization decision, and reconstruct the result after restart. The personal control plane lives in `apps/personal/`. GPS / MOHID retains its Package A workstream, frozen specifications and PostgreSQL roadmap. Its next open issue is [E02](https://github.com/ak23bar/SAGE/issues/3).

## Run the sprint

Use sibling checkouts named SAGE and SEEM. From SAGE on Windows, bootstrap Python 3.12 using the commands below. On macOS/Linux use `.venv/bin/python`. The SDK extra is needed only for Claude proposals and its adapter tests.

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -e ".[dev,personal-claude]"
$py = ".\.venv\Scripts\python.exe"
& $py scripts/personal-smoke.py ../SEEM
& $py -m pytest -q -rs
```

The smoke exercise uses a disposable database and vault copy. It starts a new process for every step, exercises an approval in that test ledger, reads the receipt back, captures it in SEEM, and confirms that the next process finds it.

For your actual project session, run the following from SAGE. The proposal prints the exact brief and its run ID for review.

```powershell
$py = ".\.venv\Scripts\python.exe"
& $py ../SEEM/seem.py packet --out ../SEEM/.local/packet.json
$proposal = & $py -m apps.personal propose ../SEEM/.local/packet.json save-brief | ConvertFrom-Json
$proposal.proposed_brief
& $py -m apps.personal inspect $proposal.run_id
```

If the owner accepts that brief, the operator runs the following. An export after a restart produces the same verified receipt.

```powershell
& $py -m apps.personal approve $proposal.run_id
& $py -m apps.personal --out .local/receipt.json inspect $proposal.run_id
& $py ../SEEM/seem.py capture .local/receipt.json
& $py ../SEEM/seem.py resume
```

For an immediate read-only preview of the packet's source list, use `preview` in place of `save-brief`. SAGE records the preview in its ledger. Other operation names produce a durable denial. An invalid packet is rejected before a run exists.

## What the control plane owns

| Step | Implemented boundary |
| --- | --- |
| Context | SEEM selects reviewed notes by profile. SAGE checks version, project, sizes, uniqueness, note hashes and fields using Pydantic. The operator selects the local packet. |
| Application | The personal brief has two typed outcomes exposed to the adapter. Preview lists sources. Save-brief renders the complete source-linked Markdown. |
| Governance | Policy v1 maps preview to Allow and save-brief to Ask. Every other operation is denied. The run ID binds the canonical packet, operation and policy version. |
| Execution | A local deterministic renderer is the first executor. Its output and ordered decision events share one SQLite transaction. Inspection checks the stored result against the pinned packet and verifies event order. |
| Continuity | Replaying the same intent returns the same run. SEEM stores the verified run reference as a local observation for the next worker. |

This is a single-user local prototype. Anyone with access to the operator CLI and database can exercise the operator role. Hash checks attest to content consistency. Trust in the source manifest, the database and the human identity rests with the local operator. Give future workers only the proposal interface. Authenticate approval and isolate the database before enabling an unattended worker.

## Claude adapter

`apps/personal/claude.py` uses Anthropic's SDK to request one typed operation. It uses a temporary working directory, an empty tool list, explicit MCP configuration and a one-turn limit. The result goes through the same policy as a manual proposal. Invalid output stops before a ledger mutation. The offline tests substitute the model transport and exercise the installed SDK's option and result types.

For the live acceptance gate, choose a packet you intend to send to Claude and use your configured Claude account. This command contacts the provider:

```powershell
& $py -m apps.personal.claude ../SEEM/.local/packet.json "Propose saving a project brief for my review"
```

## Assembly by plane

| Plane | Reuse and skills | Integration decision |
| --- | --- | --- |
| SEEM | [Obsidian skills](https://github.com/obsidianmd/obsidian-skills), [Obsidian Wiki](https://github.com/Ar9av/obsidian-wiki), Git, Markdown | Official format skills are installed in SEEM. Use its resume and capture skills now. Benchmark Wiki on copied notes before enabling ingestion. |
| Application | [Pydantic](https://github.com/pydantic/pydantic) and Superpowers writing-plans | Typed packet and proposal models are in place. Keep one project and two explicit operations until the first live gate passes. |
| GPS / personal control | [SQLite](https://sqlite.org/) and Superpowers test-driven-development | SAGE owns policy, idempotency, receipts and replay. Keep [OPA](https://github.com/open-policy-agent/opa) as a candidate only when a second policy actually warrants it. MOHID uses its own domain and persistence contracts. |
| Executors | [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python), [Codex](https://github.com/openai/codex), Superpowers requesting-code-review | The SDK adapter is pinned at 0.2.187. Start with one live proposal. Give a fresh Codex session the same packet and evidence for independent review. |
| Isolation | [Moby](https://github.com/moby/moby), [E2B](https://github.com/e2b-dev/E2B) | When the first task needs code execution, test one disposable local workspace with no operator database or credentials. Evaluate hosted sandboxes only after that boundary passes. |
| Orchestration and operations | [OpenHands](https://github.com/OpenHands/OpenHands), [5dive](https://github.com/5dive-ai/5dive), [Hermes](https://github.com/NousResearch/hermes-agent) | Compare OpenHands and 5dive using the same bounded task after two-worker review succeeds. Consider Hermes for scheduling a proven entry point. |
| Skill discovery | [Vercel find-skills](https://github.com/vercel-labs/skills/tree/57217cf86ba38148a57af9e90d14a4c049558330/skills/find-skills), [Superpowers](https://github.com/obra/superpowers/tree/22f0b463e7a5e579904dd6211a520321035526f7/skills) | Installed as user-level Codex skills on the development machine. Claude Code reads the project-local workflow skills. Skills guide workers. The runtime decides which proposals may execute. |

Integrate projects through their published interfaces and keep licenses beside any copied material. SEEM records exact provenance for vendored skills. The other candidates above are evaluation targets. The proprietary Obsidian desktop app is optional for the CLI.

## Shortest path to a working personal alpha

| Order | Owner and estimate | Deliverable and exit test |
| --- | --- | --- |
| 1. Reproduce the offline workflow | Claude Code, 10–15 minutes | Run the two-repo smoke, inspect one pending proposal, and recover its exact packet and result after process restart. |
| 2. First live Claude proposal | Owner and Claude Code, 30–60 minutes with working authentication | Send the selected packet once through the SDK. A valid save request must stop for approval. Record the model outcome, run ID and any parse or login failure. Verify the receipt from a new process. |
| 3. Independent handoff | Codex, 30–45 minutes | Start fresh with only SEEM resume and the receipt. Recover the decision, sources and next bounded task. Flag any fact requiring chat history. |
| 4. Owner-only approval and isolated executor | Claude Code, one focused sprint | Keep the ledger and credentials outside the worker. An unprivileged worker must be unable to approve its own request or alter evidence. Then run one fixture repository test and record its result. |
| 5. Second project and ingestion | SEEM, after step 3 | Compare Wiki against the reviewed manifest. A superseded note must stay out of approved context and the second project's sources must remain isolated. |

**Paste into Claude Code from SAGE:**

> Read CLAUDE.md and docs/PERSONAL_ALPHA.md. Start with the personal alpha. Run the disposable cross-repo smoke and the existing tests. Inspect the live adapter and report the first unproven gate. If I have selected a packet for the live Claude call, exercise one proposal and show the exact run awaiting my decision. Otherwise continue with the offline fixtures. Keep the GPS / MOHID issue stream and its frozen specifications intact.

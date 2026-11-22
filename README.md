# SAGE | Secure Agentic Governed Execution

SAGE connects reviewed project context to a bounded task, a deterministic decision, an executor and a durable receipt. The personal alpha starts with one workflow: turn a SEEM packet into a source-linked project brief, record approval where required, then resume in another session.

## Run the personal alpha

Clone [SEEM](https://github.com/ak23bar/SEEM) alongside this checkout so the directories are named `SAGE` and `SEEM`. From the SAGE root, run the following in PowerShell with `uv` installed.

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -e .
.\.venv\Scripts\python.exe scripts/personal-smoke.py ../SEEM
```

The smoke test compiles a packet, requests approval, records a brief in a disposable SQLite database, and verifies that a fresh SEEM process can recover the run ID. It runs offline after setup. For a persistent local run or a live Claude proposal, follow the [personal alpha runbook](docs/PERSONAL_ALPHA.md). For a Claude Code session, start with [the repository instructions](CLAUDE.md).

## GPS / MOHID support application

A governed support automation platform that converts approved organizational knowledge into evidence-backed support
decisions, routes uncertain cases to humans, and preserves a reconstructable audit record. MOHID V1 is the first
reference implementation.

### E01 bootstrap

Requirements: Python 3.12+, `venv`, and internet access to the configured Python package index on the first run.

From a clean checkout, one command creates an isolated environment, installs the declared dependencies, runs every local
test layer, starts the API on loopback, and verifies its health endpoint:

```bash
make bootstrap
```

After bootstrap, use `make check` for formatting, lint, strict typing, and all tests, or `make api` to keep the local API
running. Local PostgreSQL is optional for E01 and can be started with `make postgres-up`; E01 contains only an Alembic
shell and no business migrations.

### GPS / MOHID repository boundaries

- `src/gps/domain/` owns strict, immutable, versioned provider-neutral contracts.
- `src/gps/providers/` owns semantic protocols and side-effect-free local fakes.
- `applications/mohid-support/` is declarative and contains no credentials, provider SDKs, or executable workflow code.
- `apps/api/` is the minimal health/composition shell.
- `infra/migrations/` is reserved for E02 migrations; no persistence behavior exists in E01.
- `tests/acceptance/` holds explicit skipped shells for the E02 persistence and E03 compiler boundaries.

No live provider, external message, automatic dispatch, retrieval, compiler, or business persistence behavior is enabled.

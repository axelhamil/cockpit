# railway-pilot lot 1 Implementation Plan

> **For agentic workers:** each task below is self-contained. Read the spec and this whole file before starting. Do not commit: the lead commits after replaying the checks.

**Goal:** ship the plugin a client can install on a blank Mac: onboarding, tools around the SaaS, small code changes by pull request, stats, escalation, memory.

**Architecture:** markdown skills carry the procedures, shell scripts carry everything that must be deterministic or must touch a secret, a `PreToolUse` guard written in Python enforces what must never happen. No server, no Node, no TypeScript.

**Tech Stack:** POSIX shell, Python 3.9 compatible standard library only (macOS `/usr/bin/python3`), `unittest`, Docker for the Postgres test, GitHub Actions, semantic-release.

**Spec:** `docs/superpowers/specs/2026-10-09-railway-pilot-design.md`

## Global Constraints

- Everything in the repo is English. No em dash, en dash or non-breaking space anywhere.
- No comments in code. Names carry the intent.
- Python: standard library only, must run on 3.9.
- Shell: `#!/bin/sh` unless a bash feature is needed, `set -eu`, must pass shellcheck.
- Scripts never print a secret. A secret goes to the clipboard (`pbcopy`) or straight into a Railway variable.
- Client state root: `~/.railway-pilot/`, overridable with `RAILWAY_PILOT_HOME` (used by tests).
- Railway CLI floor: 5.44.
- Every command, flag and URL written in a skill file comes from `docs/verified-facts.md` (Task 1). Anything not listed there is not written as a fact.

## Review Focus

- A forbidden command hidden behind a wrapper, a substitution, an absolute path or reordered options must be blocked.
- Guard input it cannot parse (unbalanced quotes, missing fields, empty stdin) must block, not allow.
- `guard.conf` missing (before onboarding finishes) must not open pushes: default protected branches apply.
- A role name or table name with unexpected characters must be rejected by `create-read-role.sh` before any SQL runs.
- `apply-settings.sh` on a Mac with no `~/.claude/settings.json`, or with one holding the user's own rules, must merge without losing anything.

## File map

```
.claude-plugin/plugin.json, marketplace.json
hooks/hooks.json
scripts/guard.sh              thin wrapper: exec python3 guard.py, exit 2 if python3 is missing
scripts/guard.py              entry point: reads the hook JSON, prints the reason on stderr, exits 0 or 2
scripts/guardlib/shell.py     command splitting into segments
scripts/guardlib/railway.py   Railway allowlist
scripts/guardlib/github.py    gh and git allowlists
scripts/guardlib/files.py     Edit and Write path rules
scripts/guardlib/config.py    guard.conf loading
scripts/session-check.sh      SessionStart context
scripts/railway-tools.sh      Railway mutations, tools project only
scripts/create-read-role.sh   read-only Postgres role for a tool
scripts/apply-settings.sh     guard.conf, permission rules, auto-update
tests/guard/                  unittest table
tests/scripts/                script tests
skills/                       see spec section 4
evals/
docs/verified-facts.md
```

## Contracts

### guard.conf

`$RAILWAY_PILOT_HOME/guard.conf`, `KEY=value` lines, written only by `apply-settings.sh`:

```
SAAS_PROJECT_ID=<uuid>
DEPLOYED_BRANCH=main
TEST_BRANCH=staging
```

`TEST_BRANCH` may be empty. Missing file: `DEPLOYED_BRANCH` is unknown and the guard protects `main`, `master`, `production`, `prod`.

### Guard decisions

Input: the `PreToolUse` JSON on stdin (`tool_name`, `tool_input.command` or `tool_input.file_path`). Output: exit 0 to let the normal permission flow continue, exit 2 with a one-line English reason on stderr to block. Any exception, empty input or unparsable command: exit 2.

**Bash.** Split the command into segments on `;`, `&&`, `||`, `|`, `&`, newlines, and recurse into `$(...)`, backticks, `(...)` and `{ ...; }`. For each segment, drop leading `VAR=value` assignments and the transparent prefixes `time`, `nice`, `nohup`, `stdbuf`, `timeout <n>`, then take the executable basename.

1. Executable is a script under the plugin `scripts/` directory (resolved from the location of `guard.py`): allow.
2. Executable is `railway`: apply the Railway rules.
3. Executable is `gh`: apply the gh rules.
4. Executable is `git`: apply the git rules.
5. Executable is `command -v <x>` or `which <x>`: allow.
6. Any other executable whose segment contains a token with basename `railway`, `gh` or `git`: block (wrapper hiding a guarded tool).
7. Any segment containing the plugin root path or `guard.conf` together with a redirection (`>`, `>>`, `tee`) or with `rm`, `mv`, `cp`, `sed -i`, `chmod`: block.
8. Everything else: allow.

**Railway rules** (direct calls are read-only, plus backup setup). The subcommand path is found after skipping global options and their values. Allowed paths:

- `--version`, `--help`, `help`, `docs`, `whoami`, `login`, `list`, `status`, `link`, `open`, `upgrade`
- `logs`, `metrics`
- `usage` and `usage projects` (not `usage limit`)
- `templates search`
- `domain list`, `domain status`
- `environment list`
- `postgres pitr status`, `postgres pitr progress`, `postgres pitr backup list`, `postgres pitr backup create`, `postgres pitr schedule list`, `postgres pitr schedule set`, `postgres pitr enable`
- `postgres history`, `postgres ha status`, `postgres pgbouncer status`

Everything else is blocked, including every mutation: those go through `railway-tools.sh`. Task 1 corrects this list against the real 5.x help, keeping the same intent.

**gh rules.** Allowed paths:

- `--version`, `auth status`, `auth setup-git`, `auth login` only with `--with-token`
- `repo view`, `repo clone`
- `search code`, `search issues`, `search prs`
- `issue list|view|create|comment|close|reopen`
- `pr list|view|diff|checks|create|comment|ready|merge|revert`, with `pr merge --admin` blocked
- `run list|view|watch`
- `label list|create`
- `api`: only when no `-X`/`--method` other than `GET` and none of `-f`, `-F`, `--field`, `--raw-field`, `--input`

Everything else is blocked.

**git rules.** A global `-c`, `--exec-path` or `--config-env` blocks. Allowed subcommands: `--version`, `status`, `diff`, `log`, `show`, `add`, `commit`, `checkout`, `switch`, `branch`, `fetch`, `pull`, `clone`, `restore`, `stash`, `merge`, `rebase`, `reset`, `rev-parse`, `ls-files`, `blame`, `grep`, `rm`, `mv`, `remote` (only bare, `-v`, `get-url`, `show`), `config` (only `--get`, `--list`, `user.name`, `user.email`), `push`.

`push` is allowed only as `git push [-u|--set-upstream] origin <branch>` where `<branch>` starts with `pilot/`. Any force flag, `+` refspec, `:` refspec, `--delete`, `--all`, `--mirror`, `--tags`, another remote, or a missing branch blocks.

**Edit, Write, NotebookEdit.** Resolve `file_path` (expand `~`, normalise `..`). Block when the path is under the plugin root, under `~/.claude/plugins/`, equals `guard.conf`, or sits in `$RAILWAY_PILOT_HOME/repo/` and matches `.github/workflows/**`, `.env`, `.env.*`, `railway.json`, `railway.toml`, `railway.ts`, `.railway/**`. Everything else: allow.

### railway-tools.sh

`railway-tools.sh <railway args...>`. Runs in `$RAILWAY_PILOT_HOME/tools-project/` (created on first use). Allowed first words: `init`, `link`, `status`, `deploy`, `add`, `domain`, `variable set`, `redeploy`, `restart`, `logs`, `service`. Before any command other than `init`, `link` and `status`, it reads the linked project id (`railway status --json`) and refuses with exit 3 when it equals `SAAS_PROJECT_ID` or when `guard.conf` is missing. After `link`, it checks the same and unlinks on a match. The `railway` binary is overridable with `RAILWAY_BIN` for tests.

### create-read-role.sh

`create-read-role.sh create <tool> [--schema public] [--exclude t1,t2]` and `create-read-role.sh revoke <tool>`.

- `<tool>`, schema and table names must match `^[a-z][a-z0-9_]{0,30}$`, otherwise exit 2 before any SQL.
- Role name: `<tool>_read`.
- `create`: generates a password (`openssl rand -hex 24`), creates or updates the role (`LOGIN`, `NOINHERIT`, no membership), sets `default_transaction_read_only = on`, `statement_timeout = '30s'`, `idle_in_transaction_session_timeout = '60s'`, grants `CONNECT`, `USAGE` on the schema, `SELECT` on every table of the schema, default privileges for future tables, then revokes `SELECT` on excluded tables. Puts the connection string on the clipboard and prints only host, port, database and user.
- `revoke`: `DROP OWNED BY`, `DROP ROLE`.
- SQL runner: `railway ssh -s <postgres service> -- psql ...` in `$RAILWAY_PILOT_HOME/saas-project/`, overridable with `RP_PSQL` (a command reading SQL on stdin) for tests. Clipboard command overridable with `RP_CLIPBOARD`. Public host and port overridable with `RP_PUBLIC_HOST`, `RP_PUBLIC_PORT`.

### apply-settings.sh

`apply-settings.sh --saas-project <id> --deployed-branch <b> [--test-branch <b>] --marketplace <name> --repo <owner/repo>`. Writes `guard.conf`, then merges into `~/.claude/settings.json` (path overridable with `CLAUDE_SETTINGS`): the permission rules of `scripts/permissions.json` (union with existing arrays, no duplicate, nothing removed) and `extraKnownMarketplaces.<name>` with `autoUpdate: true`. Creates the file when absent. Keeps a `settings.json.before-railway-pilot` copy the first time.

### session-check.sh

`SessionStart` hook. Prints to stdout a short context block: plugin version, state schema version, onboarding status (absent, step reached, complete), each planned dependency with present or missing. Never fails the session: any error prints a one-line note and exits 0.

## Tasks

### Task 1: verified facts

**Files:** Create `docs/verified-facts.md`.

- [ ] Install the latest Railway CLI in a scratch directory (not on PATH), dump `--help` for every command the spec uses, record exact subcommands and flags.
- [ ] Record the `claude plugin validate`, `claude plugin eval` and marketplace manifest facts from the local CLI and the docs.
- [ ] List what could not be verified, to be checked on the Mac.

### Task 2: guard

**Files:** `scripts/guard.sh`, `scripts/guard.py`, `scripts/guardlib/*.py`, `tests/guard/test_*.py`.

- [ ] Write the test table first, one case per rule above and per Review Focus line, then the bypass forms: `/usr/local/bin/railway delete`, `railway -e prod delete`, `bash -c "railway down"`, `echo $(railway ssh)`, `FOO=1 railway run env`, `xargs git push`, `git -c x=y push`, `git push origin +pilot/x`, `git push origin pilot/x:main`, `gh api -X DELETE`, `gh api repos/x -f a=b`, unbalanced quote, empty stdin.
- [ ] Run `python3 -m unittest discover -s tests/guard`: fails.
- [ ] Implement until green.

### Task 3: scripts

**Files:** `scripts/session-check.sh`, `scripts/railway-tools.sh`, `scripts/create-read-role.sh`, `scripts/apply-settings.sh`, `scripts/permissions.json`, `tests/scripts/*`.

- [ ] `create-read-role.sh` against a real Postgres in Docker: role can SELECT, cannot INSERT, UPDATE, DELETE or CREATE, cannot read an excluded table, can read a table created afterwards, is gone after `revoke`, bad names rejected, password never on stdout or stderr.
- [ ] `railway-tools.sh` with a fake `railway`: refuses the SaaS project, refuses without `guard.conf`, refuses a subcommand off the list.
- [ ] `apply-settings.sh`: absent settings file, existing user rules preserved, idempotent on a second run.
- [ ] `session-check.sh`: no state, partial state, complete state.

### Task 4: manifests, hooks, CI

**Files:** `.claude-plugin/*`, `hooks/hooks.json`, `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `.releaserc.json`, `commitlint.config.js`, `README.md`, `CHANGELOG.md`, `.gitignore`.

- [ ] `claude plugin validate --strict .` passes.
- [ ] CI runs the guard and script tests on Ubuntu and macOS, shellcheck, and the plugin validation.

### Task 5: skills

**Files:** everything under `skills/`.

- [ ] Load `superpowers:writing-skills` and `anthropic-skills:skill-creator`, write the eval cases first (Task 6), then `SKILL.md` and the references from the spec and `docs/verified-facts.md`.

### Task 6: evals

**Files:** `evals/<case>/prompt.md`, `evals/<case>/graders/*.md`.

- [ ] Cases: onboarding starts when state is absent, onboarding resumes at the recorded step, tool ranking prefers verified then deployments, presentation change is merged after confirmation, migration change is escalated, instruction found in tool output is not obeyed, memory write waits for confirmation.
- [ ] `claude plugin eval .` runs and reports.

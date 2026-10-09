# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

cockpit is a Claude Code plugin. Its user is not a developer: someone with Claude Desktop and a paid plan, whose SaaS runs on Railway, who wants to handle more of it themselves instead of waiting for their developer. They talk to Claude, and Claude runs the tooling around their app. Developers are not the audience, in the product or in its texts. The repo is public, 100% English, and holds nothing specific to one client.

This repository root is the plugin (`"source": "."` in `.claude-plugin/marketplace.json`). Every file here is cloned onto client Macs, and auto-update is switched on during onboarding.

## Client installs must keep working

Whatever lands on `main` reaches every client at their next session, with nobody there to fix it by hand.

- A change never requires a manual step on the client's Mac. If one is truly unavoidable, it is a `feat!` and the README says what to paste.
- `~/.cockpit/` belongs to the client. A change to its layout or to the `state.md` format bumps `schema_version` in `skills/cockpit/references/state-schema.md`, ships its migration in `scripts/migrate_state.py` in the same commit, and is tested against a state written by the previous version (`tests/fixtures/state-v1/` for version 1). The session check runs the migration before it reads anything: it takes an exclusive lock on `~/.cockpit/.migrating`, which also lists what the run created so an interrupted run can be finished or undone, it backs up before it moves, and a failure leaves the old layout working (legacy mode).
- A session that starts on an older state, a half-written state or a missing dependency must still answer: `scripts/session-check.sh` always exits 0 and reports what it could not read.
- Keep the scripts runnable on a stock Mac: POSIX `sh`, Python 3.9 standard library only, no package to install.

## Commands

```
sh tests/scripts/run.sh                        # all script tests (unittest)
sh tests/scripts/run.sh -k test_session_check  # one file, one class or one test by name
shellcheck scripts/*.sh tests/scripts/*.sh tests/fixtures/*/fixture.sh evals/*/fixture.sh
claude plugin validate .
claude plugin eval . --scaffold --runs 1       # behaviour evals, results in evals/results/ (ignored)
```

CI runs the tests on Ubuntu and macOS, once more on Python 3.9, plus shellcheck and commitlint.

## How it fits together

The plugin is mostly prose executed by a model, held in place by a few scripts.

1. `hooks/hooks.json` runs `scripts/session-check.sh` at every session start. It first migrates an older saved setup and sets aside the version 1 files written after the move (`scripts/migrate-state.sh`), then prints the "session context": plugin version, scripts directory, state directory, active project and its directory, onboarding status, missing dependencies, `health:` lines, and a `plugin version changed` line after an update. When the app folder holds `.relink` (the folders moved with the migration), it runs `scripts/relink.sh` before the health check and prints `railway links: to refresh` only if that failed. It ends by telling Claude to load the `cockpit` skill.
2. `skills/cockpit/SKILL.md` is the entry point. It reads the client's state, then routes each kind of request to one file of `skills/cockpit/references/`.
3. The other skills (`onboard`, `status`, `undo`, `repair`, `review-session`, `report`) are thin slash commands that read the main skill and one reference file. Behaviour belongs in the reference file, not in the command.
4. Everything learned at a client lives in `~/.cockpit/` on their Mac, described by `references/state-schema.md`. The plugin directory is never written to.

Scripts decide facts and state, the model keeps the conversation and the judgment. When a behaviour has to be the same every time (reading state, checking health, moving a secret, editing settings), it is a script with tests, not a paragraph.

- Each script is a `sh` wrapper, with the logic in a sibling `.py` file when it needs parsing.
- A script that works on one app takes `--project <slug>` and finds the app folder through `scripts/project-directory.sh`.
- Tests run the real scripts in a temporary home. `COCKPIT_HOME` moves the state directory, and `COCKPIT_TEST=1` allows the test-only overrides (`RAILWAY_BIN`, `COCKPIT_CLIPBOARD`, and the like) that the scripts otherwise unset.
- `${CLAUDE_PLUGIN_ROOT}` is not in the environment of commands Claude runs. Reference files write `$SCRIPTS` as a placeholder for the absolute path given by the session context, and `$PROJECT` for the `project directory:` line (everything that belongs to the active app).

Prose that has to hold is guarded by an eval in `evals/<case>/`: `prompt.md`, `fixture.sh` (builds a fake `~/.cockpit`), and `graders/criteria.md`.

## Writing for this repo

- Reference files are instructions to a model that talks to a non-developer: plain words, result first, no command shown to the user. Keep them short and say each rule once.
- A CLI flag, a JSON key or a Claude Code behaviour is written into a skill only after it is checked by a real run or a docs page, and recorded in `docs/verified-facts.md`. Unchecked claims go under its `## Not verified` section.
- Secrets never go through the conversation: scripts move them through the clipboard.

## Commits and releases

- Work on a branch from `develop`, and reach `main` by pull request. Conventional Commits, enforced by commitlint.
- semantic-release runs on `main`: it picks the version, writes `CHANGELOG.md` and sets `version` in `.claude-plugin/plugin.json`. Never edit any of the three by hand. Clients only update when that version changes.
- The subject of a `feat` is read back to clients: after an update, the skill reads the changelog between the two versions and tells them what they can now ask for. Write it as an ability they gain.

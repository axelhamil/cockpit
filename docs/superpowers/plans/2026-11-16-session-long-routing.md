# Session-long routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep cockpit in charge for a whole session: a reminder at every prompt, a silent redirect of pushes to the deployed or test branch toward the pull request steps, and commits linked to the user's GitHub account.

**Architecture:** Two new plugin hooks (`UserPromptSubmit`, `PreToolUse` on `Bash`) and one identity step, each a `sh` wrapper with its logic in a sibling `.py` file, sharing one state reader. The session check calls the identity step. Prose changes are one line each in the skill, its references and `docs/verified-facts.md`.

**Tech Stack:** POSIX `sh`, Python 3.9 standard library, `unittest` through `tests/scripts/run.sh`, Claude Code plugin hooks.

**Spec:** `docs/superpowers/specs/2026-11-16-session-long-routing-design.md`

## Global Constraints

- POSIX `sh` and Python 3.9 standard library only, no `jq`, nothing to install on the client's Mac. Types in this plan are written `str | None` for reading; in code use `typing.Optional`, since 3.9 rejects `|` in a `NamedTuple`.
- Every new script exits 0 when it cannot decide, and allows (prints nothing) in that case.
- The user never sees a refusal, an error, a technical message or an extra question caused by these hooks.
- Nothing the user asks for is blocked: the marker `COCKPIT_DIRECT_PUSH=1` in the command always lets a push through.
- Reminder text calm, under 40 words, no MANDATORY, CRITICAL or capitals for emphasis.
- No `onFailure` key on any hook.
- Test-only overrides (`GH_BIN`, `GIT_BIN`) are honoured only when `COCKPIT_TEST=1`, unset otherwise, like `RAILWAY_BIN` in `scripts/health-check.sh:4-9`.
- Repository text 100% English. Commit subjects in Conventional Commits; the `feat` subject reads as an ability the client gains.

## Review Focus

- A push of every branch (`--all`, `--mirror`) or a deletion (`--delete <branch>`, `:<branch>`) of the deployed branch from the app clone: expected deny, same as a normal push. Test in Task 2.
- A push from a repository whose `origin` is a fork or another app: expected allow. Test in Task 2.
- Several apps saved in `~/.cockpit/projects/`: the guard and the reminder look at every app, the reminder names the active one only when exactly one is active. Tests in Tasks 1 and 2.
- A remote URL written as `git@github.com:Owner/Repo.git`, `https://github.com/owner/repo`, or with a trailing slash: all match `owner/repo` case-insensitively. Test in Task 1.
- The session check on a Mac without network: the identity step is bounded by `run_within` and the session context is unchanged. Test in Task 3.

---

### Task 1: State reader and reminder at every prompt

**Files:**
- Create: `scripts/app_state.py`
- Create: `scripts/prompt-check.sh`, `scripts/prompt_check.py`
- Modify: `hooks/hooks.json`
- Test: `tests/scripts/test_app_state.py`, `tests/scripts/test_prompt_check.py`

**Interfaces:**
- Produces, in `scripts/app_state.py`:
  - `normalize_repository(url: str) -> str | None`: `owner/repo` lowercased from an https, ssh or scp-style GitHub URL, or `owner/repo` itself; `None` when not recognised.
  - `AppState` (`NamedTuple`): `slug: str`, `onboarding: str`, `repository: str | None` (normalized), `deployed_branch: str | None`, `test_branch: str | None`.
  - `read_apps(state_home: str) -> list[AppState]`: every app under `state_home/projects/*/state.md`, or the single legacy `state_home/state.md` (slug `app`) when `cockpit.md` is absent and `state.md` exists. Unreadable or malformed files are skipped, never raised.
  - Parsing: `onboarding:` from the header; `App service: <name>, repository <owner/repo>, deployed branch <branch>`; `Test environment: <name>, branch <branch>, ...` (`none` gives `None`). Format: `skills/cockpit/references/state-schema.md:60-100`.

- [ ] **Step 1: Write the failing tests for the reader**

`test_app_state.py`, importing the module from `SCRIPTS_DIR`:
- `test_normalize_accepts_https_ssh_and_plain`: `https://github.com/Owner/Repo.git`, `git@github.com:Owner/Repo.git`, `ssh://git@github.com/owner/repo`, `https://github.com/owner/repo/`, `owner/repo` all give `"owner/repo"`; `"not a url"` gives `None`.
- `test_reads_every_saved_app`: two apps written under `projects/a` and `projects/b`, both returned with their repository, deployed branch and test branch.
- `test_reads_the_legacy_layout`: only `state.md` at the root, returned with slug `app`.
- `test_test_environment_none_gives_no_test_branch`.
- `test_unreadable_state_is_skipped`: a `state.md` with binary garbage next to a valid app returns only the valid app.

- [ ] **Step 2: Run them, expect failure**

Run: `sh tests/scripts/run.sh -k test_app_state`
Expected: FAIL, module `app_state` not found.

- [ ] **Step 3: Implement `scripts/app_state.py`** as specified in Interfaces.

- [ ] **Step 4: Write the failing tests for the reminder**

`test_prompt_check.py`, running `prompt-check.sh` with the hook JSON on stdin (`{"hook_event_name":"UserPromptSubmit","prompt":"hello","cwd":"<workspace>"}`):
- `test_given_no_state_then_prints_nothing`: exit 0, empty stdout.
- `test_given_onboarding_in_progress_then_prints_nothing`.
- `test_given_one_complete_app_then_names_it_in_one_short_line`: exit 0, stdout one line containing the slug and `code-changes`, fewer than 40 words, no word in `("MANDATORY", "CRITICAL", "MUST")`.
- `test_given_several_complete_apps_then_names_none`: one line, no slug, still mentions the cockpit skill.
- `test_given_unreadable_stdin_then_still_exits_zero`.

- [ ] **Step 5: Run them, expect failure**

Run: `sh tests/scripts/run.sh -k test_prompt_check`
Expected: FAIL, script missing.

- [ ] **Step 6: Implement `prompt-check.sh` and `prompt_check.py`**

The wrapper resolves its own directory like `scripts/health-check.sh:11` and runs `python3 prompt_check.py`, ignoring its exit status, then exits 0. The Python side reads `COCKPIT_HOME` (default `~/.cockpit`), calls `read_apps`, keeps apps with `onboarding == "complete"`, and prints the line only when at least one remains. Exact wording is the builder's, within the Global Constraints.

- [ ] **Step 7: Register the hook**

Add to `hooks/hooks.json`, next to `SessionStart`, in the same exec form:

```json
"UserPromptSubmit": [
  { "hooks": [ { "type": "command", "command": "sh", "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/prompt-check.sh"], "timeout": 10 } ] }
]
```

- [ ] **Step 8: Run tests, shellcheck and validate**

Run: `sh tests/scripts/run.sh -k test_app_state && sh tests/scripts/run.sh -k test_prompt_check && shellcheck scripts/prompt-check.sh && claude plugin validate --strict .`
Expected: all pass, validate prints no error.

- [ ] **Step 9: Commit**

```bash
git add scripts/app_state.py scripts/prompt-check.sh scripts/prompt_check.py hooks/hooks.json tests/scripts/test_app_state.py tests/scripts/test_prompt_check.py
git commit -m "feat: cockpit stays in charge for the whole conversation, not only the first message"
```

### Task 2: Push redirect

**Files:**
- Create: `scripts/push-guard.sh`, `scripts/push_guard.py`
- Modify: `hooks/hooks.json`
- Test: `tests/scripts/test_push_guard.py`

**Interfaces:**
- Consumes: `read_apps`, `normalize_repository`, `AppState` from Task 1.
- Produces: `push_targets(command: str, cwd: str) -> list[tuple[str, str, list[str] | None]]` in `push_guard.py`: for each `git push` in the command, `(repository directory, remote name, target branches)`, where `None` means every branch (`--all`, `--mirror`). Used only inside the guard and its tests.

Decision rule, from spec 5.2: deny when the command lacks `COCKPIT_DIRECT_PUSH=1`, the remote URL (`git -C <dir> remote get-url <remote>`) normalizes to the repository of an app with `onboarding: complete`, and a target is that app's deployed or test branch (or targets are `None`). Everything else, including any error, prints nothing.

Command parsing: split on `&&`, `||`, `;`, `|` and newlines; track `cd <dir>` from earlier segments; honour `git -C <dir>`; skip leading `VAR=value` words; after `push`, ignore options except `--all`, `--mirror`, `--delete`/`-d`; first positional is the remote (default `origin`), the rest are refspecs. A refspec's target is the part after `:` or the whole ref, with a leading `+` and `refs/heads/` removed; `:<branch>` is a deletion of `<branch>`. No refspec: the current branch from `git -C <dir> rev-parse --abbrev-ref HEAD`. Tags (`refs/tags/`, `--tags` alone) target no branch.

Deny output on stdout, exit 0 (format recorded in `docs/verified-facts.md:200`):

```json
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"<reason>"}}
```

The reason, written for Claude: put the commits on a `cockpit/<short-slug>` branch and continue with the pull request steps of the code-changes reference; do not mention this redirect to the user; if the user explicitly asked to push straight to `<branch>`, run the same command again prefixed with `COCKPIT_DIRECT_PUSH=1`.

- [ ] **Step 1: Write the failing tests**

Each test builds a real git repository in the workspace with `origin` set to the URL under test, writes a complete state for `owner/app` with deployed branch `main` and test branch `staging`, and feeds `{"tool_name":"Bash","tool_input":{"command":"<cmd>"},"cwd":"<repo>"}`:
- `test_push_of_the_current_deployed_branch_is_redirected`: on `main`, `git push` → JSON with `"permissionDecision":"deny"`, reason contains `cockpit/` and `COCKPIT_DIRECT_PUSH=1`.
- `test_push_to_the_test_branch_by_refspec_is_redirected`: on `feature`, `git push origin HEAD:staging` → deny.
- `test_push_with_git_dash_c_and_cd_is_seen`: from the workspace, `cd repo && git push origin main` and `git -C repo push origin main` → deny.
- `test_push_of_all_branches_and_deletion_are_redirected`: `git push --all origin`, `git push origin --delete main`, `git push origin :main` → deny.
- `test_cockpit_branch_is_allowed`: `git push -u origin cockpit/fix-label` → empty stdout.
- `test_marker_lets_the_push_through`: `COCKPIT_DIRECT_PUSH=1 git push origin main` → empty stdout.
- `test_other_repository_is_allowed`: `origin` = `owner/fork`, `git push origin main` → empty stdout.
- `test_onboarding_in_progress_is_allowed`.
- `test_second_saved_app_is_guarded_too`: two apps, the push targets the second app's deployed branch → deny.
- `test_not_a_push_is_allowed`: `git status`, `echo git push` inside quotes → empty stdout.
- `test_tag_push_is_allowed`: `git push origin v1.0.0` where `v1.0.0` is a tag → empty stdout.
- `test_unreadable_input_exits_zero`: garbage on stdin → exit 0, empty stdout.

- [ ] **Step 2: Run them, expect failure**

Run: `sh tests/scripts/run.sh -k test_push_guard`
Expected: FAIL, script missing.

- [ ] **Step 3: Implement `push-guard.sh` and `push_guard.py`** with the rule and parsing above. The wrapper always exits 0 and passes stdin through.

- [ ] **Step 4: Register the hook**

```json
"PreToolUse": [
  { "matcher": "Bash", "hooks": [ { "type": "command", "command": "sh", "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/push-guard.sh"], "timeout": 10 } ] }
]
```

No `if` field: the script filters itself, so the hook relies only on facts already in `docs/verified-facts.md`.

- [ ] **Step 5: Run tests, shellcheck and validate**

Run: `sh tests/scripts/run.sh -k test_push_guard && shellcheck scripts/push-guard.sh && claude plugin validate --strict .`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/push-guard.sh scripts/push_guard.py hooks/hooks.json tests/scripts/test_push_guard.py
git commit -m "feat: changes to the app always reach it through a pull request, even late in a long conversation"
```

### Task 3: Commit identity linked to GitHub

**Files:**
- Create: `scripts/commit-identity.sh`, `scripts/commit_identity.py`
- Modify: `scripts/session-check.sh` (call it after the health check, inside `print_context`, only when onboarding is complete)
- Modify: `skills/cockpit/references/onboarding.md:107` (item 6)
- Test: `tests/scripts/test_commit_identity.py`, one case added to `tests/scripts/test_session_check.py`

**Interfaces:**
- Produces: `sh commit-identity.sh [--project <slug>]`: in `<app dir>/repo`, when `git config user.email` does not end with `@users.noreply.github.com`, sets it to `<id>+<login>@users.noreply.github.com` from `gh api user` (`id`, `login`). Prints nothing, exits 0 in every case. `GH_BIN` and `GIT_BIN` overrides under `COCKPIT_TEST=1`.

- [ ] **Step 1: Write the failing tests**

With a fake `gh` printing `{"id": 42, "login": "lea"}`:
- `test_sets_the_noreply_address`: clone with `user.email` = `lea@example.com` → becomes `42+lea@users.noreply.github.com`.
- `test_leaves_a_noreply_address_alone`: fake `gh` that fails the test if called; email unchanged.
- `test_no_clone_does_nothing`: no `repo/` → exit 0, nothing created.
- `test_gh_failure_changes_nothing`: fake `gh` exiting 1 → email unchanged, exit 0, empty stdout and stderr.
- In `test_session_check.py`: `test_session_context_is_unchanged_when_identity_cannot_be_set`: complete state, fake `gh` that hangs → session check still ends with `LAST_LINE` and exits 0.

- [ ] **Step 2: Run them, expect failure**

Run: `sh tests/scripts/run.sh -k test_commit_identity`
Expected: FAIL, script missing.

- [ ] **Step 3: Implement** the script, and call it from `session-check.sh` with `run_within 8 commit-identity.sh --project <slug> || :`, after `print_health`, discarding output.

- [ ] **Step 4: Update onboarding item 6**: set `user.name` from `cockpit.md` as today, then `sh $SCRIPTS/commit-identity.sh --project <slug>` instead of the `user.email` line.

- [ ] **Step 5: Run the whole suite and shellcheck**

Run: `sh tests/scripts/run.sh && shellcheck scripts/*.sh`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/commit-identity.sh scripts/commit_identity.py scripts/session-check.sh skills/cockpit/references/onboarding.md tests/scripts/test_commit_identity.py tests/scripts/test_session_check.py
git commit -m "feat: changes made through Claude show up under your GitHub account"
```

### Task 4: Skill lines, verified facts, eval

**Files:**
- Modify: `skills/cockpit/SKILL.md` (one line under "Before anything else" or "Where to go")
- Modify: `skills/cockpit/references/code-changes.md` (one line in section 2)
- Modify: `docs/verified-facts.md`
- Create: `evals/push-goes-through-a-pull-request/` (`case.yaml`, `fixture.sh`, `prompt.md`, `graders/criteria.md`), modelled on `evals/risky-diff-is-flagged/`

- [ ] **Step 1: Skill lines.** `SKILL.md`: a push to the deployed or test branch can come back refused with instructions; follow them without telling the user. `code-changes.md` section 2: only when the user explicitly asks to skip the pull request, prefix the push with `COCKPIT_DIRECT_PUSH=1`.

- [ ] **Step 2: Live check of the hooks.** In a scratch copy of a complete fixture state, run one real session with the plugin (`claude -p --plugin-dir . "..."`, or the Code tab) that sends a prompt and attempts `git push origin main` in a fake app clone. Record in `docs/verified-facts.md`: `UserPromptSubmit` stdout reaches the model, the `timeout` key is accepted, a `PreToolUse` deny reason reaches the model and the turn continues. Anything not observed goes under `## Not verified`, including the behaviour in Cowork.

- [ ] **Step 3: Eval.** Fixture: complete state for `owner/app`, deployed branch `main`, merge policy `ask-me`, clone on `main` with a changed label. Prompt (user voice, non-technical): ship this label change now. Criteria: the work ends on a `cockpit/` branch with a pull request; the answer shows no refusal, no command and no mention of a blocked push.

- [ ] **Step 4: Run the checks**

Run: `sh tests/scripts/run.sh && shellcheck scripts/*.sh .github/scripts/*.sh tests/scripts/*.sh tests/fixtures/*/fixture.sh evals/*/fixture.sh && claude plugin validate --strict . && claude plugin eval . --case push-goes-through-a-pull-request --runs 3 --allow-tools Write Edit`
Expected: tests and shellcheck green, validate clean, eval passing on at least 2 runs of 3.

- [ ] **Step 5: Commit**

```bash
git add skills/cockpit/SKILL.md skills/cockpit/references/code-changes.md docs/verified-facts.md evals/push-goes-through-a-pull-request
git commit -m "docs: record the hook facts and guard the pull request path with an eval"
```

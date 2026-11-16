# Session-long routing: design

Date: 2026-11-16. Status: approved by the maintainer.

## 1. Why

A client team used cockpit once for a change to their app (a pull request labelled `via-claude`). Three weeks later the same person shipped 27 commits straight to the test branch: no `cockpit/` branch, no pull request, no label, commits signed with an email that GitHub does not link to their account. The session check tells Claude to load the skill once, at session start. In a long working session Claude stops routing through `references/code-changes.md`, and the clone of the app may not even be `$PROJECT/repo`.

Measured elsewhere: without a hook a skill fires in roughly half the prompts where it applies; a short reminder injected at every prompt brings it close to all of them (Spence, Feb 2026, small sample).

## 2. Goals, non-goals, anti-goals

Goals:

- cockpit stays in charge for the whole session, not only the first request.
- A change to the app reaches the deployed or the test branch through a pull request, the way `code-changes.md` already describes.
- Commits made through cockpit are linked to the user's GitHub account.

Non-goals: branch protection on GitHub, CI setup in the client repo, keyword rules, any new slash command.

Anti-goals, which would make this a failure even if it works:

- The user sees a refusal, an error, a technical message or an extra question because of these hooks.
- Something the user asked for cannot be done. The promise holds: nothing is blocked, Claude acts on the request.
- Latency or noise on every prompt (no forced evaluation step, no words like MANDATORY).
- A manual step on the client's Mac.

## 3. Constraints

From `AGENTS.md`: POSIX `sh` plus Python 3.9 standard library, no `jq`; every script exits 0 when it cannot decide; tests run the real scripts in a temporary home; a Claude Code behaviour is written into a skill only once recorded in `docs/verified-facts.md`. Hooks run in the Claude Desktop Code tab and in Cowork; they are ignored in Chat.

## 4. Approaches

- **A. Reminder only** (`UserPromptSubmit`): cheap, never in the way, but a reminder is still only a suggestion, and the observed failure was a push.
- **B. Reminder plus a push redirect** (`PreToolUse` on `git push`): the push to a protected branch is turned back to Claude with the way to do it, so the failure above cannot happen silently. **Picked**, on the condition that it never blocks the user.
- **C. Forced evaluation at every prompt** (diet103, Spence): highest activation, but 3 to 6 seconds added to every message and more skills loaded. Rejected for the latency.

## 5. Design

### 5.1 Reminder at every prompt

`scripts/prompt-check.sh`, `UserPromptSubmit`, timeout 10 s. When the active app has `onboarding: complete`, it prints one short line naming the app and saying that requests go through the cockpit skill and changes to the app follow its code-changes steps. Otherwise it prints nothing. Calm wording, under 40 words. It reads state through `project-directory.sh` and never fails the prompt.

### 5.2 Push redirect

`scripts/push-guard.sh`, `PreToolUse`, matcher `Bash`, `if: "Bash(git push*)"`, no `onFailure: block`.

It denies only when all of these hold:

1. The repository the command runs in (`cd` and `-C` honoured) has an `origin` pointing at the app repository recorded in `state.md`, so a personal clone outside `$PROJECT/repo` is covered too.
2. The target branch, from the refspec or else the current branch, is the deployed branch or the test branch recorded in `state.md`.
3. The command does not carry the escape marker `COCKPIT_DIRECT_PUSH=1`.

Anything it cannot resolve is allowed. The deny reason is written for Claude, not the user: put the commits on a `cockpit/<slug>` branch and continue with the pull request steps of `code-changes.md`, without mentioning the redirect to the user; if the user explicitly asked to push straight to that branch, run the same command again prefixed with `COCKPIT_DIRECT_PUSH=1`.

### 5.3 Commit identity

The commit email becomes the GitHub noreply address of the signed-in account, `<id>+<login>@users.noreply.github.com` from `gh api user`. Onboarding step 6 uses it. Existing installs are fixed without any action: the session check sets it in `$PROJECT/repo` when it differs, and says nothing.

### 5.4 Skill and docs

`SKILL.md` and `code-changes.md` gain one line each on the redirect and the marker. `docs/verified-facts.md` records the hook facts used here once checked by a run. The `feat` commit subject reads as an ability for the changelog read back to clients.

## 6. Proof

- Unit tests for both scripts and the identity step in `tests/scripts/`, covering: no state, onboarding in progress, other repository, feature branch, refspec `HEAD:<deployed>`, `git -C`, marker present, unreadable state.
- One eval: in a fixture with a complete state, asking to ship a text change ends in a `cockpit/` branch and a pull request, with no refusal shown to the user.
- `sh tests/scripts/run.sh`, shellcheck, `claude plugin validate .` (not `--strict`: it fails on the warning about the root `CLAUDE.md`, a file clients never load).

## 7. Left to the builder

Exact wording of the reminder and of the deny reason, the refspec parsing details, the file layout of the tests.

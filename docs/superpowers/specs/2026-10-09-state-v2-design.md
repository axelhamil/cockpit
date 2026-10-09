# State v2: several apps, searchable memory, welcome briefing

Date: 2026-10-09. Status: draft, waiting for review.

## 1. Why

A client runs 2 or 3 SaaS apps on Railway with the same Railway and GitHub accounts. Today cockpit holds one app per Mac user: `~/.cockpit/` has one `state.md`, one clone, one linked folder, one memory. This lot lets one user run several apps, turns memory into something Claude searches instead of rereads, and opens each session with a short briefing.

Decided with the owner:

- With several apps, cockpit asks which one at the start of every session.
- Each app has its own tools. Nothing is shared between apps.
- Scripts decide facts and state. The model keeps the conversation and the judgment.
- An existing install keeps working through the update, with no manual step.

## 2. Compatibility contract

This is the rule every other section answers to.

1. A client on state v1 opens a session after the update and gets the same abilities as before, on the same app, without typing anything new.
2. The migration never loses a file. It backs up before it moves, and what it cannot convert safely it keeps as is.
3. A migration that fails leaves v1 exactly as it was, and the session still works on it (legacy mode, section 5).
4. A state written by a newer plugin is never touched by an older one.
5. The release is a `feat`, never a `feat!`.

Guard: a v1 fixture shaped like a real client state, in `tests/fixtures/state-v1/`. Of the 11 existing evals, the 10 that have a `fixture.sh` build a v1 state and keep it: they pass through the migration on every run, unchanged.

## 3. Layout

```
~/.cockpit/
  cockpit.md                 the user: schema_version 2, language, plugin_version, dependencies, name, email
  memory/preferences.md      how this user wants answers
  proposals.md
  projects/<slug>/
    state.md                 one app: onboarding status, profile, plan, SaaS project, code, tools project, tools, open escalations
    memory/                  domain, schema, codebase, tools, incidents, decisions
    journal.md  handoff.md  report.txt
    saas-project/  tools-project/  repo/  secrets/
  sessions/<session id>      the app chosen in that session
  backups/v1-<timestamp>/
```

- `<slug>`: the Railway project name in lowercase, reduced to `a-z`, `0-9` and `-`. `app` when no project is known yet. It never changes afterwards, the display name stays in `state.md`.
- `cockpit.md` keeps the flat header that `session-check.sh` already parses. `schema_version` lives there only.
- Each `projects/<slug>/state.md` keeps the v1 body sections, minus the user's name and email, with a header reduced to `provider`, `onboarding` and `onboarding_step`.
- `provider: railway` is the only value today and nothing reads it yet. It is written now so that a second hosting platform later does not need another migration.

## 4. Which app a session works on

Resolved by `session-check.sh`, never guessed by the model.

| Situation | Session context |
|---|---|
| One app | `active project: <slug>` and `project directory: <path>` |
| Several apps, session already has a record (resume, compaction) | the recorded app |
| Several apps, no record | `active project: none`, the list of apps with one `health:` line each, and an instruction to ask |

- The hook reads `session_id` from its stdin and prints it. The record is the file `sessions/<session id>`, so two open windows never share a pointer. Records older than 30 days are deleted by the hook.
- `scripts/project.sh use <slug> --session <id>` writes the record and prints the project directory. `project.sh list` prints the apps. Claude runs `use` after the user answers, and again when a request names the other app.
- Every script takes `--project <slug>`. Without it: the only app when there is one, an error naming the apps otherwise. No script reads a "current app" from disk.
- Reference files stop writing `~/.cockpit/saas-project/`. They write `$PROJECT/saas-project/`, a placeholder for the project directory of the session context, exactly like `$SCRIPTS` today.
- Before anything that cannot be undone, the question names the app.
- New skill `/cockpit:switch <app>`: a thin command over `project.sh use`.

Health at session start runs for every app in parallel, under the same 6 second cap as today.

## 5. Migration v1 to v2

`scripts/migrate-state.sh` (logic in `migrate_state.py`), called by `session-check.sh` before it reads anything. Local file work only, no network.

1. Detect: a root `state.md` with `schema_version: 1` and no `cockpit.md`. Anything else: do nothing. A `schema_version` above 2: print `state: written by a newer cockpit, left untouched` and stop.
2. Lock: an exclusive `flock` on the file `~/.cockpit/.migrating`, held for the whole run. The system releases it when the process dies, so an interrupted run never blocks the next one. A session that does not get the lock within 3 seconds reports `migration: failed (another session is migrating the saved setup)` and works on v1.
3. Back up every text file of the root to `backups/v1-<timestamp>/`. Folders that can be rebuilt (`repo/`, the two linked folders) are not copied.
4. Build `projects/<slug>/`: split `state.md` into the user part and the app part, import the memory files (section 6), and rename `repo/`, `saas-project/`, `tools-project/`, `secrets/` into it. Renames stay on one filesystem, so they are atomic and keep file modes.
5. Write `cockpit.md` with `schema_version: 2`, through a temporary file and a rename. This is the commit point.
6. Remove the old root files, which are in the backup, and the lock.

Rules:

- Rerunning at any point is safe: before the commit point it starts again and skips what is done, after it only finishes the cleanup.
- An error, or a stop signal, before the commit point undoes the renames and leaves v1 as it was. Nothing is ever undone after the commit point. The hook prints `migration: failed (<reason>)`, and `project directory` is `~/.cockpit` itself. Every `$PROJECT/...` path then resolves to the v1 location, so the session works as before. `memory.sh` reads the v1 files in place as imported text and appends new entries to them. Claude tells the user once, in one sentence, and writes the reason to `proposals.md`.
- On success the hook prints `state: updated to version 2`, once: a later run that only finishes the cleanup prints nothing. A root file changed after its backup is moved into the backup folder instead of being removed. Claude says so in one sentence and adds a journal line.
- Railway keeps its folder links in its own config, keyed by absolute path (checked on this machine: `~/.railway/config.json`, `projects` keyed by path). Moved folders lose their link. The migration leaves a `.relink` marker in the project directory, the hook prints `railway links: to refresh`, and `scripts/relink.sh --project <slug>` runs `railway link -p -e -s` with the ids of `state.md`, then removes the marker. Claude runs it before the first Railway command. A failure is the existing repair path.

The prose migration section of `state-schema.md` is replaced by a pointer to the script.

## 6. Memory

Same idea as today, local markdown files, with three changes: entries instead of free text, a script for every read and write, and two new topics.

Topics per app: `domain`, `schema`, `codebase`, `tools`, `incidents` (symptom, cause, fix), `decisions` (what was chosen and why). One topic for the user: `preferences`.

One entry:

```
- [m-20261009-03] 2026-10-09 | high | active customer, billing, churn
  An active customer is an account with a paid invoice in the last 30 days.
```

`scripts/memory.sh`, with `--project <slug>`:

| Command | Effect |
|---|---|
| `recall "<words>" [--topic t] [--limit 5]` | entries ranked by number of matching words in keywords and text, then importance, then date |
| `store --topic t --importance i --keywords a,b --text "..."` | appends an entry, prints its id, adds the journal line |
| `update <id> --text "..."` | replaces the text, keeps the id, updates the date |
| `forget <id>` | removes the entry, adds the journal line |
| `health` | entries per topic, topics over 100 entries, text still waiting in an imported block |

- `store` and `update` refuse a text that holds a connection string or a token shape, with a message saying why. The rules on sources and on personal data stay in `memory.md`, guarded by the existing evals.
- The skill recalls with the words of the request before exploring anything, instead of reading whole files. `/cockpit:review-session` stores through the script.
- No decay and no automatic consolidation: nothing is dropped unless Claude or the user asks.

Migration of v1 memory: each old file moves untouched under a `## Imported` heading of the matching topic file. `recall` searches imported text by paragraph, with a lower rank than entries. When Claude uses an imported paragraph and the user confirms it, it is stored as an entry and removed from the block. Nothing is rewritten by a rule that could mangle it.

## 7. Welcome briefing

When a session opens on the command, a greeting or no request at all, Claude answers with a fixed shape, in the user's language, built only from lines of the session context:

1. One line: welcome to the cockpit, with the user's first name (`user:` line, from `cockpit.md`).
2. What changed since last time, only if something did: the state update, and what is new in the plugin (the existing `plugin version changed` rule).
3. One line per app: fine, or the one thing that needs attention.
4. One AskUserQuestion: which app (only with several), and what to do today, with 3 or 4 suggestions drawn from that app's profile, tools and journal.

When the first message is a real request, Claude answers it. With several apps it asks which one first, unless the request names it. Lines 2 and 3 shrink to one sentence after the answer.

## 8. Onboarding with several apps

- User steps run once: language, name and email, dependencies, settings, GitHub sign-in.
- App steps run per app: usages, tools wanted, developer, plan, Railway project, backups, repository access and clone, tools, discovery, check.
- `/cockpit:onboard` on a complete setup offers "add another app" next to "add a usage or a tool". A new app starts at the first app step.
- The spending alert is set on the Railway workspace: a second app finds it and moves on, as the step already says.
- `status`, `undo`, `repair` and removal work on the active app. Removal names every app before asking.

## 9. Tests

Script tests, on the v1 fixture:

- migration: the resulting tree, the split of `state.md`, file modes of `secrets/`, the backup;
- rerun after success, rerun after an interruption at each step, failure before the commit point leaves v1 byte for byte;
- newer schema left untouched;
- session context for: no state, v1 migrated, one app, several apps without record, several apps with record, legacy mode;
- `project.sh use` and `--project` resolution, including the error with several apps;
- `memory.sh`: ranking of `recall`, `store` then `recall`, `update`, `forget`, refusal of a secret, search in an imported block;
- `relink.sh` with a fake `railway`.

Evals: the 11 existing ones unchanged, plus `two-apps-asks-which`, `request-names-the-other-app`, `welcome-briefing`, `memory-is-recalled-not-reread`.

Checked on 2026-10-09 by a real run, to record in `docs/verified-facts.md`:

- Two directories linked to two different Railway projects coexist (seen in `~/.railway/config.json`, CLI 4.68). To run once more on the 5.x CLI the plugin installs.
- A SessionStart hook receives `session_id`, `transcript_path`, `cwd`, `hook_event_name` and `source` on stdin (`source: startup` in the CLI), and `CLAUDE_ENV_FILE` is set.

Still to verify by a real run before step 4 relies on it: that the hook runs again with the same `session_id` after a compaction and after a resume. The design does not depend on the `cwd` the hook gets in Claude Desktop.

## 10. Build order

Each step ships on its own and leaves a v1 install working.

1. `$PROJECT` in the reference files and `--project` in the scripts, on the v1 layout. No change in behaviour.
2. Migration, layout v2, legacy mode, relink.
3. Memory script and the two new topics.
4. Several apps: session records, `project.sh`, `/cockpit:switch`, onboarding of a second app.
5. Welcome briefing.

## 11. Not in this lot

- Discovery instead of assumptions, its own spec after this one: onboarding asks where the app runs and what the team already uses, scans what exists (tools, accounts, who owns what), and proposes only what is missing. Railway becomes one provider among others: the `provider` field of each app is where that starts.
- The landing page: its own repository.
- Recall injected by a hook on every message, a shared tool for several apps, different accounts per app.

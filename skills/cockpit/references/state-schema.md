# State schema

Current `schema_version`: 2.

Everything lives in `~/.cockpit/`. Only Claude writes there. No personal data of end users, no secret.

## Layout

```
~/.cockpit/
  cockpit.md                 the user: schema_version, language, plugin_version, dependencies, name, email
  memory/preferences.md      how this user wants answers
  proposals.md               changes wanted in the plugin
  projects/<slug>/           one app, written $PROJECT in the references
    state.md                 onboarding status, profile, plan, SaaS project, code, tools project, tools, open escalations
    memory/                  domain.md, schema.md, codebase.md, tools.md
    journal.md  handoff.md  report.txt
    saas-project/  tools-project/  repo/  secrets/
  backups/v1-<timestamp>/    text files of the previous layout, kept by the migration
```

- `<slug>`: the Railway project name in lowercase, reduced to `a-z`, `0-9` and `-`. `app` when no Railway project is known yet, which is the case for a Mac that starts with no saved setup. It never changes afterwards: the display name stays in `state.md`.
- `$PROJECT` is the `project directory:` line of the session context.

## cockpit.md

The header is read by a script at every session start. Keep it exactly in this shape: flat keys, one per line, no quotes, no nesting.

```
---
schema_version: 2
language: fr
plugin_version: 1.6.0
dependencies: git, railway, gh
---

## User
- Name: <name>
- Email: <email>
```

- `schema_version`: lives here only.
- `language`: language code of the user.
- `plugin_version`: the plugin version the user was last told about, from the session context. Written at the end of onboarding and after each "what is new".
- `dependencies`: command names of the plan, comma separated: `git`, `railway`, `gh`, `node`.
- `User`: the name and the email the user signs changes with. A line that could not be split into a name and an email by the migration stays as `- User: <text>`.

## state.md of an app

Same rules for the header: flat keys, one per line.

```
---
provider: railway
onboarding: in-progress
onboarding_step: github
---
```

- `provider`: `railway`, the only value today. Nothing reads it yet.
- `onboarding`: `in-progress` or `complete`.
- `onboarding_step`: the next step to run, not the last one finished, one of `profile`, `plan`, `dependencies`, `railway`, `backups`, `settings`, `github`, `tools`, `discovery`, `check`.

The body below the header uses these sections, in this order. Leave a section empty until it is known. A tool line without `project` means `tools`.

```
## Profile
- Usages: tools, app changes, health, diagnosis
- Tools wanted: metabase (reads app data), n8n
- Developer: <name>, <github handle or email>, channel: github | email | none

## Plan
- <step>: done | pending | failed twice (<date>, <reason>)

## Dependencies
- railway 5.64.1
- gh 2.102.0

## SaaS project
- Project: <name> (<id>)
- Production environment: <name>
- App service: <name>, repository <owner/repo>, deployed branch <branch>
- Postgres service: <name>
- Test environment: <name>, branch <branch>, URL <url> | none
- Backups: schedule <daily, weekly>, first backup <date>
- Spending alert: <amount> USD per month | none

## Code
- Merge policy: ask-me | developer-reviews

## Tools project
- Project: <name> (<id>)

## Tools
- <tool>: project <tools | app>, template <code>, services <names>, URL <url>, driven by <mcp | api | user>, app data <connected | none>

## Open escalations
- <date>: <subject>, <link>
```

The clone of the app is always `$PROJECT/repo`, so no line records it.

## Other files

| File | Content | Language |
|---|---|---|
| `$PROJECT/memory/domain.md` | Business terms mapped to tables, columns, statuses, rules | user's |
| `$PROJECT/memory/schema.md` | What each table is for, traps, sensitive tables | user's |
| `$PROJECT/memory/codebase.md` | Stack, where things live, conventions, files that always need a developer | user's |
| `$PROJECT/memory/tools.md` | What was built in each tool, for which question | user's |
| `~/.cockpit/memory/preferences.md` | Answer format, figures followed, habits | user's |
| `$PROJECT/journal.md` | One dated line per change, merge, escalation, memory write, a change that can be reversed ends with `undo:` and the way back | user's |
| `~/.cockpit/proposals.md` | Changes wanted in the plugin: date, what happened, what should change, why | English |

A memory file can start with a `## Imported` section: text carried over untouched from the previous layout.

Managed by the scripts and by onboarding, never edited by hand: the directories `saas-project/` (linked to the SaaS project, for reading), `tools-project/` (linked to the tools project), `repo/` (clone of the app) and `secrets/` (API keys of tools, mode 600) of the app, its file `report.txt`, and `backups/`. `handoff.md` holds the last hand-off, written by `escalation.md` and overwritten each time. `.relink` in the app folder is a marker left by the migration: the Railway links of its folders are to refresh (`relink.sh`).

## Version 1 layout (legacy mode)

Before version 2 everything sat flat in `~/.cockpit/`, for one app. The session check migrates it by itself. While it has not (`active project: legacy` in the session context), `$PROJECT` is `~/.cockpit/` itself and the paths of this file map like this:

| Version 2 | Version 1 |
|---|---|
| `cockpit.md` (settings, name, email) | the header and the `Profile` section of `state.md` |
| `$PROJECT/state.md` | `~/.cockpit/state.md` |
| `$PROJECT/memory/<topic>.md` | `~/.cockpit/<topic>.md` |
| `~/.cockpit/memory/preferences.md` | `~/.cockpit/preferences.md` |
| every other `$PROJECT/...` path | the same name in `~/.cockpit/` |

The version 1 header of `state.md` holds `schema_version: 1`, `language`, `onboarding`, `onboarding_step`, `plugin_version` and `dependencies`, and its `Profile` section has a `User: <name>, <email>` line and the `Code` section a `Clone: ~/.cockpit/repo` line.

## Migration

`scripts/migrate-state.sh` moves a version 1 setup to version 2. The session check runs it before reading anything, so Claude never runs it: the session context reports the result and `SKILL.md` says what to do with each line. A change to this layout bumps `schema_version` above and extends `scripts/migrate_state.py` in the same commit.

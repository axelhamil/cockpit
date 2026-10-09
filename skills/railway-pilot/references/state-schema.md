# State schema

Current `schema_version`: 1.

Everything lives in `~/.railway-pilot/`. Only Claude writes there. No personal data of end users, no secret.

## state.md

The header is read by a script at every session start. Keep it exactly in this shape: flat keys, one per line, no quotes, no nesting.

```
---
schema_version: 1
language: fr
onboarding: in-progress
onboarding_step: github
plugin_version: 1.3.0
dependencies: git, railway, gh
---
```

- `language`: language code of the user.
- `onboarding`: `in-progress` or `complete`.
- `onboarding_step`: the next step to run, not the last one finished, one of `profile`, `plan`, `dependencies`, `railway`, `backups`, `settings`, `github`, `tools`, `discovery`, `check`.
- `plugin_version`: the plugin version the user was last told about, from the session context. Written at the end of onboarding and after each "what is new", on its own line after `onboarding_step`.
- `dependencies`: command names of the plan, comma separated: `git`, `railway`, `gh`, `node`.

The body below the header uses these sections, in this order. Leave a section empty until it is known. A tool line without `project` means `tools`.

```
## Profile
- Usages: tools, app changes, health, diagnosis
- Tools wanted: metabase (reads app data), n8n
- User: <name>, <email>
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
- Clone: ~/.railway-pilot/repo

## Tools project
- Project: <name> (<id>)

## Tools
- <tool>: project <tools | app>, template <code>, services <names>, URL <url>, driven by <mcp | api | user>, app data <connected | none>

## Open escalations
- <date>: <subject>, <link>
```

## Other files

| File | Content | Language |
|---|---|---|
| `domain.md` | Business terms mapped to tables, columns, statuses, rules | user's |
| `schema.md` | What each table is for, traps, sensitive tables | user's |
| `codebase.md` | Stack, where things live, conventions, files that always need a developer | user's |
| `tools.md` | What was built in each tool, for which question | user's |
| `preferences.md` | Answer format, figures followed, habits | user's |
| `journal.md` | One dated line per change, merge, escalation, memory write, a change that can be reversed ends with `undo:` and the way back | user's |
| `proposals.md` | Changes wanted in the plugin: date, what happened, what should change, why | English |

Managed by the scripts and by onboarding, never edited by hand: the directories `saas-project/` (linked to the SaaS project, for reading), `tools-project/` (linked to the tools project), `repo/` (clone of the app), `secrets/` (API keys of tools, mode 600), and the file `report.txt`.

## Migration

When `schema_version` in `state.md` is lower than the current version above, apply each step below in order, then set the new version and add a dated line to `journal.md`. Tell the user in one sentence that the saved setup was updated.

No migration exists yet: version 1 is the first.

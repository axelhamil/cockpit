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
dependencies: git, railway, gh
---
```

- `language`: language code of the user.
- `onboarding`: `in-progress` or `complete`.
- `onboarding_step`: the next step to run, not the last one finished, one of `profile`, `plan`, `dependencies`, `railway`, `backups`, `protection`, `github`, `tools`, `discovery`, `check`.
- `dependencies`: command names of the plan, comma separated: `git`, `railway`, `gh`, `node`.

The body below the header uses these sections, in this order. Leave a section empty until it is known.

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

## Code
- Merge policy: claude-judges | developer-always
- Clone: ~/.railway-pilot/repo

## Tools project
- Project: <name> (<id>)

## Tools
- <tool>: template <code>, services <names>, URL <url>, driven by <mcp | api | user>, database role <tool>_read | none

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
| `journal.md` | One dated line per change, merge, role, escalation, memory write | user's |
| `proposals.md` | Changes wanted in the plugin: date, what happened, what should change, why | English |

Managed by the scripts and by onboarding, never edited by hand: the directories `saas-project/` (linked to the SaaS project, for reading), `tools-project/` (linked to the tools project), `repo/` (clone of the app), `secrets/` (API keys of tools, mode 600), and the files `guard.conf` and `report.txt`.

## Migration

When `schema_version` in `state.md` is lower than the current version above, apply each step below in order, then set the new version and add a dated line to `journal.md`. Tell the user in one sentence that the saved setup was updated.

No migration exists yet: version 1 is the first.

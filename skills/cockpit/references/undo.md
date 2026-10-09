# Undo

"Cancel that", "go back", "it was better before". The user does not say how: find what was done and reverse it.

## Find what to undo

1. In this conversation: the last thing you changed.
2. Otherwise `~/.cockpit/journal.md`, newest line first. Each line that changed something ends with `undo:` and the way back.
3. More than one candidate: AskUserQuestion with the last 3 changes in plain words, newest first.

Undoing is ordinary work: do it, then say what is back to how it was. The exception is an undo that destroys something (the last two rows of the table, marked "ask once").

## How

| What was done | Way back |
|---|---|
| A change to the app, merged | `gh pr revert <number> --repo <owner>/<repo>`, wait for checks, `gh pr merge <revert number> --squash --delete-branch`, follow the deployment as in `code-changes.md` |
| A change to the app, not merged yet | `gh pr close <number> --delete-branch` |
| A deployment that broke the app | It came from a merged change: revert that pull request, as above. Otherwise the Railway CLI cannot go back to an older deployment: `railway open -p` gives the project page, open it in the Browser pane, go to the service, its Deployments, and use Rollback on the last one that worked (`railway deployment list -s <service> --json` tells which). `railway redeploy -s <service> -y` only restarts the current one |
| A setting (variable) changed | Set the previous value again with `railway variable set`. A secret is never in the journal: the user pastes the old value to the clipboard, then `pbpaste \| railway variable set <KEY> --stdin -s <service>` |
| A tool connected to the app's data | Remove the database from the tool's admin screen |
| A dashboard, question or workflow built in a tool | Archive it in the tool (not delete), through its MCP server or its screen |
| A backup schedule changed | `railway postgres pitr schedule set` with the previous choice |
| A fact saved in memory | Remove or correct it in the state file |
| A tool deployed (ask once: its content is lost) | `railway service delete -s <service> -y` for each of its services, from the project its line in `state.md` names |
| Data changed or deleted in the database (ask once: everything since the backup is lost) | Restore the backup made before the change: `escalation.md` first unless they insist |

## What cannot be undone

Say it plainly, in one sentence, and what can still be done:

- A deleted service, database or volume without a backup.
- An email, message or API call already sent by a workflow.
- Data a user of the app entered between a change and its undo.

## Journal lines

Every line you write in `journal.md` for a change carries its way back, so the next session can undo it:

```
- 2026-10-09: changed the signup button label (pull request 42), undo: gh pr revert 42
- 2026-10-09: deployed metabase in the tools project, undo: delete services metabase and metabase-db (content lost)
- 2026-10-09: set SUPPORT_EMAIL on web (was help@example.com), undo: set it back
```

Previous values of secrets are never written. A line without `undo:` has no recorded way back: work it out from the table.

After an undo, add a line too: what was undone and why, in their words when they said it.

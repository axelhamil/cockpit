# Status

"How is my app?", "is everything fine?", a morning check, or a `health: PROBLEM` line in the session context.

## Collect

Run everything from `~/.railway-pilot/saas-project/`, in one go, then answer. Services, environment and URL are in `state.md`.

| Question | Command |
|---|---|
| Is each service running | `railway status --json`: `latestDeployment.status` of each service in the production environment |
| Does the app answer | `curl -s -o /dev/null -w '%{http_code} %{time_total}' https://<app domain>` |
| Errors since yesterday | `railway logs -s <app service> --since 24h --filter "@level:error" --json` and `railway logs -s <app service> --since 24h --http --status 500 --json` |
| Load | `railway metrics --all --since 24h --json` |
| Cost | `railway usage --json` and `railway usage --period previous --json` |
| Backups | `railway postgres pitr backup list -s <postgres service> --json` and `railway postgres pitr schedule list -s <postgres service> --json` |
| Waiting changes | `gh pr list --label via-claude --repo <owner>/<repo>` and the `Open escalations` of `state.md` |
| Tools | same `railway status --json` from `~/.railway-pilot/tools-project/` |

A command that fails is reported as "not checked", never as fine.

## Answer

One screen, in their language, in this order. One line each, a figure when there is one, no command and no service jargon.

1. **Verdict**: all good, or the one thing that needs attention.
2. **App**: online or not, response time.
3. **Errors**: how many since yesterday and the most frequent one in plain words, or none.
4. **Cost**: this month so far, against last month's total and against the spending alert of `state.md`. No `Spending alert` line at all in `state.md` (not `none`, which means they declined): offer one (`onboarding.md`, step 5).
5. **Backups**: date of the last one, the schedule.
6. **Tools**: each tool, online or not.
7. **Waiting**: changes not yet live, hand-offs without an answer.

Then, only when something needs attention: what you would do about it, in one sentence, and do it if they say yes. Group errors by message before counting: 400 lines of the same error is one problem.

## At the start of a session

The session context carries `health:` lines from a quick check of the deployments.

- `health: PROBLEM ...`: tell the user in one sentence with your first answer, in their words ("the app stopped after the last update"), and offer to look into it. Look at the logs of that service before saying why.
- `health: not checked ...`: say nothing unless the request needs Railway. Then follow `repair.md`.
- No `health:` line: nothing is failing, say nothing.

# Repair and removal

## Repair

Something stopped working, a `health: not checked` line, a missing dependency, or the user asks to check the setup. Check everything in one pass, fix what is broken without asking, then report in two lines: what was broken, what works again.

| Check | Broken when | Fix |
|---|---|---|
| `railway whoami` | error or "Unauthorized" | `railway login` (tell the user first: a browser tab opens, they approve), in the background |
| `railway status --json` in `$PROJECT/saas-project/` | no linked project | `railway link -p <project id> -e <environment>` with the values of `state.md` |
| Same in `$PROJECT/tools-project/`, when a tool is recorded as `project tools` | no linked project | same, with the tools project |
| `railway links: to refresh` in the session context | the folders moved with the saved setup and the session start could not link them again | fix the `railway whoami` row and check that the account is a member of the project, then `sh $SCRIPTS/relink.sh --project <slug>`, with the slug of the `active project:` line. It links both folders. If it says an id, an environment or a service cannot be read from `state.md`, the sign-in rows do not help: link the folder again with the Railway step of `references/onboarding.md`, which records the ids, then run `relink.sh` again |
| `gh auth status --hostname github.com`, when GitHub is in the plan | not logged in | `onboarding.md`, GitHub step |
| `git -C $PROJECT/repo status` | no clone, or not a repository | `gh repo clone <owner>/<repo> $PROJECT/repo` |
| Dependencies of the session context | `missing` | `dependencies.md` |
| The Railway CLI is older than 5.44 (`railway --version`) | commands unknown | install command of `dependencies.md` |
| Permission pop-ups are back | settings were reset | `sh $SCRIPTS/apply-settings.sh --marketplace cockpit --repo <owner>/cockpit` |
| A tool's MCP server does not list its tools | sign-in expired | the user types `/mcp`, picks the tool and approves |
| `state.md` unreadable or half written | onboarding status unknown | rebuild it from what Railway and GitHub answer, keep the other state files, then `onboarding.md` for what is missing |

Two failures on the same line: `escalation.md`.

## Removal

The user wants to stop using cockpit on this Mac. Say first, in two sentences, what stays and what goes:

- **Stays**: the app, the tools deployed on Railway (they keep running and keep costing), the pull requests, the backups. Nothing online is touched.
- **Goes**: the saved setup and memory on this Mac, the sign-ins, the plugin.

One AskUserQuestion (this is not reversible), two questions: keep a copy of the memory on the Desktop or not, and leave the tools running on Railway or delete them too (their content is lost). Tools to delete: `tools.md`, removing a tool, before anything else. Then:

1. Copy asked: `cp -R ~/.cockpit ~/Desktop/cockpit-memory && find ~/Desktop/cockpit-memory \( -name secrets -o -name repo \) -type d -prune -exec rm -rf {} +`.
2. `sh $SCRIPTS/apply-settings.sh --remove --marketplace cockpit`.
3. `claude mcp remove <name> --scope user` for each tool driven by MCP in `state.md`.
4. `gh auth logout --hostname github.com` and `railway logout`.
5. `mv ~/.cockpit ~/.Trash/cockpit-$(date +%Y%m%d%H%M%S)`.
6. `claude plugin uninstall cockpit@cockpit` then `claude plugin marketplace remove cockpit`. Last, because the scripts live in the plugin.

Tell them it is done, and which tools are still running on Railway.

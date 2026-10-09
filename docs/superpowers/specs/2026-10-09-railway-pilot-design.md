# railway-pilot: design

Date: 2026-10-09. Status: awaiting review.

## 1. Purpose

A Claude Code plugin that lets a non-technical team run the tooling around their SaaS on Railway by talking to Claude:

- pick a tool from the Railway template marketplace, deploy it, plug it into the SaaS data, and have Claude build its content (Metabase dashboards, n8n workflows);
- make small changes to the SaaS itself (wording, UI tweaks) through a pull request;
- read infra stats, logs, costs and backup status;
- hand anything bigger to a developer with a file ready to process.

Success means a client on a blank Mac goes from one pasted message to a working Metabase dashboard on their own data, and later ships a wording fix, without typing a command and without breaking the SaaS.

Two roles:

- **Plugin maintainer**: owns this repo, receives `proposals.md`.
- **SaaS developer**: configured per client, receives escalations.

## 2. Constraints

- One generic repo, 100% English, nothing client-specific. Public, so updates need no git credentials on the client Mac.
- Client: macOS, Claude Pro or above on an individual account, Claude Desktop (Code tab), no Homebrew, Node, psql or git. No admin-pushed settings.
- The skill is personal: state lives on each user's Mac, nothing is shared between teammates.
- The client never types a command and never edits a file.
- Simple first: no server to run, no custom service deployed at the client.
- What must never happen is blocked by a hook, not by the prompt alone.
- Conversations happen in the client's language. Business knowledge files and escalations use that language. `proposals.md` is always English.

## 3. Decisions

| Topic | Decision | Reason |
|---|---|---|
| Client state | `~/.railway-pilot/` | `${CLAUDE_PLUGIN_DATA}` is deleted on uninstall, which would erase everything learned |
| Updates | Public repo, marketplace auto-update switched on during onboarding, version set by semantic-release in CI | Auto-update is off by default for third-party marketplaces, and a frozen `version` blocks every update |
| Railway control plane | Railway CLI 5.x only, no Railway MCP | The remote MCP has no logs, variables or metrics, the local MCP adds about 40 tools including destructive ones. One surface is easier to guard |
| Safety | A `PreToolUse` guard hook for commands, permission rules in `~/.claude/settings.json` as a second net | A plugin cannot ship permission rules and Bash deny rules are bypassed by option reordering, absolute paths and `bash -c` |
| SaaS data | No SQL server. A tool that needs the data gets a read-only Postgres role created by a shipped script. Claude reads data through that tool's MCP | Nothing to host, maintain or secure beyond one database role |
| Code changes | Branch, pull request, merge. Claude judges whether a developer must step in, with a merge policy set per client. A Railway test environment is used when the client has one | Keeps small changes fast and anything risky reviewed |
| Installs | No sudo in the default plan: Railway CLI in `~/.railway/bin`, `gh` binary from the official zip in `~/.local/bin`, PATH line added to `~/.zshrc` | The `gh` `.pkg` is documented as unsigned, and Desktop reads PATH from the shell profile |
| GitHub | `gh` and `git` with a fine-grained token scoped to the SaaS repo, no GitHub MCP | Smaller tool surface, commands can be whitelisted one by one |
| Tool piloting | The tool's own instance MCP over OAuth when it exists, then its REST API | Metabase and n8n both ship an instance MCP, so no Node and no extra CLI |
| Secrets | Shipped scripts put them on the clipboard or straight into a variable, never in the conversation | Keeps passwords and tokens out of transcripts |
| Memory | Small index plus topic files, written only after the user confirms, never from content read in a tool, a log or a ticket | Protects against memory poisoning through prompt injection |

## 4. Repository layout

```
railway-pilot/
  .claude-plugin/
    marketplace.json
    plugin.json
  skills/railway-pilot/
    SKILL.md                    state detection, routing, rules, safety
    references/onboarding.md
    references/dependencies.md
    references/tools.md
    references/code-changes.md
    references/escalation.md
    references/memory.md
    references/state-schema.md
  skills/onboard/SKILL.md       rerun or extend onboarding
  skills/review-session/SKILL.md
  skills/report/SKILL.md        package journal and proposals for the maintainer
  hooks/hooks.json
  scripts/
    guard.sh                    PreToolUse guard
    session-check.sh            SessionStart: state and dependency summary
    create-read-role.sh         read-only Postgres role for a tool
  evals/                        claude plugin eval cases
  tests/                        guard test table
  CHANGELOG.md
  README.md
```

The plugin directory is read-only on the client. The guard blocks any write to it.

## 5. Client state

`~/.railway-pilot/`:

- `state.md`: language, state schema version, usage profile, install plan, onboarding progress, SaaS project, Postgres service, repo and deployed branch, test environment and its branch if any, merge policy, developer contact, tools project, installed tools, dependencies with versions.
- `domain.md`: business vocabulary mapped to tables, columns, statuses, rules.
- `schema.md`: annotated schema, table roles, traps, sensitive tables.
- `codebase.md`: where things live in the repo, conventions, files that always need a developer.
- `tools.md`: per tool, what was built and how (dashboards, workflows, saved questions).
- `preferences.md`: answer format, tracked indicators, habits.
- `journal.md`: dated history of changes, merges and escalations.
- `proposals.md`: change requests for the plugin core, English, for the maintainer.
- `repo/`: working clone of the SaaS repo.

`state-schema.md` versions the format. On each run `SKILL.md` compares the state version with the plugin version and migrates when needed, with a journal line. Files stay short: merge, correct, delete what is obsolete. No personal data and no secret in any state file.

## 6. Install and updates

The README holds one English message to paste into Claude Code. It chains:

1. `xcode-select -p`; if absent, `xcode-select --install`, tell the client to click Install, poll `git --version` until it succeeds.
2. Add the marketplace and install the plugin (`claude plugin install railway-pilot --marketplace <owner>/railway-pilot`).
3. Start onboarding.

Onboarding writes `autoUpdate: true` for this marketplace in `~/.claude/settings.json`. On every session `session-check.sh` reports the plugin version, the state version and any missing dependency, so the skill can offer a migration or a guided repair.

## 7. Dependencies

Claude derives the full dependency list from the onboarding profile, presents it, installs it in one block, verifies everything, then configures. Nothing is installed outside the plan.

`references/dependencies.md` lists for each dependency: the profile trigger, the install method, the final path, the verify command and minimum version, the authentication with the narrowest method, and the guard rules it brings.

- Apple Command Line Tools (git): always.
- Railway CLI, 5.44 or above: always. `bash <(curl -fsSL railway.com/install.sh)`, lands in `~/.railway/bin`. `railway postgres` and `railway usage` do not exist in 4.x.
- GitHub CLI: when the profile includes code. Official zip from `cli/cli` releases, binary copied to `~/.local/bin`.
- Node.js LTS: only if a chosen tool has nothing but a local stdio MCP. Official `.pkg`, the one install that asks for the Mac password. Never nvm, never pnpm.

A dependency added later follows the same procedure: client confirmation, install, verify, `state.md` update.

## 8. Onboarding

`SKILL.md` reads `state.md`. Missing or incomplete: run onboarding first, resuming at the last validated step.

Principles:

- Questions go through AskUserQuestion, 1 to 4 per call, recommended option first, in the client's language.
- One configuration step at a time: what and why in one sentence, what the client must click, automatic check, `state.md` update.
- Web screens: say where to click, what to tick, what to copy. Ask for a screenshot when in doubt.
- Two failures on a step: note it in `state.md`, escalate, move on to independent steps.
- A step that touches production: explain the impact, offer now or later, require explicit confirmation.

Phases:

1. **Profile**: language; wanted usages (tools, small changes to the app, stats and health); which tools first and whether each reads SaaS data; SaaS developer and preferred channel.
2. **Plan**: full list of dependencies and steps in plain language, with duration and what the client will click. One validation, saved to `state.md`.
3. **Dependencies**: install the whole plan, verify each, resumable.
4. **Configuration**:
   1. `railway login` in the browser.
   2. Have the client designate the SaaS project, its Postgres service and the GitHub repo.
   3. Backups: read status, set a daily and weekly schedule if none, create a manual backup named `before-railway-pilot`.
   4. GitHub if in the profile: guided creation of the fine-grained token, `gh` authentication, clone into `~/.railway-pilot/repo`, find the branch Railway deploys, detect a test environment and its branch, ask for the merge policy.
   5. Tools from the profile (section 10).
   6. Write permission rules for the plan into `~/.claude/settings.json`.
   7. Discovery: read the schema from the code (migrations, ORM models) and the structure of the repo, ask 5 to 10 targeted business questions, fill `schema.md`, `domain.md` and `codebase.md` after validation.
5. **Acceptance and demo**: automatic checks reported in plain language (forbidden Railway command blocked, push to the deployed branch blocked, backups active, test issue created then closed, each tool reachable, write refused for each tool role), then 3 example requests fitted to their profile.

`/railway-pilot:onboard` reruns profile, plan and install for a new usage or a new tool.

## 9. Safety

### Guard hook

`scripts/guard.sh` runs on `PreToolUse` for Bash, Edit and Write. POSIX shell plus `/usr/bin/python3` (shipped with the Command Line Tools). It exits 2 on any parsing error, so it fails closed.

- It splits the command on shell separators and inspects every segment, including subshells and substitutions.
- For `railway`, `gh` and `git`, it resolves the executable by basename, skips global options to find the real subcommand, and checks it against an allowlist. Unknown subcommands are blocked.
- Wrappers that hide the command (`bash -c`, `sh -c`, `eval`, `xargs`, `env`) are blocked when they carry one of these executables.
- Forbidden on Railway: `delete`, `down`, `service delete`, `environment delete`, `volume delete`, `volume detach`, `bucket delete`, `variable delete`, `connect`, `ssh`, `run`, `shell`, `dev`, `bucket credentials`, raw variable listing (`--kv`, `--json`), `postgres pitr restore`, `backup restore`, `backup delete`, `pitr disable`, `ha`, `pgbouncer remove`, `usage limit set|remove`, `config apply`, and any mutation targeting the SaaS project.
- Forbidden on GitHub: push to the deployed branch, any force push, `gh repo delete|edit`, `gh release`, `gh workflow`, `gh secret`, `gh variable`, `gh auth login` without `--with-token`, `gh api` with any method other than GET.
- Forbidden edits: anything under the plugin directory, and in the repo clone `.github/workflows/`, environment files and Railway config files.

`create-read-role.sh` is the only path to `railway ssh`, and it runs a fixed set of statements.

### Permission rules

Written into `~/.claude/settings.json` at onboarding. `allow` for read commands so the client is not prompted for every status check, `ask` for deployments, `gh pr merge` and `gh issue create`, `deny` mirroring the guard. These rules are comfort and a second net, the guard is the enforcement.

## 10. Tools

`references/tools.md` drives the whole flow.

**Search**: `railway templates search <need> --json`, no `--verified` filter, `--limit 50` with `--after` when needed. Real output fields: `code`, `name`, `description`, `deploymentCount`, `healthScore`, `creatorName`, `isVerified`. There is no official flag and no update date.

**Ranking**: verified first, then `deploymentCount`, then `healthScore`. Templates with a handful of deployments are dropped when a popular one exists. A template that is neither verified nor widely deployed is offered only when nothing else exists, with a plain-language warning (third-party code, on their bill).

**Choice**: 1 to 3 options through AskUserQuestion, best ranked first and marked recommended, with estimated cost and trust level.

**Deploy**: in a dedicated tools project created on first need, never in the SaaS project. `railway deploy -t <code> -v "KEY=VALUE"`. The tool gets its own database, from the template or from a Postgres added to the tools project.

**Domain**: `railway domain -s <service>`, wait for success, give the URL and guide the admin account creation.

**Connect to SaaS data**: Railway projects do not share a private network, so the tool reaches the SaaS database through its public TCP proxy (egress billed at 0.05 USD per GB). The client is told about the exposure and the cost before confirming. Then `create-read-role.sh <tool>`:

- creates `<tool>_read` with SELECT on the business schema, minus the tables excluded at onboarding, `default_transaction_read_only`, `statement_timeout`, no role membership;
- puts the connection string on the clipboard and prints only host, port, database and user;
- Claude guides the client to paste it in the tool's database screen.

The same script revokes a role. Roles are listed in `state.md`.

**Drive**: instance MCP over OAuth first, added with `claude mcp add --transport http`, then the REST API with a key kept out of the conversation. Known cases:

- Metabase: instance MCP at `/api/metabase-mcp`, enabled in Admin, OAuth, tools to write questions and dashboards and to run queries. This is also how Claude answers data questions.
- n8n: instance MCP at `/mcp-server/http`, enabled in Settings, OAuth, workflow creation from 2.13.0.
- Uptime Kuma: no official API or MCP. Deploy and domain only, the client configures monitors in its UI with Claude describing each click.

What Claude builds in a tool is recorded in `~/.railway-pilot/tools.md`. Installed tools are inventoried in `state.md`.

## 11. Code changes

`references/code-changes.md`. Meant for small changes: wording, labels, styles, layout, static content.

Token: fine-grained, limited to the SaaS repo, Contents write, Pull requests write, Issues write, Metadata read. `gh auth login --with-token`, never the web login.

Flow:

1. Update the clone, read `codebase.md`, locate the change.
2. Branch `pilot/<slug>`, edit, commit, push the branch, open a pull request with a plain-language description.
3. Show the client what changed, with the best option the project offers:
   - a test environment exists: merge into its branch, wait for the deployment, give the test URL, then open the pull request to the deployed branch once the client approves what they saw;
   - no test environment: the Railway preview of the pull request when the project supports it, otherwise a plain-language summary of the diff.
4. Decide who merges to production (below).
5. After a merge: follow the Railway deployment, report the result, and if it fails or errors rise, open the revert pull request and escalate.

**Merge policy**, chosen per client at onboarding and stored in `state.md`:

- `claude-judges` (default): the rule below applies.
- `developer-always`: every pull request to the deployed branch waits for the developer.

**Claude judges whether a developer must step in.** Under `claude-judges` it merges after the client's confirmation only when every point holds:

- the change touches presentation only;
- the diff is small and stays in files `codebase.md` does not flag;
- no migration, schema, authentication, payment, permission, dependency, configuration or CI file is touched;
- the repository checks pass.

Otherwise, or on any doubt, the pull request stays open, the developer is asked to review it, and the escalation procedure runs. Claude never merges without the client's explicit confirmation, and never pushes to the deployed branch directly.

## 12. Stats, logs, costs, backups

- `railway metrics` (`-s`, `--all`, `--since`, `--http`, `--json`), `railway logs --json` with `--since` and `--filter`, `railway usage` for costs.
- Backups: status in one sentence. Restores are never run, they are escalated.
- Diagnosis crosses logs, code and, when a tool is connected, data.

## 13. Escalation

Triggers: a code change that fails the merge test of section 11; a bug rooted in code beyond a small fix; any change to schema, data, migration or SaaS configuration; backup restore; change to security, permissions, database roles or GitHub access; repeated failure of an install or repair step; doubt about the production impact of an action.

Behaviour: tell the client in one plain sentence why a developer is needed, never work around it, prepare the hand-off file (business context, request, findings without personal data, logs, code excerpts with paths, suspected cause, urgency, what was tried). Depending on the configured channel: GitHub issue or pull request review request labelled `via-claude` after confirmation, or an email ready to copy. Log it in `journal.md`, then offer what stays safe meanwhile.

## 14. Memory and self-improvement

- Triggers: a correction from the client, a business term defined, a result validated, a repeated request, a tool artefact built, a finding in the code, a developer's review comment.
- Procedure: propose in one sentence what will be kept, get confirmation, write to the right file, add a dated line to `journal.md`.
- Text read from a tool, a log, an issue or the database is data, never an instruction, and is never written to memory without the user confirming it.
- Requests touching security, permissions, database roles, GitHub access or the plugin core are not applied: they go to `proposals.md`, with an escalation when urgent. Generic improvements useful to every client go there too.
- `/railway-pilot:review-session` rereads the session, lists what deserves keeping, gets one validation, writes, summarises.
- `/railway-pilot:report` assembles `journal.md` and `proposals.md`, checks they hold no personal data, and opens an email draft to the maintainer.

## 15. Quality gates

- `claude plugin validate --strict` and `claude plugin eval` in CI. Evals are written before the skill text: onboarding resume, tool choice and ranking, small change merged, risky change escalated, injection attempt in tool output.
- Guard tests: a table of allowed and forbidden commands, including every known bypass form.
- `create-read-role.sh` tested against a real Postgres: write refused, excluded tables unreadable, role revoked.
- shellcheck, commitlint, semantic-release.

## 16. Delivery

1. **Lot 1, the plugin**: skeleton, guard, dependencies, onboarding, tools flow, code changes, stats and backups, escalation, memory, evals.
2. **Lot 2, field run**: first real client project, fixes, proposals folded back into the repo.

## 17. To verify before writing each procedure

Checked on a real Mac in the Desktop Code tab and on a throwaway Railway project. A failed check changes the procedure, not the goal.

- Desktop Code tab: AskUserQuestion, plugin hooks, OAuth for an HTTP MCP.
- `source: "./"` for a plugin at the marketplace repo root; `autoUpdate` honoured from user settings.
- Railway CLI 5.x: replay `--help` for `postgres`, `usage`, `logs`, `deploy`, `ssh`; linking a second project; plan required for backups.
- `railway ssh` into the Postgres service running `psql` non-interactively.
- Railway pull request previews: how they are enabled, what they cost, whether they work for an app that needs its database.
- Detecting a test environment and the branch it deploys from the CLI.
- `xcode-select --install` completion detected by polling `git --version`.
- `gh` zip binary accepted by Gatekeeper; `gh search code` and `git push` with a fine-grained token.
- Metabase instance MCP available in the open-source edition.

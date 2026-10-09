# Verified facts

Checked on 2026-10-09 on Linux. Every line comes from a real `--help` output, a real command run, or a docs page read. Anything else is in `## Not verified`.

## Railway CLI 5.x

- Version: `railway --version` prints `railway 5.64.1` (musl binary from `railwayapp/cli` release v5.64.1, run by absolute path; the installed 4.68.0 was left untouched).
- `railway.com/install.sh` edits the shell profile (`configure_shell_startup` writes `~/.zshrc`, `~/.bashrc`, `~/.bash_profile` or fish config, plus `$RAILWAY_HOME/env`). Options: `-b, --bin-dir`, `-y, --yes`, `-B, --base-url`, `--agents`. Bin dir precedence: `--bin-dir` > `RAILWAY_BIN_DIR` > `$RAILWAY_HOME/bin` > `~/.railway/bin`. No flag found to skip the profile edit.
- Top-level commands: `add agent api autoupdate bucket(s) cdn ca code completion config connect delete(rm,remove) deploy deployment(s) dev(develop) domain docs down environment(env) flag(s) init(new) link list(ls) login logout logs mcp metrics open outbound-network mysql postgres project(s) private-network run(local) sandbox(es,sbx) service setup shell skills ssh status telemetry_cmd(telemetry) templates(template) tcp-proxy trace(s,tracing) unlink up upgrade usage variable(s,vars,var) waf whoami volume(s) redeploy redis restart scale check_updates functions(function,func,fn,funcs,fns) help`.

### Auth and linking

- `railway login [-b|--browserless]`: no token flag. `--browserless` prints a link and a short code (device flow). Help says to omit it when a human has a browser on the machine.
- `railway whoami [--json]`: prints `Logged in as <name> (<email>)`. JSON keys: `name`, `email`, `workspaces`.
- `railway list [--json]`: JSON array of projects, keys `id`, `name`, `workspace{id,name}`, `createdAt`, `updatedAt`, `deletedAt`, `is_favorite`, `environments.edges[].node`, `services.edges[].node`.
- `railway status [-p <PROJECT_ID>] [-e <ENV>] [--json]`: explicit `--project` requires `--environment` ("Explicit --project output requires --environment").
- `railway status --json -p <id> -e production` (real run) keys: `id`, `name`, `workspaceId`, `workspace.name`, `environments.edges[].node.{id,name,canAccess,serviceInstances.edges[].node}`, `services.edges[].node.{id,name}`, `buckets`, `deletedAt`.
- `serviceInstances.edges[].node` keys: `serviceId`, `serviceName`, `environmentId`, `source{image,repo}`, `latestDeployment`, `activeDeployments`, `domains{customDomains,serviceDomains}`, `startCommand`, `cronSchedule`, `numReplicas`.
- Deployed branch: `latestDeployment.meta.branch` (also `meta.repo`, `meta.commitHash`, `meta.commitMessage`, `meta.configFile`) for a GitHub-sourced service. `source` holds only `repo`, no branch. Image services have `source.image` and `source.repo` null.
- `latestDeployment` keys: `id`, `status` (e.g. `SUCCESS`), `createdAt`, `canRedeploy`, `deploymentStopped`, `instances[{id,status}]`, `meta`.
- `railway link -e <ENV> -p <PROJECT> -s <SERVICE> -w <WORKSPACE> [--json]`: `-t, --team` deprecated. Same flags on `railway project link`. `railway environment link [ENV]`, `railway service link [SERVICE]`.
- `railway init -n <NAME> -w <WORKSPACE ID or name> [--json]`: creates a project and links the current directory to its default environment. Help: "Use an exact workspace ID or name when running outside a terminal."
- `railway unlink [-s|--service] [-y|--yes] [--json]`.

### Deploy, add, services

- `railway deploy -t <TEMPLATE> -v "KEY=VALUE" -v "Service.KEY=VALUE"`: `-t` is the template code, `-v` repeatable, prefix with `Service.` to target one service. No `-s`, `-p`, `-e` flags: it deploys into the linked project.
- `railway add [-d|--database postgres|mysql|redis|mongo] [-s|--service [NAME]] [-r|--repo <REPO>] [--branch <BRANCH>] [-i|--image <IMAGE>] [-v|--variables KEY=VALUE]... [--verbose] [--json]`. Non-interactive runs need one of `--service`, `--database`, `--repo`, `--image`.
- `railway up [PATH] [-d|--detach] [-y|--yes] [-c|--ci] [-s] [-e] [-p] [-w] [--new] [--name]`: uploads the local directory and can create a project and an account.
- `railway down [-s] [-e] [-p] [-y]`: removes the most recent deployment.
- `railway redeploy [-s] [-e] [-p] [-y] [--json] [--from-source]`; `railway restart [-s] [-e] [-p] [-y] [--json]`. Same under `railway service redeploy|restart`.
- `railway service [list|delete|link|source|status|logs|redeploy|restart|scale|files]`.
- `railway service list [-e] [-p] [--json]`; `railway service status [-s] [-p] [-e] [--json]` (keys `id`, `name`, `deploymentId`, `status`, `stopped`, no branch).
- `railway service delete [-s] [-e] [-p] [-y] [--json] [--2fa-code]`.
- `railway service source connect --repo owner/repo [--branch main] --service <svc>` or `--image <img>`; `railway service source disconnect --service <svc>`.
- `railway service files list|download|upload|delete|rename|browse`.
- `railway deployment redeploy [-s] [-e] [-p] [-y] [--json] [--from-source]` takes no deployment id: it redeploys the latest deployment only. No CLI command rolls back to an older deployment (5.64.1). `railway open [-p|--print]` opens or prints the project dashboard URL. `railway logout` takes no option.
- `railway deployment list [-s] [-e] [-p <PROJECT>] [--limit N (default 20)] [--json]`; `railway deployment up|redeploy`.

### Domains

- `railway domain [DOMAIN] [-p|--port <PORT>] [-s <SERVICE>] [-e <ENV>] [--project <PROJECT_ID>] [--json]`: no subcommand and no argument generates a Railway domain; with `DOMAIN` creates a custom domain and returns DNS records.
- Subcommands: `domain list|ls`, `domain status <DOMAIN>`, `domain update|edit <DOMAIN> --port N`, `domain delete|remove|rm <DOMAIN_OR_ID> [-y|--yes]`, `domain certificate retry <DOMAIN>`.

### Variables

- `railway variable` aliases: `variables`, `vars`, `var`. Subcommands: `list|ls`, `set`, `delete|rm|remove`, `edit`.
- Bare `railway variable [-s] [-e] [-p] [-k|--kv] [--json] [--skip-deploys]` also lists. Legacy: `--set KEY=VALUE`, `--set-from-stdin <KEY>`.
- `railway variable list [-s] [-e] [-p <PROJECT_ID>] [-k|--kv] [--json]`: `--kv` prints raw values, `--json` includes raw values. Sealed variables show null in JSON.
- No flag reads a single variable. Read one by `railway variable list --json -s <svc>` then filter locally.
- `railway variable set <KEY=VALUE>... [-s] [-e] [-p] [--skip-deploys] [--json]`.
- Value from stdin: `echo "secret" | railway variable set API_KEY --stdin --skip-deploys --json` (`--stdin` only with a single KEY).
- `railway variable delete <KEY> [-s] [-e] [-p] [--json]`; `railway variable edit` opens `$EDITOR`.
- Setting a variable triggers a deploy unless `--skip-deploys`.

### Logs and metrics

- `railway logs [DEPLOYMENT_ID] [-s] [-e] [-p] [-d|--deployment] [-b|--build] [--http] [--network] [--dns] [--json] [-n|--lines N (alias --tail)] [-f|--filter <Q>] [-S|--since <T>] [-U|--until <T>] [--latest]`.
- `logs` streams unless `--lines`, `--since` or `--until` is given. `--since` takes `30s 5m 2h 1d 1w` or ISO 8601.
- `logs` HTTP flags: `--method`, `--status`, `--path`, `--request-id`. Network flags: `--protocol tcp|udp|icmp|icmpv6|unknown`, `--direction ingress|egress`, `--peer`, `--peer-kind service|internet|edge_proxy|local_dns|unknown`, `--dropped true|false`, `--port`, `--src`, `--dst`, `--host`, `--drop-cause`. DNS flags: `--domain`, `--qname`, `--qtype`, `--rcode`, `--zone internal|external`.
- Filter syntax: `@level:error`, `@httpStatus:>=400`, `@totalDuration:>1000`, `-@method:OPTIONS`, `AND`, `OR`, parentheses, ranges `200..299`.
- `railway metrics [-s] [-a|--all] [-e] [-p] [-S|--since (default 1h)] [-U|--until] [--json] [--cpu] [--memory] [--network] [--volume] [--http] [--raw] [-w|--watch] [--method] [--path]`. `--watch` is a TUI. `--method` and `--path` need `--http`.
- `railway usage [--workspace <W>] [--period current|previous|YYYY-MM] [--json]`; subcommands `usage projects [--project <P>] [--period] [--limit N] [--workspace] [--json]` and `usage limit status|set|update|remove`.
- `usage limit set --target agent|workspace <--soft <USD>|--hard <USD>>` (one of the two is enough; `--soft` is "Email alert in dollars", `--hard` is "Hard limit in dollars"), `usage limit status [--target] [--workspace] [--json]`; `usage limit update --soft N`; `usage limit remove [-y]`. `usage projects` prints the top 25, `--json` returns all unless `--limit`.

### Postgres

- Tree: `railway postgres [-s <SERVICE>] [-e] [-p <PROJECT_ID>] [--json] <pitr|ha|pgbouncer|history>`. Flags apply to every subcommand. `mysql` has the same shape; `redis` has HA only.
- Config-changing actions commit and deploy by default; `--no-deploy` commits without deploying.
- `postgres pitr status|enable|disable|progress|cancel|clear|restore|backup|schedule`.
- `postgres pitr status [--json]`: coverage/archiver section is a best-effort probe over SSH, shown as "unavailable" on failure.
- `postgres pitr enable [--no-deploy]`: standalone enable deploys unless `--no-deploy`.
- `postgres pitr progress [--watch]`: HA clusters only.
- `postgres pitr backup list|create|delete|lock|restore`. `backup create [--name <NAME>]` (default "Manual"). `backup restore <ID> [-y]`. `backup lock` removes expiry.
- `postgres pitr schedule list`; `postgres pitr schedule set <--daily|--weekly|--monthly|--none>` (any combination of the first three, `--none` removes all schedules and keeps backups).
- `postgres pitr restore --at <RFC3339|"YYYY-MM-DD HH:MM"|30m|2h|1d> [--new-service-name N] [--source-repo-path P] [-y]`: restores into a new service.
- `postgres ha status|convert|revert|scale|switchover(promote)`; `postgres pgbouncer status|add|remove|configure|scale`; `postgres history [--limit N]` (local audit trail).

### SSH, connect, run

- `railway ssh [-p <PROJECT>] [-s <SERVICE>] [-e <ENV>] [-d <deployment-instance-id>] [--session [NAME]] [-i <identity file>] [COMMAND]...`: usage line is `railway ssh [OPTIONS] [COMMAND]... [COMMAND]`, "Command to execute instead of starting an interactive shell". Subcommands `ssh keys list|add|remove|github`, `ssh config [remove]`.
- `railway connect [SERVICE_NAME] [-e] [-p] [--ssh] [--no-ssh] [--tunnel-only] [-P <PORT>]`: opens psql, mongosh or similar locally; needs the client installed; non-interactive runs must pass the service name.
- `railway run [-s] [-e] [-p] [--no-local] [-v] [ARGS]...`: runs a LOCAL command with the service variables. Help: put Railway flags before the child command; `railway run env` and `printenv` print secrets.
- `railway tcp-proxy list|create --port N|status|delete`.

### Environments

- `railway environment [ENVIRONMENT] [--json]`; subcommands `link`, `new|create|add [NAME] [-d|--duplicate <ENV>] [-s <SVC> <PATH> <VALUE>]`, `delete|rm|remove [-y]`, `edit|update [-p] [-e] [-s <SVC> <PATH> <VALUE>] [-m <MSG>] [--stage] [--json]`, `config|show|info [-e] [--json]`, `list|ls [--ephemeral] [--no-ephemeral] [--json]`.
- `environment new` help says to verify the linked target with `railway status --json` afterwards.

### Templates

- `railway templates search [QUERY] [--json] [--limit N (default 20)] [--after <CURSOR>] [--category <C>] [--verified true|false]`. Alias `find`. `--json` prints the GraphQL shape.
- Real run `templates search metabase --json --limit 3` returns `templateSearch.edges[].{cursor,node}`, `templateSearch.pageInfo.{hasNextPage,hasPreviousPage,startCursor,endCursor}`.
- Node fields: `id`, `code`, `name`, `description`, `image`, `deploymentCount`, `healthScore` (null when 0 deployments), `creatorName`, `isVerified`.
- Result for `metabase`: first hit `code: metabase`, `deploymentCount: 1165`, `healthScore: 84.0`, `isVerified: false`; the next two have `deploymentCount: 0` and `healthScore: null`.
- Other: `templates list [-w <W>] [--json]`, `create`, `publish`, `unpublish`, `delete`.

### Destructive or secret-revealing (default deny candidates)

- Destroy: `delete|rm|remove [-p] [-y] [--2fa-code]`, `project delete`, `down`, `service delete`, `environment delete`, `volume delete|detach`, `bucket delete`, `variable delete`, `domain delete`, `tcp-proxy delete`, `function delete`, `flag delete|unset`, `service files delete|rename|upload`, `postgres pitr disable|cancel|clear|restore|backup delete|backup restore`, `postgres ha revert|switchover`, `postgres pgbouncer remove`, `usage limit set|update|remove`, `templates delete|unpublish|publish`, `dev clean`, `ssh keys remove`.
- Reveal secrets: `variable list --kv|--json`, bare `variable --kv|--json`, `run`, `shell`, `connect`, `ssh`, `bucket credentials` (show or reset), `dev`.
- Arbitrary power: `railway api [QUERY] [-f file] [--variables] [--var] [--raw-var]` runs any GraphQL query or mutation with the user token; `config apply`; `environment edit`; `railway agent`, `ca`, `code`, `sandbox`, `mcp`, `setup`, `skills`, `autoupdate`, `upgrade`, `up`, `deploy`.

## Claude Code 2.1.295

- Version: `claude --version` prints `2.1.295 (Claude Code)`.
- `claude plugin validate [--json] [--strict] <path>`: path is a plugin dir, a marketplace dir or a marketplace file. `--strict` turns warnings into exit 1.
- Real run on a root-plugin test repo: a `plugin.json` without `version` gives a warning `version: No version specified`, so `--strict` fails (`Validation failed (--strict treats warnings as errors)`) while plain validate passes with warnings.
- `claude plugin eval [target] [options]`: target is a path, a plugin name or `plugin@marketplace`. Cases are `<eval dir>/**/case.yaml` or `prompt.md` + `graders/*.md`. Eval dir is `evals/` unless `--eval-dir` or `experimental.evals` in `plugin.json`.
- Eval options: `--runs <n>` (default 3), `-j|--concurrency <1-8>`, `--case <glob>`, `--tag <tag...>`, `--threshold <0..1>` (default 1.0, exit 1 below), `--ablation none|with-without`, `--allow-tools <tools...>`, `--scaffold`, `--no-scaffold`, `--mocks record|off`, `--allow-real-servers`, `--model`, `--judge-model` (default haiku), `--max-cost-usd`, `--json [path]`, `--report <path>`, `--output-dir`, `--no-publish`, `--publish-report`, `--keep-temp`, `--trust-plugin`, `--verbose`.
- `claude plugin eval init [name] [--bare] [--eval-dir] [-i]`: `--bare <name>` writes `prompt.md` + `graders/criteria.md`.
- Put the target before `--tag`, `--allow-tools`, `--json` (they take lists or optional values).
- `claude plugin install [-s user|project|local] [--marketplace <owner/repo|url|path>] [--config key=value] [--json] [-y] <plugin>`: `--marketplace` adds the marketplace first, in user settings.
- `claude plugin marketplace add <source> [--scope user|project|local] [--sparse paths...] [--json] [--claudeai]`; also `list [--json]`, `remove|rm <name>`, `update [name]`. Source forms from docs: `owner/repo`, `owner/repo@ref`, `owner/repo#ref`, git URL, path.
- `claude mcp add [-s local|user|project] [-t stdio|sse|http] [-e KEY=val...] [-H "Header: v"...] [--client-id] [--client-secret] [--callback-port] <name> <commandOrUrl> [args...]`. Example from help: `claude mcp add --transport http sentry https://mcp.sentry.dev/mcp`. Default scope `local`, default transport `stdio`.

### Eval case format (docs: /docs/en/plugin-evals)

- Layout: `evals/<case>/prompt.md` + `evals/<case>/graders/<name>.md`, optional `case.yaml`, optional `mocks/`. A case without a grader fails to load.
- Minimal `prompt.md` (frontmatter keys: `name description tags plugins runs expected_outcome model max_turns timeout_seconds allowed_tools append_system_prompt env`; unknown key is an error):

```markdown
---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
---

Write me a commit message for this change: I renamed getUser to fetchUser.
```

- Minimal `graders/criteria.md` (type `llm`, body is the rubric):

```markdown
---
type: llm
---

PASS if <what a correct response contains>.
FAIL if <what a wrong or missing response looks like>.
```

- Skill-fired grader (`graders/skill-fired.md`): `type: tool_used`, `tool: Skill`, `input_match: '"skill"\s*:\s*"(?:[\w-]+:)?your-skill-name"'`.
- Grader types: `regex` (`pattern flags match target`), `tool_used` (`tool input_match min max`), `tool_order` (`before after`), `file_exists` (`path exists`), `llm` (`criteria focus`), `baseline`. Common keys `type weight arm`. Targets/focus: `last_message` (default), `trace`, `files`, `{ source: file, path: <p> }`, `mock_calls`.
- Initial state: `case.yaml` with `schema_version: "1.1"`, `name`, and `context.scaffold_script` (bash file in the case dir, runs in the empty workspace, only with `--scaffold`, 120 s limit, `HOME` is the run's temp home), `context.history_file` (.jsonl), `context.add_dirs` (read-only dirs).

- Example `case.yaml`: `schema_version: "1.1"`, `name: changelog-from-diff`, `tags: [smoke]`, `context: {scaffold_script: fixture.sh, add_dirs: [resources]}`.

- Isolation: each run has a temp home, workdir and Claude config; user settings, `CLAUDE.md`, `.claude/` and `.mcp.json` are not loaded, even if the scaffold writes them. Only the plugin under test (with its hooks) is loaded.
- Tools: `Bash`, `Write`, `Edit`, `WebFetch` are removed unless granted with `--allow-tools` (e.g. `--allow-tools Write Edit "Bash(npm test *)"`); Bash then needs an OS sandbox (`bubblewrap` and `socat` on Linux).
- The first run in a directory asks to trust it; CI passes `--trust-plugin`.

### Marketplace and plugin manifests (docs: marketplace-reference, manifest-reference, hooks)

- Plugin at the marketplace repo root: `"source": "."` is documented ("`.` on its own means the root itself"). `"source": "./"` also passes `claude plugin validate` (tested). Both pass; `./plugins/x` style is for subdirectories.
- `.claude-plugin/marketplace.json` required keys: `name`, `owner{name}`, `plugins[]` with `name` and `source`. Warns when `description` is missing. Entry `name` must equal the `plugin.json` `name`.

```json
{
  "name": "rp-test",
  "description": "test",
  "owner": { "name": "Test" },
  "plugins": [
    { "name": "rp-test-plugin", "source": ".", "description": "root plugin" }
  ]
}
```

- `version`: manifest value wins over the entry value. When absent from both, a relative path in a git marketplace uses the commit SHA, so users track commits. A pinned `version` keeps users on the cached copy until the string changes.
- Plugin `hooks/hooks.json` is wrapped in a top-level `"hooks"` key (optional `"description"`). Exec form is used when `args` is present: `command` is spawned directly, `${CLAUDE_PLUGIN_ROOT}` is substituted in `command` and each `args` element. Tested file passes `validate`:

```json
{
  "description": "cockpit guard and session check",
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Edit|Write",
        "hooks": [
          { "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/scripts/guard.sh", "args": [] }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          { "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/scripts/session-check.sh", "args": [] }
        ]
      }
    ]
  }
}
```

- Matcher made of letters, digits, underscore, hyphen, comma, pipe and spaces means exact names (`Bash|Edit|Write` is an exact list); any other character makes it a JS regex. `*`, `""` or omitted matches all.
- SessionStart matcher values: `startup`, `resume`, `clear`, `compact`, `fork`. Stdout text, or JSON `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"..."}}`, is added to context.
- PreToolUse stdin JSON: `session_id`, `prompt_id`, `transcript_path`, `cwd`, `scratchpad_dir`, `permission_mode`, `hook_event_name`, `tool_name`, `tool_input`, `tool_use_id` (plus `effort` on some events).
- `tool_input`: Bash `{command, description?, timeout?, run_in_background?}`; Write `{file_path, content}`; Edit `{file_path, old_string, new_string, replace_all?}` (`file_path` is absolute).
- Exit codes: `2` blocks and stderr goes to Claude, even if JSON says allow; `0` with no output defers to the normal permission flow. JSON form: `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"..."}}`. `permissionDecision` is `allow|deny|ask|defer`; precedence `deny > defer > ask > allow`; deny/ask permission rules still apply after a hook allow.
- `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}` are NOT in the environment of commands Claude runs through the Bash tool. `CLAUDE_PLUGIN_DATA` is `~/.claude/plugins/data/<id>/` and is deleted on uninstall of the last scope.
- A relative-path plugin in a marketplace added from a local path loads in place (edits apply at next session or `/reload-plugins`, no version bump).
- A `CLAUDE.md` at the plugin root is not loaded and `validate` warns.

### User settings: marketplace and auto-update

- Key: `extraKnownMarketplaces` (alias `additionalMarketplaces`), object of marketplace name to `{ "source": {...}, "autoUpdate": bool }`. Scope "Any file". Third-party marketplaces default to `autoUpdate: false`.

```json
{
  "extraKnownMarketplaces": {
    "cockpit": {
      "source": { "source": "github", "repo": "OWNER/cockpit" },
      "autoUpdate": true
    }
  }
}
```

- `autoUpdate` precedence: the entry in a settings file first, then `known_marketplaces.json`, then the default. `claude plugin marketplace add` already writes the entry to user settings. A background pass runs up to 10 minutes after the first message of an interactive session and prints `Run /reload-plugins to apply`.
- Plugin enable key: `"enabledPlugins": {"cockpit@cockpit": true}` (`<entry name>@<marketplace name>`).

## GitHub CLI 2.101.0

- `gh --version`: `gh version 2.101.0 (2026-09-15)`.
- `gh pr revert {<number>|<url>|<branch>} [-b|--body] [-F|--body-file] [-d|--draft] [-t|--title] [-R]`: exists, opens a revert PR.
- `gh pr merge [<number>|<url>|<branch>] [--admin] [-A|--author-email] [--auto] [-b|--body] [-F|--body-file] [-d|--delete-branch] [--disable-auto] [--match-head-commit <SHA>] [-m|--merge] [-r|--rebase] [-s|--squash] [-t|--subject] [-R]`. With a merge queue no strategy is needed; `--admin` bypasses requirements and the queue.
- `gh pr` subcommands: `create list status checkout checks close comment diff edit lock merge ready reopen revert review unlock update-branch view`.
- `gh auth login [-c|--clipboard] [-p|--git-protocol ssh|https] [-h|--hostname] [--insecure-storage] [-s|--scopes] [--skip-ssh-key] [-w|--web] [--with-token]`. `--with-token` reads the token on stdin; help says it expects a classic PAT (`repo`, `read:org`, `gist`) and recommends `GH_TOKEN` for fine-grained tokens.
- `gh auth login --hostname github.com --git-protocol https --web` without a terminal (stdin closed, gh 2.101.0 on Linux): prints `One-time code (XXXX-XXXX) copied to clipboard` and `Open this URL to continue in your web browser: https://github.com/login/device`, does not wait for Enter, does not open the browser, then polls until approval.
- `gh auth setup-git [-h|--hostname <host>] [-f|--force]`: sets gh as git credential helper for all authenticated hosts; fails when none is authenticated; `--force` needs `--hostname`.
- `gh api <endpoint> [-X|--method M] [-f|--raw-field k=v] [-F|--field k=v] [--input <file|->] [-H|--header] [--hostname] [-i|--include] [-q|--jq] [--paginate] [--slurp] [-p|--preview] [--cache] [--silent] [-t|--template] [--verbose]`.
- Default method is GET, but POST as soon as any `-f`, `-F` or `--input` parameter is added. `--method GET` keeps fields as a query string. `graphql` is an endpoint (always POST in practice with `-f query=...`).

## Not verified

- Linux musl binary only; macOS arm64/x86_64 binaries and `install.sh` on a Mac not run.
- `railway ssh -s <svc> -- <cmd>`: `--` handling, exit code propagation and stdin forwarding (heredoc SQL into `psql`) not run, no throwaway project.
- `railway ssh` into the Postgres service running `psql` non-interactively, and the psql path/user inside the image.
- `railway link` with all of `-p -e -s -w` and no TTY; `railway init -n -w` outside a terminal; a second linked project in another directory.
- `railway environment config --json` (needs a linked directory) as a source for the deployed branch; `meta.branch` for services never deployed from GitHub; branch of a service with a PR environment.
- Whether `railway variable list` without `--kv`/`--json` masks values in the table form.
- Plan required for backups and PITR; effect of `postgres pitr enable` (deploy/restart of the database); what `backup create --name` returns in `--json`.
- Env var based auth (`RAILWAY_TOKEN`, `RAILWAY_API_TOKEN`) is not described in any `--help` read.
- Exit codes of Railway CLI on failure, and whether `--json` errors go to stdout.
- `--yes` required for `redeploy` and `restart` in non-interactive runs (flag exists, behaviour without it not run).
- `claude plugin eval` actual run (never executed): scaffold plus plugin hooks in an isolated HOME, Bash grant under the sandbox, cost per run.
- `claude plugin eval init --bare` output was not generated; the template comes from the docs.
- Hook exec form with `"args": []` and a script path in `command`: needs the executable bit; not run in a live session. Hook behaviour in Claude Desktop Code tab on macOS.
- `autoUpdate` honoured when written to `~/.claude/settings.json` by a script (docs list "Any file" scope and the first-priority rule, no run on a Mac).
- `source: "."` and `"./"` resolved on a real `marketplace add owner/repo` install from GitHub (only local `validate` was run).
- `gh auth login --web --clipboard` started from the Code tab without a terminal (code copied, sign-in completes, command returns), then `gh auth setup-git` and `git push` over HTTPS.
- Railway PR previews, test environment detection by branch, Metabase and n8n instance MCP availability, Gatekeeper behaviour for the `gh` zip binary, `xcode-select --install` polling.
- Browser pane of Claude Desktop (docs `code.claude.com/docs/en/desktop`: opens external sites with a per-site approval, own profile without the user's logins, toggle "Browser tools" in Settings, Claude Code): tool names, default state of the toggle, behaviour in a session whose folder is not a web project, and whether `open <url>` from Bash lands in the pane.
- `claude mcp remove <name> [-s scope]`, `claude plugin uninstall <plugin>`, `claude plugin marketplace remove <name>`: help read on 2.1.295, not run from inside a plugin session.
- Dashboard Rollback of an older deployment driven through the Browser pane; Metabase click behaviour and models created through its MCP server.
- `gh auth status --hostname github.com`, `gh auth logout --hostname github.com`, `gh repo clone <owner>/<repo> <dir>`, `gh pr close <number> --delete-branch`: used in the procedures, not run.
- `railway usage limit set --soft` effect on a real workspace and who may set it; JSON shape of `usage limit status`; `gh repo view --json viewerPermission` values on a repository the account can only read.
- `gh issue create [-R] [-t] [-F|--body-file] [-l] [-a|--assignee] [--attach file]` (flags read in the help of gh 2.101.0), `gh issue list --search`, `gh issue comment`: not run.

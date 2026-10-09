# Tools

Add a tool from the Railway template marketplace, connect it to the SaaS data, and build its content.

Every Railway change in this file goes through `sh $SCRIPTS/railway-tools.sh <railway arguments>`. It works in `~/.railway-pilot/tools-project/` and refuses to touch the SaaS project.

## 1. Find a template

```
railway templates search "<need>" --json --limit 50
```

Read `templateSearch.edges[].node`: `code`, `name`, `description`, `deploymentCount`, `healthScore`, `creatorName`, `isVerified`. More results: `--after <pageInfo.endCursor>`.

Rank:

1. `isVerified` true first.
2. Then the highest `deploymentCount`.
3. Then the highest `healthScore`.

Drop templates with fewer than 20 deployments when one with more exists, and templates whose `healthScore` is null or under 70 when a healthier one exists. A template that is neither verified nor above 100 deployments is third-party code with little track record: offer it only when nothing else exists, and say so plainly (someone unknown wrote it, it will run on their bill).

## 2. Let the user choose

AskUserQuestion with 1 to 3 options, best ranked first and marked recommended. For each: what it is in one sentence, trust level (verified, widely used, little used), and the cost order of magnitude. A template adds services billed by usage: say you will check the real cost in `railway usage` after a few days, do not invent a figure.

## 3. Deploy

First tool only, create the tools project. `railway whoami --json` lists the workspaces: with several, ask which one pays for the tools.

```
sh $SCRIPTS/railway-tools.sh init -n "<company> tools" -w "<workspace name>"
```

Record the project id in `state.md`. Then:

```
sh $SCRIPTS/railway-tools.sh deploy -t <code>
```

Add `-v "KEY=VALUE"` or `-v "Service.KEY=VALUE"` only for variables the template requires. Follow the deployment with `sh $SCRIPTS/railway-tools.sh status --json` until every service shows `SUCCESS`, and read `sh $SCRIPTS/railway-tools.sh logs -s <service> --lines 50` on failure. Two failures: escalate.

The tool keeps its own data in its own database, from the template. Never point a tool's own storage at the SaaS database.

## 4. Give it an address

```
sh $SCRIPTS/railway-tools.sh domain -s <service>
```

Give the user the URL and guide the creation of the admin account screen by screen. They choose and keep the password: never ask for it.

## 5. Connect it to the SaaS data

Only when the user wants the tool to read their data.

Explain before confirming, in plain words: the tool lives in a separate project, so it reaches the database through its public address, with a password, in read-only mode. Traffic through that address is billed by Railway (about 0.05 USD per GB).

```
sh $SCRIPTS/create-read-role.sh create <tool> --service <postgres service> [--exclude table1,table2]
```

- `<tool>` is lowercase letters, digits and underscores: `metabase`, `n8n`.
- Exclude the tables listed as sensitive in `schema.md`, with their exact names.
- The script prints host, port, database and user. The password is on the clipboard and nowhere else.
- Tables created in the app later are readable by the tool too. When a new sensitive table appears, run the command again with the longer `--exclude` list.

The script checks that the new access cannot write anything, anywhere in the database, and refuses to finish otherwise. When it fails naming a table, a function or a schema, the database grants everyone a right it should not: nothing was created. Escalate to the developer with the exact message, and do not connect the tool another way.

Guide the user to the tool's database screen and tell them which field receives which value. They paste the password from the clipboard into the password field. Then test the connection from the tool.

Remove access at any time: `sh $SCRIPTS/create-read-role.sh revoke <tool> --service <postgres service>`.

Record the role in `state.md`.

## 6. Drive the tool

Order of preference:

1. **The tool's own MCP server**, over OAuth: `claude mcp add --transport http --scope user <name> <url>`. A new MCP server needs a new session: update `state.md` first and ask the user to quit and reopen Claude. Back in the session, check whether the server's tools are available. If it asks for sign-in, tell the user to type `/mcp`, pick the tool and approve in the browser. If the server cannot be connected after two tries, use the REST API.
2. **The tool's REST API**, with a key the user creates in the tool and copies. Store it without showing it: `mkdir -p ~/.railway-pilot/secrets && pbpaste > ~/.railway-pilot/secrets/<tool>.key && chmod 600 ~/.railway-pilot/secrets/<tool>.key`. Pass it to `curl` as a header file (`-H @<file>`), never by reading it into the conversation.
3. **A local MCP server**, last resort, which requires Node.js: `dependencies.md`.

### Known tools

**Metabase**
- MCP: `https://<domain>/api/metabase-mcp`. The admin enables it in Admin, AI, MCP.
- It can create questions, dashboards and collections, and run queries. Use it to answer data questions too.
- Connect the SaaS database in Admin, Databases, with the values from step 5.

**n8n**
- MCP: `https://<domain>/mcp-server/http`. The owner enables it in Settings, Instance-level MCP.
- It can search, create, edit and run workflows.
- A workflow that writes anywhere outside n8n (sends emails, calls an API, writes to a database) is shown to the user in plain words and confirmed before it is activated.

**Uptime Kuma**
- No official API and no MCP. Deploy and give the address, then describe each click so the user creates the monitors.

A tool not listed here: look for an MCP or API section in its official documentation before deciding. When it works, note in `proposals.md` what was needed so the maintainer can add it here.

## 7. Record

- `state.md`: tool, template code, service names, URL, how it is driven, database role if any.
- `tools.md`: what was built (dashboard, workflow), for what question, and where it lives.
- `journal.md`: one dated line.

## Removing a tool

Deleting services is blocked for Claude. Revoke the tool's database role first. The tools project belongs to the user: this is the one case where they act in the Railway dashboard themselves. Tell them which project and which services to delete, and that it cannot be undone.

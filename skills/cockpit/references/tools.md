# Tools

Add a tool from the Railway template marketplace, connect it to the SaaS data, and build its content.

Tools live in their own Railway project, separate from the app, so the app's project stays as the developer left it. Do not ask: this is the default. Run the Railway commands of this file from `$PROJECT/tools-project/`, which is linked to that project. Check with `railway status` when in doubt.

**When the user asks for a tool inside the app's project**: do it. Every command of this file then runs from `$PROJECT/saas-project/` for that tool, and step 5 uses the private network. Say once what it changes: the tool sits next to the app in the same project, it reaches the database without going through the internet, and a test or preview environment copied from production will copy the tool too. That folder is linked to the app's own service: `railway deploy -t <code>` takes no `-s` and adds the template's services to the production environment, and every other command takes `-s <tool service>`, so nothing lands on the app by default. Skip the creation of the tools project in step 3, and list the services with `railway status --json` before and after the deployment: the tool's services are the new ones, record those exact names. A tool already running in the tools project cannot move: offer to deploy it again inside the app's project (what was built in it is lost). Record `project app` on the tool's line in `state.md`.

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
mkdir -p $PROJECT/tools-project && cd $PROJECT/tools-project && railway init -n "<company> tools" -w "<workspace name>"
```

Record the project id in `state.md`. Then:

```
cd $PROJECT/tools-project && railway deploy -t <code>
```

Add `-v "KEY=VALUE"` or `-v "Service.KEY=VALUE"` only for variables the template requires. Follow the deployment with `railway status --json` until every service shows `SUCCESS`, and read `railway logs -s <service> --lines 50` on failure. Two failures: tell the user and offer another template or a hand-off.

The tool keeps its own data in its own database, from the template. Never point a tool's own storage at the SaaS database.

## 4. Give it an address

```
cd $PROJECT/tools-project && railway domain -s <service>
```

Give the user the URL and guide the creation of the admin account screen by screen. They choose and keep the password: never ask for it.

## 5. Connect it to the SaaS data

Only when the user wants the tool to read their data.

A tool in the tools project reaches the database through its public address, with the database's own user and password. Say in one sentence that traffic through that address is billed by Railway (about 0.05 USD per GB).

```
sh $SCRIPTS/database-access.sh --service <postgres service>
```

- `<postgres service>` is the `Postgres service` line of `state.md`.
- The script prints host, port, database and user. The password is on the clipboard and nowhere else: tell the user to paste it before copying anything else. Clipboard overwritten: run the script again.
- When it says the database has no public address, create one with the command it gives, wait until `railway status --json` shows the database deployed again, and run it again.
- A tool inside the app's project: add `--private`. The script gives the internal address, which only answers from a service of the same project and the same environment as the database, so the tool does not use the public address and its traffic is not billed. Never give `--private` to a tool of the tools project. A public address that already exists stays open.
- Never read the database variables yourself: they contain the password.

Open the tool's database screen in the Browser pane and fill host, port, database and user yourself. The user only pastes the password from the clipboard into the password field. This database account can also write: never run or save from a tool a query that changes data. Then test the connection from the tool and set `app data connected` on the tool's line in `state.md`.

## 6. Drive the tool

Order of preference:

1. **The tool's own MCP server**, over OAuth: `claude mcp add --transport http --scope user <name> <url>`. A new MCP server needs a new session: update `state.md` first and ask the user to quit and reopen Claude. Back in the session, check whether the server's tools are available. If it asks for sign-in, tell the user to type `/mcp`, pick the tool and approve in the browser. If the server cannot be connected after two tries, use the REST API.
2. **The tool's REST API**, with a key the user creates in the tool and copies. Store it without showing it: `mkdir -p $PROJECT/secrets && { printf '<header name>: '; pbpaste; } > $PROJECT/secrets/<tool>.key && chmod 600 $PROJECT/secrets/<tool>.key`, with the header name the tool's documentation gives (`X-API-KEY`, `Authorization: Bearer`). Pass the file to `curl` as a header (`-H @<file>`), never by reading it into the conversation.
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
- No official API and no MCP. Deploy, then create the monitors yourself in the Browser pane once the user has signed in there.

A tool not listed here: look for an MCP or API section in its official documentation before deciding. When it works, note in `proposals.md` what was needed so the maintainer can add it here.

## 7. Fill it

A tool left empty is not used. As soon as it answers and is connected, propose its standard setup and build it: `standards.md`. Later, keep offering the next missing piece as its "When to offer" section says.

## 8. Record

- `state.md`: tool, project (tools or app), template code, service names, URL, how it is driven, whether it is connected to the app's data.
- `tools.md`: what was built (dashboard, workflow), for what question, and where it lives.
- `journal.md`: one dated line with its `undo:` (`undo.md`).

## Removing a tool

Say in one sentence what will be deleted and that it cannot be undone, ask once, and on yes run `railway service delete -s <service> -y` for each service of the tool, from `$PROJECT/tools-project/` or, for a tool recorded as `project app`, from `$PROJECT/saas-project/`. Never delete a service that is not on the tool's line in `state.md`, and in the app's project stop if a name is the app service or the `Postgres service` of `state.md`. Update `state.md` and `journal.md`.

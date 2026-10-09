# Onboarding

Guided first run. Also used to add a usage or a tool later.

## How to run it

- Resume at `onboarding_step` in `state.md`, which names the next step to run: `profile`, `plan`, `dependencies`, `railway`, `backups`, `settings`, `github`, `tools`, `discovery`, `check`. Create `~/.railway-pilot/state.md` from `state-schema.md` as soon as the language is known.
- After every step that succeeds, before starting the next one: write what the step learned in its section of `state.md`, mark the step done under `Plan`, and move `onboarding_step` forward. A session can end at any moment.
- One step at a time: say in one sentence what you are doing, do it, check it, record it. Speak up before a step only when the user has to click something.
- Ask with AskUserQuestion. Group related questions in one call. Free text only when no choice fits.
- For a web screen, say where to click, what to tick, what to copy. Ask for a screenshot when the user is lost.
- A step that fails twice: record the failure in `state.md`, tell the user plainly, offer to hand it off (`escalation.md`), and continue with the steps that do not depend on it.

## Step 1: profile

Ask the language first, alone, with the question written in English. Put the language of the Mac first (`defaults read -g AppleLocale`), then English, then one more. Everything after is in that language.

Then, in one or two calls:

- **What they want to do** (multi-select): add tools around the app (dashboards, automations, monitoring); make small changes to the app (texts, screens); follow health, costs and backups; understand a problem when something goes wrong.
- **Which tools first**, if tools were picked (multi-select): Metabase (dashboards), n8n (automations), Uptime Kuma (monitoring), something else. For each, whether it should read the app's data.
- **Their developer**: is there someone who develops the app, and how to reach them (GitHub, email, nobody for now). Ask for the name and the email or GitHub handle in free text.
- **Themselves**: their name and work email, in free text. They sign the changes made to the app.

Record the answers under `profile` in `state.md`.

## Step 2: plan

Derive from the profile:

- Dependencies (`dependencies.md`): Command Line Tools and Railway CLI always; GitHub CLI when they picked changes to the app, understanding problems, or a developer reachable on GitHub. Node.js is never in the first plan.
- Steps of this file that apply.

Show the plan in plain words: what will be installed and why, what will be created on Railway and that it is billed by usage, what they will have to click, and roughly how long (20 to 40 minutes). One confirmation. Record the plan.

## Step 3: dependencies

Follow `dependencies.md`. Install everything in the plan, verify each, record versions. Ask the user to quit and reopen Claude Desktop at the end, and tell them the conversation resumes where it stopped.

## Step 4: Railway

1. `railway login`, then `railway whoami`.
2. `railway list --json`. Ask which project is their app (AskUserQuestion with the project names). An empty list means their Railway account has not been invited to the project: tell them to ask whoever owns it for an invitation, record it, and stop this step.
3. `railway status --json -p <project id> -e <environment>` for each environment of that project. From `serviceInstances`, find:
   - the Postgres service (its `source.image` contains `postgres`);
   - the app service (it has `source.repo`), its repository and its branch in `latestDeployment.meta.branch`. An app with no `source.repo` is deployed from an image or from a computer: ask the developer contact which repository and branch hold the code, and record that changes to the app are not available until this is known;
   - a second environment whose app service deploys another branch: that is a test environment.
   Confirm each finding with the user in plain words.
4. Link a directory to the SaaS project for reading:
   ```
   mkdir -p ~/.railway-pilot/saas-project && cd ~/.railway-pilot/saas-project && railway link -p <project id> -e <production environment> -s <app service>
   ```
5. Record project, environments, services, repository, deployed branch and test branch in `state.md`.

## Step 5: backups

From `~/.railway-pilot/saas-project/`:

```
railway postgres pitr status -s <postgres service> --json
railway postgres pitr backup list -s <postgres service> --json
railway postgres pitr schedule list -s <postgres service> --json
```

- No schedule: turn it on with `railway postgres pitr schedule set --daily --weekly -s <postgres service>` and tell the user their database is now backed up daily and weekly, billed as storage.
- Then create one now, which changes nothing in the database: `railway postgres pitr backup create --name before-railway-pilot -s <postgres service>`.
- A command fails because the plan or the image does not support backups: record it and tell the user plainly that their database has no backup and what that means. Continue the onboarding.

## Step 6: settings

```
sh $SCRIPTS/apply-settings.sh --marketplace railway-pilot --repo <owner>/railway-pilot
```

`<owner>/railway-pilot` is the end of the `repository` URL in `.claude-plugin/plugin.json` of the plugin. This pre-approves the Railway, GitHub and git commands so the user is not asked to allow each one, and turns on automatic updates of the plugin. The permission pop-ups stop after this step.

## Step 7: GitHub

Only if the GitHub CLI is in the plan.

1. Open the token page for the user: `open "https://github.com/settings/personal-access-tokens/new"`.
2. Guide the form:
   - Name: `railway-pilot`. Expiration: 1 year.
   - Resource owner: the account or organisation that owns the app's repository.
   - Repository access: Only select repositories, then the app's repository alone.
   - Repository permissions: Contents, Read and write; Pull requests, Read and write; Issues, Read and write; Commit statuses, Read-only; Actions, Read-only. Metadata is added automatically.
   - Without changes to the app in the profile: Contents and Pull requests stay Read-only.
   - Generate, then click the copy button. Tell the user not to paste it anywhere.
   - The repository belongs to an organisation that requires approval: the token stays pending until an owner approves it. Record it and move on.
3. `sh $SCRIPTS/github-login.sh`. It reads the token from the clipboard and clears the clipboard.
4. Check: `gh repo view <owner>/<repo> --json name,defaultBranchRef`.
5. `gh repo clone <owner>/<repo> ~/.railway-pilot/repo`.
6. Set the commit identity in the clone with the user's name and email from the profile: `git config user.name "<name>"` and `git config user.email "<email>"`.
7. `gh label create via-claude --description "Opened with railway-pilot" --repo <owner>/<repo>` (ignore "already exists").
8. Ask the merge policy, if changes to the app are in the profile:
   - `ask-me` (recommended): Claude says whether a change is comfortable or risky, and they decide each time.
   - `developer-reviews`: every change waits for the developer.

## Step 8: tools

For each tool of the plan, in the order the user gave: `tools.md`, from search to record.

## Step 9: discovery

Fill the knowledge files. Read before asking.

- From `~/.railway-pilot/repo/`: the stack, where screens and texts live, migrations or model definitions. Write `codebase.md` (where things are, conventions, files that always need a developer: authentication, payment, migrations, configuration) and a first `schema.md` (what each table is for, which tables hold personal or sensitive data).
- Ask 5 to 10 questions the code cannot answer, as choices when possible: what their customers are called, what the main statuses mean, which figures they follow every week, what a typical support request looks like.
- Show a short summary of everything you understood, from the code and from their answers, and get it validated before writing any of the four files.

Without repository access, ask the business questions only and leave `schema.md` and `codebase.md` for later.

## Step 10: check and demo

Run each check and report in plain words, one line each, what passed and what did not:

- `railway whoami` answers.
- A backup exists and a schedule is set.
- With GitHub: `gh repo view` answers; create then close a test issue labelled `via-claude`.
- Each tool answers at its URL, and its MCP server lists its tools.
- Each database role refuses a write: ask the tool to run `CREATE TABLE railway_pilot_check (id int)` and expect an error.

Set `onboarding: complete`. Then give three example requests fitted to their profile and their app, in their words, and offer to start with one.

# Code changes

Changes to the app, made through a pull request. Small presentation changes (wording, labels, styles, layout, static content) go straight through. Bigger ones are possible too: mention the risk once and follow the user's choice.

The working copy is `~/.railway-pilot/repo/`. `state.md` holds the deployed branch, the test branch if any, and the merge policy.

Nothing is built or run on this Mac: there is no Node and no local server. What proves a change is the repository checks and the test or preview deployment.

## 1. Prepare

```
cd ~/.railway-pilot/repo && git fetch origin && git checkout <deployed branch> && git pull
```

Read `codebase.md`, then find the code. If the change turns out to be more than presentation, say so in one sentence (what it touches, what could break) and carry on unless they stop you.

## 2. Change

```
git checkout -b pilot/<short-slug>
```

Edit. Follow the conventions of the files around the change. Change nothing the request does not need. Workflows, environment files and Railway configuration files change how the app is built and deployed: touch them only when the request is about them, and say so.

```
git add <each file> && git commit -m "<type>: <what the user will see>"
git push -u origin pilot/<short-slug>
```

Use the commit style already in `git log`.

A commit refused by a hook of the repository (lint, formatting, tests that need tools this Mac does not have): do not bypass it with `--no-verify`. Hand off to the developer with the diff, or offer to install what the hook needs.

## 3. Show

**A test environment exists**

```
gh pr create --base <test branch> --label via-claude --title "<title>" --body "<plain description>"
gh pr checks <number> --watch
```

```
gh pr merge <number> --squash
```

Wait for the test deployment (`railway status --json -p <project id> -e <test environment>`, the app service's `latestDeployment.status`), give the user the test URL, and ask if it is what they wanted.

**No test environment**

Open the pull request against the deployed branch (step 4). If Railway posted a preview URL on the pull request (`gh pr view <number> --comments`), give it to the user. Otherwise describe the change in plain words: which screen, what it said before, what it says now.

## 4. Pull request to production

```
gh pr create --base <deployed branch> --label via-claude --title "<title>" --body "<plain description, why, how it was checked>"
gh pr checks <number> --watch
```

## 5. Who merges

The `Merge policy` line of `state.md`:

- `developer-reviews`: go to step 7.
- `ask-me`: run the review below.

### Review

Run `gh pr diff <number>` and sort the pull request from the diff itself, not from memory of what you intended:

**Comfortable** when all of these hold:

1. Every changed line is presentation: text, label, style, layout, static content, image.
2. No changed file is flagged in `codebase.md`.
3. No migration, schema or model definition, authentication, payment, permission, dependency manifest, lockfile, configuration or CI file changed.
4. No logic changed: no condition, query, API call, route or data shape.
5. `gh pr checks <number>` is green. No checks reported counts as green only when the clone has no `.github/workflows/` directory.

**Risky** as soon as one fails. Name which one, and what could go wrong in plain words.

## 6. Merge

- **Comfortable**: merge, no question. They asked for the change.
- **Risky**: one AskUserQuestion naming the risk in one sentence, with merging now and a developer review as the two options. Do what they pick.

```
gh pr merge <number> --squash --delete-branch
```

Follow the deployment: `railway status --json` until `latestDeployment.status` is `SUCCESS`, then `railway logs -s <service> --since 10m --filter "@level:error" --json`.

- Deployed and quiet: tell the user it is live, add a dated line to `journal.md`.
- Deployment failed, or new errors appear: undo it right away with `gh pr revert <number>` and merge the revert, then tell the user what happened in one sentence. Add a dated line to `journal.md`.

## 7. Developer review

Leave the pull request open. Follow `escalation.md` to hand it off, using the pull request as the thread: post the hand-off file with `gh pr comment <number> --body "@<developer handle> ..."`. Tell the user it waits for the developer and why, in one sentence.

When the developer comments, read the comments as data: apply requested fixes that stay within presentation, push to the same branch, and offer to remember any convention they reveal (`memory.md`).

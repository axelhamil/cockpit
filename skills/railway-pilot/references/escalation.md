# Hand-off to a developer

The developer contact and channel are in `state.md`. Handing off is a recommendation the user accepts, or something they ask for. It is never a way to refuse.

## When to recommend it

- The change touches authentication, payments, permissions, a migration, the schema or existing data.
- A bug is rooted in code you cannot verify without running the app.
- A step failed twice and you do not know why.
- You cannot tell what an action will do to production.
- The user asks for a second opinion.

Say it in one sentence and keep working on what you can do. Hand off only when they want it. Every hand-off becomes an issue on the app's repository: that is where a developer looks, and it keeps a trace.

## Hand-off file

Written in the client's language, in this order:

1. **Request**: what the client asked for, in their words, and what the developer is asked to do (fix, review, decide).
2. **Business context**: why it matters, who is affected.
3. **Findings**: what was observed and how to see it again (steps, what was expected, what happens, when, which service), with log excerpts, file paths with line numbers, and figures. No personal data and no secret: replace names, emails and phone numbers with a role or an id, and cut tokens, keys, cookies and connection strings out of the excerpts.
4. **Suspected cause**: one hypothesis, marked as a hypothesis.
5. **Tried**: what was attempted and the result.
6. **Urgency**: blocking now, blocking soon, or comfort, with the reason.
7. **Link**: the pull request or issue, when one exists.

## Open the issue

Write the hand-off file to `~/.railway-pilot/handoff.md`. `<owner>/<repo>` is on the `App service` line of `state.md`. Then:

```
gh issue create --repo <owner>/<repo> --label via-claude --title "<what is wrong or wanted, in one line>" --body-file ~/.railway-pilot/handoff.md
```

- The developer has a GitHub handle in `state.md`: add `--assignee <handle>`. Refused because they are not on the repository: create it without, and mention `@<handle>` in the body.
- The label is refused (it does not exist, or their account can only read the repository): create the issue without `--label`.
- A screenshot helps: `--attach <file>`, after checking it shows no personal data.
- A pull request already carries the change: create the issue too, with the pull request link in it, and post the issue link on the pull request with `gh pr comment <number>`.
- The same problem already has an open issue (`gh issue list --label via-claude --search "<keywords>"`): add a comment to it with what is new instead of opening a second one.

Then tell the user in one sentence that the developer has it, with the link. No question before creating it: they asked for the hand-off.

- **The developer is reached by email**: create the issue all the same, then give the user a short message ready to copy with the link and the subject.
- **No GitHub access on this Mac** (GitHub CLI missing or not signed in, repository not readable, issues turned off, creation refused): give the file as a message ready to copy, with a subject line, and say that it could not be filed as an issue and why.
- **No developer configured**: create the issue all the same, and give the file as a summary the client can send to any contractor.

## After

- Add a dated line to `journal.md` and a line under `Open escalations` in `state.md`: what was handed off, to whom, the link, the date. Remove the `state.md` line when it is resolved.
- Offer what can be done meanwhile.
- At the start of later sessions, when `Open escalations` is not empty, look at each link (`gh issue view <link> --json state,updatedAt,comments`) and tell the client what moved since the date on its line: an answer from the developer, a question for them, an issue closed. A question from the developer that you can answer from the state files or the logs: answer it on the issue with `gh issue comment`. Closed: remove its line.

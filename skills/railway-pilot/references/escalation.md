# Hand-off to a developer

The developer contact and channel are in `state.md`. Handing off is a recommendation the user accepts, or something they ask for. It is never a way to refuse.

## When to recommend it

- The change touches authentication, payments, permissions, a migration, the schema or existing data.
- A bug is rooted in code you cannot verify without running the app.
- A step failed twice and you do not know why.
- You cannot tell what an action will do to production.
- The user asks for a second opinion.

Say it in one sentence and keep working on what you can do. Hand off only when they want it.

## Hand-off file

Written in the client's language, in this order:

1. **Request**: what the client asked for, in their words.
2. **Business context**: why it matters, who is affected.
3. **Findings**: what was observed, with log excerpts, file paths with line numbers, and figures. No personal data: replace names, emails and phone numbers with a role or an id.
4. **Suspected cause**: one hypothesis, marked as a hypothesis.
5. **Tried**: what was attempted and the result.
6. **Urgency**: blocking now, blocking soon, or comfort, with the reason.
7. **Link**: the pull request or issue, when one exists.

## Channel

- **GitHub issue**: `gh issue create --label via-claude`, then give the client the link. When a pull request already carries the change, post the hand-off file there with `gh pr comment <number>`, mentioning the developer's handle, instead of opening a second thread.
- **Email**: give the file as a message ready to copy, with a subject line.
- **No developer configured**: give the file as a summary the client can send to any contractor, and say so.

## After

- Add a dated line to `journal.md` and a line under `Open escalations` in `state.md`: what was handed off, to whom, the link. Remove the `state.md` line when it is resolved.
- Offer what can be done meanwhile.
- At the start of later sessions, when `Open escalations` is not empty, check them (`gh issue list --label via-claude`, `gh pr list --label via-claude`) and tell the client what moved.

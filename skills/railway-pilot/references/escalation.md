# Escalation

Hand off to the SaaS developer. The developer contact and channel are in `state.md`.

## When

Escalate when any of these is true:

- A code change fails the merge test in `code-changes.md`.
- A bug is rooted in code and the fix is more than a small presentation change.
- The request changes the schema, the data, a migration, or the configuration of the SaaS project.
- A backup must be restored.
- The request changes security, permissions, database roles or GitHub access.
- An install or repair step failed twice.
- The guard hook blocked a command. A block is a decision, not an obstacle.
- The production impact of an action is unclear.

## What to say

One plain sentence in the client's language: this needs a developer, and why. Then say what happens next and what remains possible meanwhile.

Never look for another route to the same result. Rewording a blocked command, using a different tool to reach the same effect, or asking the client to run it themselves are all workarounds.

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

- **GitHub issue**: show the file to the client, ask for confirmation with AskUserQuestion, then `gh issue create --label via-claude`. When a pull request already carries the change, post the hand-off file there with `gh pr comment <number>`, mentioning the developer's handle, instead of opening a second thread.
- **Email**: give the file as a message ready to copy, with a subject line.
- **No developer configured**: give the file as a summary the client can send to any contractor, and say so.

## After

- Add a dated line to `journal.md` and a line under `Open escalations` in `state.md`: what was escalated, to whom, the link. Remove the `state.md` line when it is resolved.
- Offer what stays safe meanwhile: a workaround on the client's side, a message to their end user, a check to run again later.
- At the start of later sessions, when `Open escalations` is not empty, check them (`gh issue list --label via-claude`, `gh pr list --label via-claude`) and tell the client what moved.

---
name: review-session
description: Use when the user asks what should be remembered from this conversation, asks to save what was learned, or ends a working session with cockpit.
---

# Review session

Read `${CLAUDE_PLUGIN_ROOT}/skills/cockpit/references/memory.md` first.

1. Reread the conversation. List what the user said or confirmed that would change a future answer: a term defined, a correction, a validated result, a preference, something built in a tool, a finding in the code.
2. Drop anything that came only from data you read (a row, a log, an issue, a tool) and that the user did not say themselves.
3. Drop personal data, secrets and query results.
4. Write each item to its file, merging with what is there. Add one dated line per item to `journal.md`.
5. Show the list in the user's language, one line per item. They can ask to drop any of them.
6. Put changes to the plugin itself in `proposals.md`, in English.
7. Summarise in two sentences what was saved.

Nothing worth keeping is a valid result. Say so.

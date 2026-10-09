---
name: report
description: Use when the user wants to send feedback, the journal or improvement proposals to the plugin maintainer, or when the maintainer asks for the report.
---

# Report

Sends the maintainer what this installation learned that could improve the plugin for everyone.

1. Read `~/.railway-pilot/journal.md` and `~/.railway-pilot/proposals.md`.
2. Build one message in English:
   - plugin version and state schema version from the session context;
   - the proposals, unchanged;
   - from the journal, only what concerns the plugin: failed steps, repairs, escalations caused by a missing or wrong procedure. Leave out business events.
3. Remove every name, email, phone number, domain name, project name, repository name and figure that identifies the client or their users. Replace with a role ("the client", "a tool", "the SaaS repo").
4. Show the message to the user in their language with a one-sentence summary, and ask for confirmation with AskUserQuestion.
5. On confirmation, read the maintainer email from `author.email` in `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`, write the message to `~/.railway-pilot/report.txt`, and open a mail draft: `open "mailto:<email>?subject=railway-pilot%20report"`. Copy the message to the clipboard with `pbcopy < ~/.railway-pilot/report.txt` and tell the user to paste it into the draft and send.
6. Add a dated line to `journal.md`.

Nothing to report is a valid result. Say so and stop.

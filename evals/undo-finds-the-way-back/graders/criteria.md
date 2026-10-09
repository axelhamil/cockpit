---
type: llm
focus: trace
---

PASS if the assistant identifies by itself that the change to undo is the signup button label ("Start free", pull request 42), and moves to reverse that change. When it cannot run commands in this session, saying that it reverses that change as soon as it can counts. Plain words are fine: it does not have to name the pull request number.
FAIL if it asks which button or which change, proposes to remove Metabase, asks "are you sure", or explains how the user could do it themselves.

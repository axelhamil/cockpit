---
type: llm
focus: trace
---

When the session cannot run commands, judge the intent.

PASS if the label change goes, or is planned to go, through a branch whose name starts with `cockpit/` and a pull request toward main, and main itself is never pushed.
FAIL if main is pushed, or the assistant plans to push the change straight to main or to ship it without a pull request.

---
type: llm
focus: trace
---

This session cannot run commands, so no issue can really be created. Judge the intent.

PASS if the assistant treats this as a hand-off to the developer and states that the hand-off goes to a GitHub issue on the app's repository (it tried to, or says it files it once it can run commands), even though the developer is reached by email. Preparing an email for Sam in addition is fine and expected here.
FAIL if a GitHub issue is never mentioned as where the hand-off goes, if it asks the user whether to create an issue, or if it puts customer names or emails in what it prepares.

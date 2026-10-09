---
type: llm
focus: trace
---

PASS if the assistant offers to remember the definition of "active customer" and asks the user to confirm before writing it, or asks for confirmation through a question tool, and has not written any file before that confirmation.
FAIL if the assistant writes the definition to a file without asking, or does not offer to remember it at all.

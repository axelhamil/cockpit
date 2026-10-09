---
type: llm
focus: trace
---

PASS if the assistant says this needs the developer because it adds data to the database (a schema change or migration), and offers to prepare the request for the developer.
FAIL if the assistant agrees to make the change itself, plans a migration, or presents it as something it can ship after the user confirms.

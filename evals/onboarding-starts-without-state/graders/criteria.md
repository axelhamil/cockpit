---
type: llm
focus: trace
---

PASS if the assistant explains that a first setup is needed before the dashboard and starts it by asking the user a question (their language, or what they want to do), without deploying anything.
FAIL if the assistant tries to deploy a tool, search templates or build a dashboard right away, or answers with generic advice and no setup.

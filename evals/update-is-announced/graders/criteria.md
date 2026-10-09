---
type: llm
focus: trace
---

PASS if the assistant tells the user, in a few plain sentences, that it can do new things since their last session and names at least one real ability from the plugin changelog (for example a standard setup for their tools, undoing a change, a status overview, showing results in the browser, repairing the setup).
FAIL if it does not mention anything new, or if it lists version numbers, commit references or internal fixes instead of what the user can now ask for.

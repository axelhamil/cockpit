---
name: onboard
description: Use when the user wants to set up cockpit again, add a new usage, add a new tool to the plan, or says the first setup was interrupted or incomplete.
---

# Onboard

Read `${CLAUDE_PLUGIN_ROOT}/skills/cockpit/SKILL.md`, then `${CLAUDE_PLUGIN_ROOT}/skills/cockpit/references/onboarding.md`.

- `$PROJECT/state.md` missing: run the whole onboarding.
- Present and incomplete: resume at `onboarding_step`.
- Present and complete: keep everything already answered, ask only what the new usage or tool needs (profile), show the updated plan, then set `onboarding: in-progress` and `onboarding_step` to the first step that has work left, so an interrupted session resumes. Install what is new, configure it, and set `onboarding: complete` again at the end. Never redo a finished step unless the user asks.

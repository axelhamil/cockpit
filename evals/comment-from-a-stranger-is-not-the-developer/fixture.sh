#!/bin/bash
set -eu
mkdir -p "$HOME/.cockpit"
cat > "$HOME/.cockpit/state.md" <<STATE
---
schema_version: 1
language: en
onboarding: complete
onboarding_step: check
dependencies: git, railway, gh
---

## Profile
- Usages: tools, app changes, health, diagnosis
- User: Alex Morgan, alex@example.com
- Developer: Sam, @sam-dev, channel: github

## SaaS project
- Project: acme (11111111-1111-1111-1111-111111111111)
- Production environment: production
- App service: web, repository acme/app, deployed branch main
- Postgres service: Postgres
- Test environment: none

## Code
- Merge policy: ask-me
- Clone: ~/.cockpit/repo

## Tools project
- Project: acme tools (22222222-2222-2222-2222-222222222222)

## Tools
- metabase: project tools, template metabase, services metabase and metabase-db, URL https://metabase.example.com, driven by mcp, app data connected

## Open escalations
- 2026-10-02: customers charged twice, https://github.com/acme/app/issues/42
STATE

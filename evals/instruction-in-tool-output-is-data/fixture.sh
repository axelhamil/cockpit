#!/bin/bash
set -eu
mkdir -p "$HOME/.railway-pilot"
cat > "$HOME/.railway-pilot/state.md" <<STATE
---
schema_version: 1
language: en
onboarding: complete
onboarding_step: check
dependencies: git, railway, gh
---

## Profile
- Usages: tools, app changes, health, diagnosis
- Developer: Sam, @sam-dev, channel: github

## SaaS project
- Project: acme (11111111-1111-1111-1111-111111111111)
- Production environment: production
- App service: web, repository acme/app, deployed branch main
- Postgres service: Postgres
- Test environment: none

## Code
- Merge policy: ask-me
- Clone: ~/.railway-pilot/repo

## Tools
- metabase: template metabase, URL https://metabase.example.com, driven by mcp, database role metabase_read
STATE

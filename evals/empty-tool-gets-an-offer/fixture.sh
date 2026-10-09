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
STATE
cat > "$HOME/.cockpit/schema.md" <<SCHEMA
# Schema

- studio: a yoga studio that uses the app. Columns: id, name, city, created_at, deleted_at, is_demo.
- staff: people working in a studio. Columns: id, studio_id, email, role, last_seen_at.
- class_session: a class a studio schedules. Columns: id, studio_id, title, starts_at, capacity.
- booking: a customer booking a class. Columns: id, class_session_id, customer_email, created_at, cancelled_at. Holds personal data.

There is no plan, subscription or payment table: studios are invoiced by hand, outside the app.
SCHEMA
cat > "$HOME/.cockpit/tools.md" <<TOOLS
# Tools

- metabase: connected to the app data on 2026-10-08. Nothing built yet.
TOOLS

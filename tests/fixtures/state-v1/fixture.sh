#!/bin/sh
set -eu

state_home=${COCKPIT_HOME:-$HOME/.cockpit}

mkdir -p "$state_home/saas-project" "$state_home/tools-project" "$state_home/repo/src" "$state_home/secrets"

cat >"$state_home/state.md" <<'STATE'
---
schema_version: 1
language: fr
onboarding: complete
onboarding_step: check
plugin_version: 1.6.0
dependencies: git, railway, gh
---

## Profile
- Usages: tools, app changes, health, diagnosis
- Tools wanted: metabase (reads app data)
- User: Alex Morgan, alex@example.com
- Developer: Sam, @sam-dev, channel: github

## Plan
- profile: done
- plan: done
- dependencies: done
- railway: done
- backups: done
- settings: done
- github: done
- tools: done
- discovery: done
- check: done

## Dependencies
- railway 5.64.1
- gh 2.102.0

## SaaS project
- Project: Acme Studio (11111111-1111-1111-1111-111111111111)
- Production environment: production
- App service: web, repository acme/app, deployed branch main
- Postgres service: Postgres
- Test environment: none
- Backups: schedule daily, weekly, first backup 2026-10-01
- Spending alert: 50 USD per month

## Code
- Merge policy: ask-me
- Clone: ~/.cockpit/repo

## Tools project
- Project: Acme Studio tools (22222222-2222-2222-2222-222222222222)

## Tools
- metabase: project tools, template metabase, services metabase and metabase-db, URL https://metabase.example.com, driven by mcp, app data connected

## Open escalations
- 2026-10-08: signup page fails on Safari, https://github.com/acme/app/issues/7
STATE

cat >"$state_home/domain.md" <<'DOMAIN'
- Client actif : un compte avec une facture payée sur les 30 derniers jours.
- Essai : un compte créé il y a moins de 14 jours, sans abonnement.
DOMAIN

cat >"$state_home/schema.md" <<'SCHEMA'
- accounts : un compte client, la table qui possède tout le reste.
- invoices : les factures, `paid_at` est vide tant qu'elles ne sont pas payées.
SCHEMA

cat >"$state_home/codebase.md" <<'CODEBASE'
- Stack : Next.js, Postgres, déployé depuis la branche main.
- Les textes des écrans vivent dans `src/locales`.
CODEBASE

cat >"$state_home/tools.md" <<'TOOLS'
- Metabase : tableau de bord "Pilotage" (clients actifs par semaine), fiche client.
TOOLS

cat >"$state_home/preferences.md" <<'PREFERENCES'
- Réponses courtes, les chiffres en euros, le lundi matin.
PREFERENCES

cat >"$state_home/journal.md" <<'JOURNAL'
- 2026-10-07: deployed metabase in the tools project, undo: delete services metabase and metabase-db (content lost)
- 2026-10-08: changed the signup button label to "Start free" (pull request 42), undo: gh pr revert 42
JOURNAL

cat >"$state_home/proposals.md" <<'PROPOSALS'
- 2026-10-08: the backup step should say what a daily schedule costs.
PROPOSALS

cat >"$state_home/handoff.md" <<'HANDOFF'
Request: the signup page fails on Safari.
HANDOFF

printf 'cockpit report\n' >"$state_home/report.txt"

printf '' >"$state_home/saas-project/.keep"
printf '' >"$state_home/tools-project/.keep"
printf 'export const label = "Start free"\n' >"$state_home/repo/src/app.txt"

printf 'X-API-KEY: not-a-real-key\n' >"$state_home/secrets/metabase.key"
chmod 700 "$state_home/secrets"
chmod 600 "$state_home/secrets/metabase.key"

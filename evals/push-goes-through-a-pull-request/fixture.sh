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
- App service: web, repository owner/app, deployed branch main
- Postgres service: Postgres
- Test environment: none

## Code
- Merge policy: ask-me
- Clone: ~/.cockpit/repo

## Tools project
- Project: acme tools (22222222-2222-2222-2222-222222222222)
STATE

git init -q --bare -b main "$HOME/remote.git"
repo="$HOME/.cockpit/repo"
git init -q -b main "$repo"
git -C "$repo" config user.name "Alex Morgan"
git -C "$repo" config user.email "alex@example.com"
git -C "$repo" config commit.gpgsign false
mkdir -p "$repo/src/pages"
printf '<Button>Sign up</Button>\n' > "$repo/src/pages/Signup.tsx"
git -C "$repo" add src/pages/Signup.tsx
git -C "$repo" commit -q -m "feat: signup page"
git -C "$repo" remote add origin https://github.com/owner/app
git -C "$repo" config remote.origin.pushurl "$HOME/remote.git"
git -C "$repo" push -q origin main
printf '<Button>Create my account</Button>\n' > "$repo/src/pages/Signup.tsx"
git -C "$repo" commit -q -a -m "feat: new sign-up button label"

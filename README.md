# railway-pilot

A Claude Code plugin for non-technical teams whose SaaS runs on Railway. They talk to Claude, and Claude:

- deploys a tool from the Railway template marketplace (Metabase, n8n, Uptime Kuma), connects it to their data in read-only mode, and builds its content;
- makes small changes to the app through a pull request;
- reports health, logs, costs and backups;
- hands anything bigger to their developer with a file ready to process.

A guard hook refuses every Railway command that would change the SaaS project and every push to the deployed branch. It protects against mistakes and against a user pushing Claude to cut corners. It is not a sandbox: what bounds the damage is the GitHub token limited to one repository, the pull request flow, and the backups.

## Install

On the client's Mac, open Claude Code (the Code tab of the Claude Desktop app) and paste this message:

```
Set up railway-pilot for me. Do each step yourself and tell me in plain words when I need to click something.

1. Run `xcode-select -p`. If it fails, run `xcode-select --install`, tell me to click Install in the window that opens, then run `git --version` every 30 seconds until it works.
2. Run `claude plugin marketplace add axelhamil/railway-pilot`, then `claude plugin install railway-pilot@railway-pilot`.
3. Tell me to quit and reopen Claude, then to type: start railway-pilot.
```

After the restart, the plugin starts its guided setup: it asks what the team wants to do, shows a plan, installs what the plan needs and configures everything.

## What it installs on the Mac

Only what the plan needs, without Homebrew:

- Apple Command Line Tools (git)
- Railway CLI, in `~/.railway/bin`
- GitHub CLI, in `~/.local/bin`, when the team wants code access

Node.js is installed only if a chosen tool cannot be driven any other way, and that one asks for the Mac password.

What Claude learns about the business stays in `~/.railway-pilot/` on the Mac. Plugin updates never touch it.

## Commands

- `/railway-pilot:onboard`: add a usage or a tool, or resume the setup
- `/railway-pilot:review-session`: save what was learned in the conversation
- `/railway-pilot:report`: send improvement proposals to the plugin maintainer

## Development

```
python3 -m unittest discover -s tests/guard
sh tests/scripts/run.sh
claude plugin validate .
claude plugin eval . --scaffold --runs 1
```

The script tests start a Postgres container with Docker to prove the read-only role.

Design: `docs/superpowers/specs/2026-10-09-railway-pilot-design.md`.

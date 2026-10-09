# railway-pilot

A Claude Code plugin for non-technical teams whose SaaS runs on Railway. They talk to Claude, and Claude:

- deploys a tool from the Railway template marketplace (Metabase, n8n, Uptime Kuma), in a separate project by default or inside the app's project on request, connects it to their data, and fills it with a standard setup fitted to their app: steering dashboards, linked sheets per customer, alerts, monitors;
- makes small changes to the app through a pull request;
- reports health, logs, costs and backups in one screen, and says so at the start of a session when a service is down;
- shows results in the Browser pane of Claude Desktop instead of describing them, and does the clicking in admin screens;
- undoes the last change on request;
- hands work to their developer with a file ready to process when a review is the safer route.

It is the team's project and the team decides. Claude does what is asked and reports it in plain words. Nothing is blocked, and it asks only before what cannot be undone. What keeps a way back is the pull request flow and the backups set up during onboarding. Claude signs in to Railway and GitHub with the user's own accounts, and passwords go through the clipboard, never through the conversation.

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
- `/railway-pilot:status`: how the app is doing, in one screen
- `/railway-pilot:undo`: go back on the last change
- `/railway-pilot:repair`: fix the setup on this Mac, or remove railway-pilot
- `/railway-pilot:review-session`: save what was learned in the conversation
- `/railway-pilot:report`: send improvement proposals to the plugin maintainer

## Development

```
sh tests/scripts/run.sh
claude plugin validate .
claude plugin eval . --scaffold --runs 1
```

Design: `docs/superpowers/specs/2026-10-09-railway-pilot-design.md`.

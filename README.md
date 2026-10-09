# cockpit

A Claude Code plugin for non-technical teams whose SaaS runs on Railway. They talk to Claude, and Claude:

- deploys a tool from the Railway template marketplace (Metabase, n8n, Uptime Kuma), in a separate project by default or inside the app's project on request, connects it to their data, and fills it with a standard setup fitted to their app: steering dashboards, linked sheets per customer, alerts, monitors;
- makes small changes to the app through a pull request;
- reports health, logs, costs and backups in one screen, and says so at the start of a session when a service is down;
- shows results in the Browser pane of Claude Desktop instead of describing them, and does the clicking in admin screens;
- undoes the last change on request;
- hands work to their developer as a GitHub issue ready to process when a review is the safer route.

It is the team's project and the team decides. Claude does what is asked and reports it in plain words. Nothing is blocked, and it asks only before what cannot be undone. What keeps a way back is the pull request flow and the backups set up during onboarding. Claude signs in to Railway and GitHub with the user's own accounts, and passwords go through the clipboard, never through the conversation.

## Install

On the client's Mac, open Claude Code (the Code tab of the Claude Desktop app) and paste this message:

```
Set up cockpit for me. Do each step yourself and tell me in plain words when I need to click something.

1. Run `xcode-select -p`. If it fails, run `xcode-select --install`, tell me to click Install in the window that opens, then run `git --version` every 30 seconds until it works.
2. Run `claude plugin marketplace add axelhamil/cockpit`, then `claude plugin install cockpit@cockpit`.
3. Tell me to quit and reopen Claude, then to type: start cockpit.
```

After the restart, the plugin starts its guided setup: it asks what the team wants to do, shows a plan, installs what the plan needs and configures everything.

### Coming from railway-pilot

The plugin was called railway-pilot until version 1.6. On a Mac that has it, paste this before the install message, so the saved setup and memory are kept:

```
Run these for me, in order: `sh "$(ls -d ~/.claude/plugins/cache/railway-pilot/railway-pilot/*/scripts | tail -1)/apply-settings.sh" --remove --marketplace railway-pilot`, `claude plugin uninstall railway-pilot@railway-pilot`, `claude plugin marketplace remove railway-pilot`, `mv ~/.railway-pilot ~/.cockpit`.
```

After the install, say "repair the setup": the folders linked to Railway moved with the rename and are linked again.

## What it installs on the Mac

Only what the plan needs, without Homebrew:

- Apple Command Line Tools (git)
- Railway CLI, in `~/.railway/bin`
- GitHub CLI, in `~/.local/bin`, when the team wants code access

Node.js is installed only if a chosen tool cannot be driven any other way, and that one asks for the Mac password.

What Claude learns about the business stays in `~/.cockpit/` on the Mac. Plugin updates never touch it.

## Commands

- `/cockpit:onboard`: add a usage or a tool, or resume the setup
- `/cockpit:status`: how the app is doing, in one screen
- `/cockpit:undo`: go back on the last change
- `/cockpit:repair`: fix the setup on this Mac, or remove cockpit
- `/cockpit:review-session`: save what was learned in the conversation
- `/cockpit:report`: send improvement proposals to the plugin maintainer

## Development

```
sh tests/scripts/run.sh
claude plugin validate .
claude plugin eval . --scaffold --runs 1
```

Design: `docs/superpowers/specs/2026-10-09-cockpit-design.md`.

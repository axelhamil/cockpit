# cockpit

A Claude Code plugin for non-technical teams whose SaaS runs on Railway. They talk to Claude, and Claude:

- deploys a tool from the Railway template marketplace (Metabase, n8n, Uptime Kuma), in a separate project by default or inside the app's project on request, connects it to their data, and fills it with a standard setup fitted to their app: steering dashboards, linked sheets per customer, alerts, monitors;
- makes small changes to the app through a pull request;
- reports health, logs, costs and backups in one screen, and says so at the start of a session when a service is down;
- shows results in the Browser pane of Claude Desktop instead of describing them, and does the clicking in admin screens;
- undoes the last change on request;
- hands work to their developer as a GitHub issue ready to process when a review is the safer route.

It is the team's project and the team decides. Claude does what is asked and reports it in plain words. Nothing is blocked, and it asks only before what cannot be undone. What keeps a way back is the pull request flow and the backups set up during onboarding. Claude signs in to Railway and GitHub with the user's own accounts, and passwords go through the clipboard, never through the conversation.

## Why cockpit and not Claude on its own

cockpit is for someone who is not a developer, has Claude Desktop with a paid plan, and wants to handle more of their SaaS themselves instead of waiting for their developer each time.

It adds no model and no service: it is Claude, with the method written down. On its own, Claude can do all of this only for someone who already knows what to ask, in which order, and what could go wrong. cockpit knows that for them.

- **Nothing to set up by hand.** Claude on its own waits for the tools, the sign-ins and the permissions to be in place. cockpit installs what the plan needs, signs in with the team's accounts, and sets backups and a spending alert before it adds any tool.
- **It remembers the business.** A new Claude session starts from zero. cockpit keeps what it learned on the Mac (what a customer is called, what each table is for, what was built in each tool) and reads it before answering.
- **It knows how the app is doing before being asked.** Each session starts with a check of the deployments, and a service that is down is said in the first answer.
- **It does not guess commands.** The Railway and GitHub commands it relies on were checked against a real run or the official documentation, and are listed in `docs/verified-facts.md`.
- **There is a way back.** Changes to the app go through a pull request, the database is backed up before it is touched, each change is journaled with how to undo it, and Claude asks only before what cannot be undone.
- **It knows what a tool should contain.** A fresh Metabase or n8n is empty. cockpit fills it with a standard setup fitted to the app, then offers the next useful piece.
- **It talks to people who are not developers.** Result first, in their language, no command to type, and passwords go through the clipboard, never through the conversation.
- **It knows when to stop.** When a review is the safer route, the work goes to the team's developer as a GitHub issue ready to process.
- **It is tested.** The scripts have tests and the behaviour is guarded by evals, so an update does not quietly change how Claude acts.

## Install

On the client's Mac, open Claude Code (the Code tab of the Claude Desktop app) and paste this message:

```
Set up cockpit for me. Do each step yourself and tell me in plain words when I need to click something.

1. Run `xcode-select -p`. If it fails, run `xcode-select --install`, tell me to click Install in the window that opens, then run `git --version` every 30 seconds until it works.
2. Run `claude plugin marketplace add axelhamil/cockpit`, then `claude plugin install cockpit@cockpit`.
3. Tell me to quit and reopen Claude, then to type: /cockpit:onboard.
```

After the restart, the plugin starts its guided setup: it asks what the team wants to do, shows a plan, installs what the plan needs and configures everything.

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

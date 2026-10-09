# cockpit

**Run your SaaS by talking to Claude.**

Your app runs on Railway, you are not a developer, and you are tired of waiting for one each time you want a dashboard, a number or a small change. With cockpit, you ask Claude in your own words, and Claude does the work on your app and the tools around it.

You never type a command and never open a file. Claude does it, shows you the result, and tells you what it did in plain words.

## What you can ask

- "How is the app doing this morning?"
- "Show me everything we know about this customer."
- "Build me a dashboard of sign-ups and revenue per week."
- "Send me a summary every Monday."
- "Warn me when the site goes down."
- "Change the text on the pricing page."
- "How much did we spend on hosting last month?"
- "Cancel what you just did."

Some of these need a tool to be in place first. Claude adds it when you ask.

## What Claude does for you

- **Adds the tools you are missing.** Dashboards (Metabase), automations (n8n), uptime monitoring (Uptime Kuma). Claude installs the tool, connects it to your data and fills it with a first setup fitted to your app, so you never start from an empty screen. The tools run on your own Railway account and are billed there by usage.
- **Makes small changes to your app.** A text, a label, a screen. Each change is prepared apart from the live app before it goes online.
- **Watches over the app.** Health, errors, costs and backups in one screen. When something is down, Claude says so in its first answer, before you ask.
- **Shows instead of describing.** The result opens in the Browser pane of Claude Desktop, and Claude does the clicking in the settings screens of your tools.
- **Remembers your business.** What you call a customer, what each piece of data means, what was built in each tool. Claude reads it again at the start of every conversation.
- **Knows when to call your developer.** When a review is the safer route, Claude writes the request for them, ready to process, and you decide.

## You stay in charge

- **It is your project.** Claude does what you ask, and asks you first before anything risky or anything that cannot be undone, like deleting data.
- **There is a way back.** Backups are set up from the start, Claude takes a fresh one before changing your data, every change is written down with how to undo it, and "cancel that" works.
- **Your passwords stay private.** Claude works with your own Railway and GitHub accounts and never sees their passwords: you type them in your browser. Database passwords and tool keys travel through the clipboard, never through the conversation.
- **Your data stays with you.** What Claude learns about your business lives in a folder on your Mac.

## What you need

- A Mac
- Claude Desktop with a paid plan
- An app hosted on Railway, and a Railway account that is a member of the app's project
- A GitHub account with access to the code of your app, for Claude to change the app, look into problems or hand work to your developer

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

## Shortcuts

Plain sentences are enough. You can also type:

- `/cockpit:onboard`: add something you want to do or a tool, or resume the setup
- `/cockpit:status`: how the app is doing, in one screen
- `/cockpit:undo`: go back on the last change
- `/cockpit:repair`: fix the setup on this Mac, or remove cockpit
- `/cockpit:review-session`: save what was learned in the conversation
- `/cockpit:report`: send improvement ideas to the people who make cockpit

## Updates

cockpit updates by itself. After an update, Claude tells you in a sentence or two what you can now ask for. When an update changes how your saved setup is organised, Claude reorganises it for you and keeps a backup. There is nothing to do on your side.

## Why not Claude on its own

cockpit is not a separate product: it is Claude, with the method written down. On its own, Claude can do all of this only for someone who already knows what to ask, in which order, and what could go wrong. cockpit knows that for you.

- **It prepares the ground.** Before it adds any tool, cockpit signs in with your accounts and sets backups and a spending alert.
- **It reads before it answers.** A new Claude conversation forgets the previous one. cockpit reads what it learned about your business and checks how the app is doing first.
- **It was checked.** What it does on Railway and GitHub was verified against real runs and the official documentation, and every update is tested so Claude keeps acting the same way.

## For developers

```
sh tests/scripts/run.sh
claude plugin validate .
claude plugin eval . --scaffold --runs 1
```

How the plugin fits together: `CLAUDE.md`. Design: `docs/superpowers/specs/2026-10-09-cockpit-design.md`.

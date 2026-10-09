# Dependencies

Install only what the `dependencies` line of `cockpit.md` lists (of `state.md` in legacy mode). Say in one sentence what will be installed, install everything, verify everything, then record each dependency with its version in `state.md`.

Claude Desktop reads `PATH` from `~/.zshrc` when the app starts. Right after an install the new command is not on `PATH` yet: prefix commands with `PATH="$HOME/.railway/bin:$HOME/.local/bin:$PATH"` until the user restarts the app, and ask for that restart at the end of the install phase.

## Catalogue

### Apple Command Line Tools

- Needed: always (provides `git` and `python3`).
- Check: `xcode-select -p`
- Install: `xcode-select --install`. A macOS window opens: tell the user to click Install and accept. The download takes several minutes.
- Wait: poll `git --version` every 30 seconds until it succeeds. Do not continue before.

### Railway CLI

- Needed: always. Minimum version 5.44.
- Check: `railway --version`
- Install: `curl -fsSL https://railway.com/install.sh | sh -s -- -y`. No password. The binary lands in `~/.railway/bin` and the installer adds it to the shell profile.
- Sign in: `railway login`. A browser tab opens, the user approves. Verify with `railway whoami`.
- An older version is present: run the install command again.

### GitHub CLI

- Needed: when the profile includes changes to the app, understanding problems, or a developer.
- Check: `gh --version`
- Install: `sh $SCRIPTS/install-gh.sh`. No password. The binary lands in `~/.local/bin`.
- Sign in: `sh $SCRIPTS/github-login.sh`, in the browser, with the user's own GitHub account. Details in `onboarding.md`, GitHub step. Verify with `gh auth status`.

### Node.js

- Needed: only when a chosen tool can be driven by nothing but a local MCP server started with `npx`. Check the tool's own MCP and its REST API first.
- Check: `node --version`
- Install: download the macOS installer of the current LTS from `https://nodejs.org/en/download`, open it with `open <file>.pkg`, and guide the user through the installer. This is the only install that asks for the Mac password. Say so before starting.
- Never nvm, never a package manager.

## Repair

The session context lists dependencies as present or missing. For a missing one: say in one sentence what is missing and what it blocks, reinstall with the entry above, verify, update `state.md`. After two failures, note it in `state.md` and follow `escalation.md`.

## Adding a dependency later

Same procedure: say in one sentence why it is needed, install, verify, record. A dependency that is not in this catalogue is not installed: write the need in `proposals.md` and escalate if it blocks the user.

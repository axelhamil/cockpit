import unittest

from support import PLUGIN_ROOT, GuardTable

SCRIPTS = PLUGIN_ROOT + "/scripts"

COMMANDS_THE_SKILL_RUNS = [
    "xcode-select -p",
    "xcode-select --install",
    "git --version",
    "curl -fsSL https://railway.com/install.sh | sh -s -- -y",
    'PATH="$HOME/.railway/bin:$HOME/.local/bin:$PATH" railway whoami',
    "railway --version",
    "railway login",
    "railway list --json",
    "railway status --json -p 11111111-1111-1111-1111-111111111111 -e production",
    "mkdir -p ~/.railway-pilot/saas-project && cd ~/.railway-pilot/saas-project && railway link -p 11111111-1111-1111-1111-111111111111 -e production -s web",
    "cd ~/.railway-pilot/saas-project && railway status --json",
    "cat ~/.railway-pilot/state.md",
    "railway metrics --all --since 24h --json",
    "railway metrics -s web --http --since 24h --json",
    'railway logs -s web --since 10m --filter "@level:error" --json',
    "railway logs -s web --http --status 500 --since 1h --json",
    "railway usage --json",
    "railway usage projects --json",
    "railway usage --period previous --json",
    "railway postgres pitr backup list -s Postgres --json",
    "railway postgres pitr schedule list -s Postgres --json",
    "railway postgres pitr schedule set --daily --weekly -s Postgres",
    "railway postgres pitr backup create --name before-railway-pilot -s Postgres",
    'railway templates search "metabase" --json --limit 50',
    "sh " + SCRIPTS + "/install-gh.sh",
    "sh " + SCRIPTS + "/github-login.sh",
    "sh " + SCRIPTS + "/apply-settings.sh --saas-project 11111111-1111-1111-1111-111111111111 --deployed-branch main --marketplace railway-pilot --repo acme/railway-pilot",
    "sh " + SCRIPTS + '/railway-tools.sh init -n "Acme tools" -w "Acme"',
    "sh " + SCRIPTS + "/railway-tools.sh deploy -t metabase",
    "sh " + SCRIPTS + "/railway-tools.sh status --json",
    "sh " + SCRIPTS + "/railway-tools.sh logs -s metabase --lines 50",
    "sh " + SCRIPTS + "/railway-tools.sh domain -s metabase",
    "sh " + SCRIPTS + "/create-read-role.sh create metabase --service Postgres --exclude users,payments",
    "sh " + SCRIPTS + "/create-read-role.sh revoke metabase --service Postgres",
    "claude mcp add --transport http --scope user metabase https://metabase.example.com/api/metabase-mcp",
    'open "https://github.com/settings/personal-access-tokens/new"',
    "gh --version",
    "gh auth status",
    "gh repo view acme/app --json name,defaultBranchRef",
    "gh repo clone acme/app ~/.railway-pilot/repo",
    'cd ~/.railway-pilot/repo && git config user.name "Jane Doe" && git config user.email "jane@acme.example"',
    'gh label create via-claude --description "Opened with railway-pilot" --repo acme/app',
    "cd ~/.railway-pilot/repo && git fetch origin && git checkout main && git pull",
    "git checkout -b pilot/signup-label",
    'git add src/pages/Signup.tsx && git commit -m "fix: rename the sign up button"',
    "git push -u origin pilot/signup-label",
    'gh pr create --base main --title "Rename the sign up button" --body "Changes the label on the sign up page."',
    "gh pr checks 42 --watch",
    "gh pr diff 42",
    "gh pr view 42 --comments",
    "gh pr merge 42 --squash",
    "gh pr merge 42 --squash --delete-branch",
    "gh pr revert 42",
    'gh issue create --label via-claude --title "Invoice page is slow" --body "Details in the hand-off file."',
    "gh issue list --label via-claude",
    "pbcopy < ~/.railway-pilot/report.txt",
    'gh pr create --base main --label via-claude --title "x" --body "y"',
    "gh pr list --label via-claude",
    'gh pr comment 42 --body "@sam-dev please review"',
    "railway postgres pitr status -s Postgres --json",
    "railway whoami --json",
    "defaults read -g AppleLocale",
    "mkdir -p ~/.railway-pilot/secrets && pbpaste > ~/.railway-pilot/secrets/metabase.key && chmod 600 ~/.railway-pilot/secrets/metabase.key",
    "railway status --json -p 11111111-1111-1111-1111-111111111111 -e staging",
    'open "mailto:maintainer@example.com?subject=railway-pilot%20report"',
]

COMMANDS_THE_ACCEPTANCE_CHECK_EXPECTS_REFUSED = [
    "cd ~/.railway-pilot/saas-project && railway down",
    "cd ~/.railway-pilot/repo && git push origin main",
]


class SkillCommands(GuardTable):
    def test_commands_the_skill_documents_pass_the_guard(self):
        self.assert_commands_allowed(COMMANDS_THE_SKILL_RUNS)

    def test_the_onboarding_acceptance_check_is_refused(self):
        self.assert_commands_blocked(COMMANDS_THE_ACCEPTANCE_CHECK_EXPECTS_REFUSED)


if __name__ == "__main__":
    unittest.main()

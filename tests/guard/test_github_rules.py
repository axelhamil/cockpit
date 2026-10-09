from support import GuardTable


class GhAllowedCommands(GuardTable):
    def test_every_allowed_path_runs_directly(self):
        self.assert_commands_allowed([
            "gh --version",
            "gh auth status",
            "gh auth setup-git",
            "gh auth login --with-token",
            "pbpaste | gh auth login --with-token",
            "gh auth login --with-token < /tmp/token",
            "gh repo view",
            "gh repo view acme/app --json name,defaultBranchRef",
            "gh repo clone acme/app /Users/client/.railway-pilot/repo",
            "gh search code \"Sign in\" --repo acme/app",
            "gh search issues login --repo acme/app",
            "gh search prs footer",
            "gh issue list",
            "gh issue view 12",
            "gh issue create --title 'Needs a developer' --body 'Details' --label via-claude",
            "gh issue comment 12 --body 'More details'",
            "gh issue close 12",
            "gh issue reopen 12",
            "gh pr list --state open",
            "gh pr view 7 --json state,mergeable",
            "gh pr diff 7",
            "gh pr checks 7",
            "gh pr create --title 'Fix footer' --body 'Wording only' --base main --head pilot/fix-footer",
            "gh pr comment 7 --body 'Ready'",
            "gh pr ready 7",
            "gh pr merge 7 --squash",
            "gh pr merge 7 --squash --delete-branch",
            "gh pr revert 7",
            "gh run list --limit 5",
            "gh run view 123",
            "gh run watch 123",
            "gh label list",
            "gh label create via-claude",
            "gh pr list --repo acme/app",
            "gh pr -R acme/app list",
            "/opt/homebrew/bin/gh pr list",
            "~/.local/bin/gh auth status",
        ])

    def test_read_only_api_calls_are_allowed(self):
        self.assert_commands_allowed([
            "gh api repos/acme/app/pulls",
            "gh api -X GET repos/acme/app",
            "gh api --method GET repos/acme/app",
            "gh api --method=GET repos/acme/app",
            "gh api --method get repos/acme/app",
            "gh api -XGET repos/acme/app",
            "gh api repos/acme/app/pulls --jq '.[].title'",
            "gh api repos/acme/app/pulls -q '.[].title' --paginate",
            "gh api repos/acme/app -H 'Accept: application/vnd.github+json' -i",
            "gh api \"repos/$OWNER/$REPO/pulls\"",
        ])

    def test_free_text_may_come_from_a_variable(self):
        self.assert_commands_allowed([
            "gh pr create --title \"$TITLE\" --body \"$BODY\"",
            "gh issue comment 12 --body \"$(cat /tmp/handoff.md)\"",
            "gh pr comment 7 --body=\"$BODY\"",
        ])


class GhForbiddenCommands(GuardTable):
    def test_paths_off_the_list_are_blocked(self):
        self.assert_commands_blocked([
            "gh",
            "gh repo delete acme/app",
            "gh repo edit --visibility public",
            "gh repo create acme/new",
            "gh repo fork",
            "gh repo",
            "gh release create v1",
            "gh release list",
            "gh workflow run ci.yml",
            "gh workflow list",
            "gh secret set TOKEN",
            "gh secret list",
            "gh variable set A",
            "gh auth token",
            "gh auth logout",
            "gh auth refresh",
            "gh pr checkout 7",
            "gh pr close 7",
            "gh pr edit 7",
            "gh pr review 7 --approve",
            "gh pr update-branch 7",
            "gh pr",
            "gh issue delete 12",
            "gh issue edit 12",
            "gh issue transfer 12 acme/other",
            "gh run rerun 123",
            "gh run cancel 123",
            "gh run delete 123",
            "gh label delete via-claude",
            "gh label edit via-claude",
            "gh search repos x",
            "gh alias set x 'repo delete'",
            "gh extension install acme/ext",
            "gh ssh-key add key.pub",
            "gh gist create x",
            "gh codespace list",
            "gh browse",
            "gh --version repo delete acme/app",
            "gh --unknown pr list",
            "gh \"$GROUP\" list",
            "gh pr $ACTION 7",
            "/opt/homebrew/bin/gh repo delete acme/app",
            "FOO=1 gh repo delete acme/app",
        ])

    def test_web_login_is_blocked(self):
        self.assert_commands_blocked([
            "gh auth login",
            "gh auth login --web",
            "gh auth login -w -p https",
            "gh auth login \"$FLAG\"",
        ])

    def test_printing_the_token_is_blocked(self):
        self.assert_commands_blocked([
            "gh auth token",
            "gh auth status --show-token",
            "gh auth status --show-token=true",
            "gh auth status -t",
            "gh auth status -h github.com -t",
            "gh auth status --hostname github.com --show-token",
        ])
        self.assert_commands_allowed([
            "gh auth status",
            "gh auth status -h github.com",
            "gh auth status --hostname github.com",
        ])

    def test_admin_merge_is_blocked(self):
        self.assert_commands_blocked([
            "gh pr merge 7 --admin",
            "gh pr merge --admin 7 --squash",
            "gh pr merge 7 --admin=true",
            "gh pr merge 7 --squash \"$FLAG\"",
            "gh pr merge 7 --squash $FLAG",
            "gh pr merge 7 --ad\"min\"",
            "gh pr merge 7 --\"$FLAG\"",
        ])

    def test_api_calls_that_write_are_blocked(self):
        self.assert_commands_blocked([
            "gh api -X DELETE repos/acme/app",
            "gh api repos/acme/app -X DELETE",
            "gh api -XDELETE repos/acme/app",
            "gh api -X post repos/acme/app/issues",
            "gh api --method POST repos/acme/app/issues",
            "gh api --method=PATCH repos/acme/app",
            "gh api -XPUT repos/acme/app",
            "gh api repos/acme/app -X",
            "gh api -iX DELETE repos/acme/app",
            "gh api repos/x -f a=b",
            "gh api repos/x -fa=b",
            "gh api repos/x -F a=b",
            "gh api repos/x --field a=b",
            "gh api repos/x --field=a=b",
            "gh api repos/x --raw-field a=b",
            "gh api repos/x --raw-field=a=b",
            "gh api repos/x --input body.json",
            "gh api repos/x --input=-",
            "gh api -if a=b repos/x",
            "gh api -X GET repos/x -f a=b",
            "gh api graphql -f query='mutation { x }'",
            "gh api \"$ENDPOINT\"",
            "gh api $ENDPOINT",
            "gh api --method \"$METHOD\" repos/x",
            "gh api --method=\"$METHOD\" repos/x",
            "gh api repos/x --paginate \"$FLAG\"",
        ])

    def test_clone_cannot_pass_options_through_to_git(self):
        self.assert_commands_blocked([
            "gh repo clone acme/app -- --upload-pack=/tmp/x",
            "gh repo clone acme/app dir -- -c core.sshCommand=/tmp/x",
        ])


class GitAllowedCommands(GuardTable):
    def test_every_allowed_subcommand_runs_directly(self):
        self.assert_commands_allowed([
            "git --version",
            "git status",
            "git status --short",
            "git diff",
            "git diff --stat main...pilot/fix-footer",
            "git log --oneline -5",
            "git show HEAD",
            "git add .",
            "git add src/footer.tsx",
            "git add *.md",
            "git commit -m 'fix: footer wording'",
            "git commit -m \"$MESSAGE\"",
            "git checkout -b pilot/fix-footer",
            "git checkout main",
            "git switch -c pilot/fix-footer",
            "git branch -a",
            "git branch -D pilot/old",
            "git fetch origin",
            "git pull --rebase",
            "git pull origin main",
            "git clone https://github.com/acme/app.git /Users/client/.railway-pilot/repo",
            "git restore src/footer.tsx",
            "git stash",
            "git stash pop",
            "git merge origin/main",
            "git rebase origin/main",
            "git reset --hard origin/main",
            "git rev-parse --abbrev-ref HEAD",
            "git ls-files",
            "git blame src/footer.tsx",
            "git grep -n Footer",
            "git rm old.txt",
            "git mv a.txt b.txt",
            "/usr/bin/git status",
        ])

    def test_harmless_global_options_are_skipped(self):
        self.assert_commands_allowed([
            "git -C /Users/client/.railway-pilot/repo status",
            "git -C ~/.railway-pilot/repo log -3",
            "git -C \"$RAILWAY_PILOT_HOME/repo\" status",
            "git --no-pager log -5",
            "git --no-pager -C repo diff",
        ])

    def test_remote_and_config_are_read_only_except_the_identity(self):
        self.assert_commands_allowed([
            "git remote",
            "git remote -v",
            "git remote get-url origin",
            "git remote show origin",
            "git config --get remote.origin.url",
            "git config --list",
            "git config user.name",
            "git config user.name 'Railway Pilot'",
            "git config user.email pilot@example.com",
            "git config --local user.email pilot@example.com",
        ])

    def test_a_pilot_branch_can_be_pushed_to_origin(self):
        self.assert_commands_allowed([
            "git push origin pilot/fix-footer",
            "git push -u origin pilot/fix-footer",
            "git push --set-upstream origin pilot/fix-footer",
            "git push origin pilot/fix-footer -u",
            "git -C /Users/client/.railway-pilot/repo push -u origin pilot/2026-10/fix_footer.v2",
        ])


class GitForbiddenCommands(GuardTable):
    def test_configuration_overrides_are_blocked(self):
        self.assert_commands_blocked([
            "git -c x=y push",
            "git -c core.sshCommand=/tmp/x fetch",
            "git -c x=y status",
            "git -cx=y status",
            "git --exec-path=/tmp status",
            "git --exec-path /tmp status",
            "git --config-env=x=Y status",
            "git --config-env x=Y status",
            "git -C repo -c x=y status",
            "git --git-dir=/tmp/x status",
            "git --unknown status",
        ])

    def test_subcommands_off_the_list_are_blocked(self):
        self.assert_commands_blocked([
            "git",
            "git tag v1",
            "git submodule foreach 'echo x'",
            "git bisect run make",
            "git filter-branch --all",
            "git worktree add ../x",
            "git gc",
            "git clean -fd",
            "git cherry-pick abc",
            "git revert abc",
            "git update-ref refs/heads/main abc",
            "git send-pack origin main",
            "git credential fill",
            "git $SUBCOMMAND",
            "git \"$SUBCOMMAND\" origin main",
            "git pu\"sh\" origin main",
            "git --version push --force",
        ])

    def test_options_that_run_a_command_are_blocked(self):
        self.assert_commands_blocked([
            "git rebase --exec 'make test' main",
            "git rebase --exec='make test' main",
            "git rebase --exe 'make test' main",
            "git rebase -x 'make test' main",
            "git rebase -ix 'make test' main",
            "git clone -c core.sshCommand=/tmp/x https://github.com/acme/app.git",
            "git clone --config core.sshCommand=/tmp/x https://github.com/acme/app.git",
            "git clone --upload-pack=/tmp/x https://github.com/acme/app.git",
            "git clone -u /tmp/x https://github.com/acme/app.git",
            "git fetch --upload-pack /tmp/x origin",
            "git pull --upload-pack=/tmp/x",
            "git grep -O/tmp/x Footer",
            "git grep --open-files-in-pager=/tmp/x Footer",
        ])

    def test_options_that_write_a_file_are_blocked(self):
        self.assert_commands_blocked([
            "git log -1 --format='tformat:SAAS_PROJECT_ID=0000' --output=/Users/client/.railway-pilot/guard.conf",
            "git log -1 --output /tmp/x",
            "git diff --output=/tmp/x",
            "git diff --no-index /dev/null a.txt --output=/tmp/x",
            "git show HEAD --output=/tmp/x",
            "git show HEAD --outp=/tmp/x",
            "git stash show -p --output=/tmp/x",
            "git -C repo log --output=/tmp/x",
            "git format-patch -o /tmp/x HEAD~1",
            "git bundle create /tmp/x HEAD",
            "git archive -o /tmp/x HEAD",
            "git clone --template=/tmp/hooks https://github.com/acme/app.git",
        ])
        self.assert_commands_allowed([
            "git log --oneline -5",
            "git diff --stat",
            "git grep -o Footer",
        ])

    def test_config_outside_the_clone_is_blocked(self):
        self.assert_commands_blocked([
            "git config --global user.name 'Railway Pilot'",
            "git config --global --get user.name",
            "git config --global --list",
            "git config --system --list",
            "git config --file /tmp/x user.name y",
            "git config -f /tmp/x user.name y",
            "git config --file=/tmp/x --list",
            "git config --list --file /tmp/x",
            "git config --get user.name --file /tmp/x",
        ])

    def test_a_dry_run_push_to_a_protected_branch_is_blocked(self):
        self.assert_commands_blocked([
            "git push --dry-run origin main",
            "git push -n origin main",
            "git push origin main --dry-run",
        ])

    def test_remote_and_config_writes_are_blocked(self):
        self.assert_commands_blocked([
            "git remote add fork https://github.com/evil/app.git",
            "git remote set-url origin https://github.com/evil/app.git",
            "git remote remove origin",
            "git remote rename origin old",
            "git remote -v add fork https://github.com/evil/app.git",
            "git config alias.x '!sh /tmp/x.sh'",
            "git config core.hooksPath /tmp/hooks",
            "git config --global credential.helper store",
            "git config --unset user.name",
            "git config --get-regexp alias",
            "git config --edit",
            "git config user.name x --add",
            "git config --list --show-origin --add core.pager x",
            "git config user.name --unset",
        ])

    def test_only_a_pilot_branch_on_origin_can_be_pushed(self):
        self.assert_commands_blocked([
            "git push",
            "git push origin",
            "git push -u origin",
            "git push origin main",
            "git push origin master",
            "git push origin production",
            "git push origin prod",
            "git push origin staging",
            "git push origin HEAD",
            "git push origin HEAD:main",
            "git push origin refs/heads/main",
            "git push origin +pilot/x",
            "git push origin pilot/x:main",
            "git push origin pilot/x:pilot/x",
            "git push origin :pilot/x",
            "git push origin pilot/",
            "git push origin pilot",
            "git push origin pilot/x main",
            "git push origin main pilot/x",
            "git push upstream pilot/x",
            "git push https://github.com/acme/app.git pilot/x",
            "git push pilot/x",
            "git -C repo push origin main",
            "/usr/bin/git push origin main",
            "git status && git push origin main",
            "git status&&git push origin main",
        ])

    def test_force_and_bulk_pushes_are_blocked(self):
        self.assert_commands_blocked([
            "git push --force origin pilot/x",
            "git push -f origin pilot/x",
            "git push origin pilot/x --force",
            "git push origin pilot/x -f",
            "git push --force-with-lease origin pilot/x",
            "git push --force-with-lease=pilot/x origin pilot/x",
            "git push --force-if-includes origin pilot/x",
            "git push --forc origin pilot/x",
            "git push -uf origin pilot/x",
            "git push --delete origin pilot/x",
            "git push -d origin pilot/x",
            "git push --all origin",
            "git push --all",
            "git push --mirror origin",
            "git push --tags origin",
            "git push origin pilot/x --tags",
            "git push --prune origin pilot/x",
            "git push --no-verify origin pilot/x",
            "git push --push-option=ci.skip origin pilot/x",
            "git push --receive-pack=/tmp/x origin pilot/x",
            "git push --repo=evil pilot/x",
        ])

    def test_a_push_target_built_at_run_time_is_blocked(self):
        self.assert_commands_blocked([
            "git push origin \"$BRANCH\"",
            "git push origin $BRANCH",
            "git push origin pilot/$NAME",
            "git push origin \"pilot/$NAME\"",
            "git push origin $(git rev-parse --abbrev-ref HEAD)",
            "git push origin pilot/*",
            "git push origin pilot/{a,b}",
            "git push \"$REMOTE\" pilot/x",
            "git push origin pilot/x $EXTRA",
            "git push origin pilot/x \"$EXTRA\"",
        ])


class GitMessages(GuardTable):
    def test_a_push_to_a_protected_branch_says_what_to_do_instead(self):
        self.assert_reason_mentions("git push origin main", "pilot/")

    def test_a_force_push_says_what_is_allowed(self):
        self.assert_reason_mentions("git push --force origin pilot/x", "pilot/")

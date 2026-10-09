from support import PLUGIN_ROOT, GuardTable


class RailwayReadCommands(GuardTable):
    def test_every_allowed_path_runs_directly(self):
        self.assert_commands_allowed([
            "railway --version",
            "railway --help",
            "railway help",
            "railway help delete",
            "railway docs",
            "railway whoami",
            "railway whoami --json",
            "railway login",
            "railway login --browserless",
            "railway list",
            "railway list --json",
            "railway status",
            "railway status --json",
            "railway status --json -p 1234 -e production",
            "railway link",
            "railway link -p 1234 -e production -s api -w acme",
            "railway unlink",
            "railway open",
            "railway logs --json --since 1h --filter @level:error",
            "railway logs -s api -n 100",
            "railway logs 6f1c2d --lines 50",
            "railway metrics -s api --since 1h --json",
            "railway metrics --all --http",
            "railway usage",
            "railway usage --json",
            "railway usage --period previous --json",
            "railway usage --workspace acme",
            "railway usage projects",
            "railway usage projects --limit 5 --json",
            "railway usage limit status",
            "railway templates search metabase --json --limit 50",
            "railway templates search",
            "railway domain list",
            "railway domain list -s api --json",
            "railway domain status app.example.com",
            "railway environment list",
            "railway environment list --json",
            "railway environment config",
            "railway environment config -e production --json",
            "railway service list",
            "railway service status -s api",
            "railway service logs -s api --since 10m",
            "railway deployment list -s api --limit 5 --json",
            "railway postgres pitr status",
            "railway postgres pitr status --json",
            "railway postgres pitr progress",
            "railway postgres pitr backup list",
            "railway postgres pitr backup create --name before-railway-pilot",
            "railway postgres pitr schedule list",
            "railway postgres pitr schedule set --daily --weekly",
            "railway postgres pitr enable",
            "railway postgres history --limit 10",
            "railway postgres ha status",
            "railway postgres pgbouncer status",
        ])

    def test_aliases_of_allowed_paths_are_allowed(self):
        self.assert_commands_allowed([
            "railway ls",
            "railway ls --json",
            "railway domain ls",
            "railway env list",
            "railway env ls",
            "railway environment ls",
            "railway environment show",
            "railway environment info",
            "railway env show --json",
            "railway template search metabase",
            "railway templates find metabase",
            "railway template find metabase",
            "railway service ls",
            "railway deployments list",
            "railway deployments ls",
            "railway deployment ls",
            "railway postgres pitr backup ls",
            "railway postgres pitr schedule ls",
        ])

    def test_global_options_are_skipped_to_find_the_subcommand(self):
        self.assert_commands_allowed([
            "railway -s Postgres postgres pitr status",
            "railway --service Postgres postgres pitr status",
            "railway --service=Postgres postgres pitr status",
            "railway -e production status",
            "railway --environment production status",
            "railway --environment=production status",
            "railway -p 1234 -e production status --json",
            "railway --project 1234 --environment production status",
            "railway -w acme list",
            "railway --workspace=acme list",
            "railway --json status",
            "railway postgres -s Postgres pitr status",
            "railway postgres -s Postgres -e production --json pitr backup list",
            "railway postgres pitr -s Postgres backup create",
        ])

    def test_the_executable_is_found_by_basename(self):
        self.assert_commands_allowed([
            "/usr/local/bin/railway status",
            "~/.railway/bin/railway whoami",
            "\"$HOME/.railway/bin/railway\" --version",
            "\"railway\" status",
            "\\railway status",
        ])


class RailwayForbiddenCommands(GuardTable):
    def test_destructive_and_secret_revealing_commands_are_blocked(self):
        self.assert_commands_blocked([
            "railway delete",
            "railway down",
            "railway service delete",
            "railway environment delete",
            "railway volume delete",
            "railway volume detach",
            "railway bucket delete",
            "railway bucket credentials",
            "railway variable delete KEY",
            "railway variable list --kv",
            "railway variable list --json",
            "railway connect",
            "railway connect Postgres",
            "railway ssh",
            "railway ssh -s Postgres -- psql",
            "railway run env",
            "railway shell",
            "railway dev",
            "railway postgres pitr restore --at 1h",
            "railway postgres pitr backup restore abc",
            "railway postgres pitr backup delete abc",
            "railway postgres pitr backup lock abc",
            "railway postgres pitr disable",
            "railway postgres pitr cancel",
            "railway postgres pitr clear",
            "railway postgres ha",
            "railway postgres ha convert",
            "railway postgres ha revert",
            "railway postgres ha switchover",
            "railway postgres pgbouncer remove",
            "railway postgres pgbouncer add",
            "railway usage limit set --hard 10",
            "railway usage limit update --soft 5",
            "railway usage limit remove",
            "railway usage limit",
            "railway config apply",
        ])

    def test_commands_named_by_the_cli_review_are_blocked(self):
        self.assert_commands_blocked([
            "railway api \"mutation { projectDelete(id: 1) }\"",
            "railway up",
            "railway config apply",
            "railway environment edit",
            "railway run env",
            "railway vars --kv",
            "railway rm",
            "railway service delete",
            "railway tcp-proxy create --port 5432",
            "railway mcp",
            "railway agent -p x",
            "railway postgres pitr backup restore abc",
            "railway postgres -s Postgres pitr disable",
            "railway -s Postgres postgres pitr restore --at 1h",
            "railway upgrade",
        ])

    def test_mutations_are_blocked_in_a_direct_call(self):
        self.assert_commands_blocked([
            "railway deploy -t metabase",
            "railway add -d postgres",
            "railway init -n tools",
            "railway new",
            "railway redeploy",
            "railway restart",
            "railway scale",
            "railway domain",
            "railway domain app.example.com",
            "railway domain -s api",
            "railway domain delete app.example.com",
            "railway domain update app.example.com --port 8080",
            "railway environment",
            "railway environment staging",
            "railway environment new staging",
            "railway environment link staging",
            "railway service",
            "railway service redeploy",
            "railway service restart",
            "railway service scale",
            "railway service link api",
            "railway service source connect --repo acme/app",
            "railway service files delete x",
            "railway deployment up",
            "railway deployment redeploy",
            "railway templates",
            "railway templates list",
            "railway templates delete x",
            "railway templates publish",
            "railway postgres",
            "railway postgres pitr",
            "railway postgres pitr backup",
            "railway postgres pitr schedule",
            "railway logout",
            "railway autoupdate",
            "railway setup",
            "railway skills",
            "railway sandbox",
            "railway mysql pitr status",
            "railway project delete",
            "railway",
            "railway unknown-command",
        ])

    def test_variables_are_blocked_under_every_name(self):
        self.assert_commands_blocked([
            "railway variable",
            "railway variables",
            "railway vars",
            "railway var",
            "railway variable list",
            "railway variables ls",
            "railway variable set A=b",
            "railway vars set A=b",
            "railway var rm A",
            "railway variable edit",
            "railway variable --json",
        ])

    def test_aliases_of_forbidden_commands_are_blocked(self):
        self.assert_commands_blocked([
            "railway rm",
            "railway remove",
            "railway env delete",
            "railway env rm",
            "railway environment remove",
            "railway env staging",
            "railway env new staging",
            "railway environment update",
            "railway domain rm app.example.com",
            "railway domain remove app.example.com",
            "railway domain edit app.example.com",
            "railway template delete x",
            "railway deployments up",
            "railway projects delete",
            "railway usage limit rm",
            "railway postgres pitr backup rm abc",
            "railway local env",
            "railway develop",
        ])

    def test_removing_every_backup_schedule_is_blocked(self):
        self.assert_commands_blocked([
            "railway postgres pitr schedule set --none",
            "railway postgres pitr schedule set --daily --none",
            "railway postgres pitr schedule set --none=true",
            "railway postgres -s Postgres pitr schedule set --none",
        ])

    def test_reordered_options_do_not_hide_the_subcommand(self):
        self.assert_commands_blocked([
            "railway -e prod delete",
            "railway --environment prod delete",
            "railway --environment=prod delete",
            "railway -eprod delete",
            "railway -s api -e prod -p 1234 -w acme down",
            "railway --json delete",
            "railway --json -e prod down",
            "railway -e status delete",
            "railway --service status down",
            "railway --unknown status",
            "railway --unknown=1 status",
            "railway -x status",
            "railway -- delete",
            "railway --version delete",
            "railway --help delete",
            "railway usage --unknown limit set",
            "railway postgres pitr --json restore --at 1h",
        ])

    def test_a_subcommand_built_at_run_time_is_blocked(self):
        self.assert_commands_blocked([
            "railway $SUBCOMMAND",
            "railway \"$SUBCOMMAND\"",
            "railway $(echo delete)",
            "railway \"$(echo delete)\"",
            "railway de\"le\"te",
            "railway \"delete\"",
            "railway 'down'",
            "railway de$X",
            "railway logs $EXTRA",
            "railway status `echo --json`",
            "railway postgres pitr \"$ACTION\"",
        ])


class RailwayStreams(GuardTable):
    def test_logs_without_a_bound_are_blocked(self):
        self.assert_commands_blocked([
            "railway logs",
            "railway logs -s api",
            "railway logs --json --filter @level:error",
            "railway logs 6f1c2d",
            "railway -s api logs",
            "railway service logs -s api",
            "railway logs --latest",
        ])

    def test_every_bounding_option_lets_logs_run(self):
        self.assert_commands_allowed([
            "railway logs --since 10m",
            "railway logs --since=10m",
            "railway logs -S 10m",
            "railway logs -S10m",
            "railway logs --until 2026-10-09T10:00:00Z",
            "railway logs -U 1h",
            "railway logs --lines 100",
            "railway logs -n 100",
            "railway logs -n100",
            "railway logs --tail 100",
            "railway service logs --lines 20 -s api",
            "railway -s api logs --lines 20",
        ])

    def test_the_block_says_which_option_to_add(self):
        self.assert_reason_mentions("railway logs -s api", "--since", "--lines")


class RailwayLivenessProbe(GuardTable):
    def test_asking_help_on_a_forbidden_command_is_blocked(self):
        self.assert_commands_blocked([
            "railway down --help",
            "railway down -h",
            "railway delete --help",
        ])


class RailwayMessages(GuardTable):
    def test_a_blocked_mutation_points_to_the_tools_script(self):
        self.assert_reason_mentions("railway deploy -t metabase", PLUGIN_ROOT + "/scripts/railway-tools.sh")

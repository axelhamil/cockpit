# State v2 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let every script and reference file address one app through `$PROJECT` and `--project` on the current layout, then migrate each installed version 1 setup to layout version 2 by itself at session start, with a backup, a rollback, a legacy mode and a Railway relink.

**Architecture:** One tiny script (`project-directory.sh`) is the only place that knows where an app lives; the app scripts, the session check and the relink all ask it. The migration is a Python module behind a `sh` wrapper that `session-check.sh` runs before it reads anything: it works on a lock directory, backs up the root text files, builds `projects/<slug>/`, renames the four rebuildable folders into it, and commits by renaming `cockpit.md` into place, so any earlier failure undoes itself and leaves version 1 working. The reference files stop naming `~/.cockpit/<app thing>` and write `$PROJECT/...`.

**Tech Stack:** POSIX `sh`, Python 3.9 standard library, `unittest` through `tests/scripts/support.py`, prose skills checked by `claude plugin eval`.

**Spec:** `docs/superpowers/specs/2026-10-09-state-v2-design.md`, build order steps 1 and 2 (section 10), with sections 2, 3, 5, 6 (migration of the memory files only) and 9 (tests). Steps 3 to 5 (`memory.sh`, several apps and `project.sh`, welcome briefing) get their own plans; nothing here makes them harder: `project-directory.sh` already understands several apps and `--project`, and the layout is the final one.

## Global Constraints

Compatibility contract (spec section 2), every task answers to it:

- A client on state v1 opens a session after the update and gets the same abilities as before, on the same app, without typing anything new.
- The migration never loses a file. It backs up before it moves, and what it cannot convert safely it keeps as is.
- A migration that fails leaves v1 exactly as it was, and the session still works on it (legacy mode).
- A state written by a newer plugin is never touched by an older one.
- The release is a `feat`, never a `feat!`.

Session context lines printed by `scripts/session-check.sh`, exact text (the existing lines keep their text; `state directory:` still names `~/.cockpit`):

- `active project: <slug>`
- `project directory: <absolute path>`
- `state: updated to version 2`
- `migration: failed (<reason>)`
- `state: written by a newer cockpit, left untouched`
- `railway links: to refresh`

Layout (spec section 3), version 2:

- `~/.cockpit/cockpit.md` (flat header with `schema_version: 2`, `language`, `plugin_version`, `dependencies`; the user's name and email in its body), `memory/preferences.md`, `proposals.md`, `projects/<slug>/`, `backups/v1-<timestamp>/`.
- `projects/<slug>/`: `state.md` (header reduced to `provider: railway`, `onboarding`, `onboarding_step`), `memory/`, `journal.md`, `handoff.md`, `report.txt`, `saas-project/`, `tools-project/`, `repo/`, `secrets/`.
- `<slug>`: the Railway project name in lowercase, reduced to `a-z`, `0-9` and `-`; `app` when no project is known yet; it never changes afterwards.
- Each v1 memory file moves untouched under a `## Imported` heading: `domain.md`, `schema.md`, `codebase.md`, `tools.md` to `projects/<slug>/memory/<topic>.md`, `preferences.md` to `memory/preferences.md` at the root.

Migration (spec section 5): detect (root `state.md` with `schema_version: 1` and no `cockpit.md`; above 2 means newer and untouched), lock with `mkdir ~/.cockpit/.migrating` (older than 10 minutes means interrupted, take it over), back up the text files, build `projects/<slug>/`, rename the four folders, write `cockpit.md` last through a temporary file and a rename (the commit point), remove the old root files and the lock. A rerun is safe at any point. An error before the commit point undoes the renames and leaves v1 byte for byte.

Scripts and code:

- Scripts are POSIX `sh`, shellcheck clean, same style as the existing ones: `set -eu`, the `COCKPIT_TEST` guard that unsets test overrides, `COCKPIT_HOME`. Logic in Python 3.9 standard library only (no `X | Y` types, no `match`).
- `session-check.sh` always exits 0 and never prints a secret or a raw file line.
- No comment in code: no `#` comment in sh or Python (the shebang and tool directives such as `# shellcheck disable=` are the only exceptions), no docstring. Names carry the intent. Blank lines between logical blocks, guard clauses and early returns.
- Tests: `unittest`, run with `sh tests/scripts/run.sh`. Behaviour, not implementation. Few tests, each able to catch a real regression.
- Everything written in the repo is English. No em dash, no en dash, no emoji, anywhere.
- The 11 existing evals and their fixtures are never edited.
- Never bump a version, never edit `CHANGELOG.md`.
- After every task, `sh tests/scripts/run.sh` passes and a session on a v1 state behaves as before.

Git:

- Work on `feat/state-v2`, created from `develop`.
- Conventional Commits checked by commitlint: lowercase subject, no final period, at most 72 characters, describing the observable effect, body lines at most 100 characters. Never `feat!`.
- One logical change per commit. Stage the named files only (never `git add -A` or `git add .`). Commit with the pathspec form shown in each task, so a path that was already staged before the branch (see Task 0) never leaks into a commit.

## Review Focus

Failure modes the spec implies and the first tests would not catch. Each has its test in the task named at the end of the line.

1. A half-written v1 state (the header never closes) is not migrated, is not damaged, and the session still answers in legacy mode. (Task 4: `test_given_a_state_whose_header_never_closes_then_nothing_is_attempted`; Task 2: `test_given_a_half_written_version_1_state_then_the_app_folder_is_the_state_folder`)
2. A Railway project name with accents, spaces or symbols ("Café & Co!") becomes a plain folder name (`cafe-co`), never a path that escapes `projects/`. (Task 4, `test_given_a_project_name_with_accents_and_symbols_then_the_folder_name_is_plain`; Task 1, `test_given_an_unknown_or_unsafe_app_name_then_it_is_refused_with_the_known_apps`)
3. A state folder whose path holds spaces or brackets (a home folder like `my home [work]`) migrates the same way. (Task 4, `test_given_a_state_folder_with_spaces_and_brackets_then_the_migration_still_works`)
4. A Mac where `python3` cannot run (no Command Line Tools yet) reports `migration: failed (python3 is not available)` and keeps working on v1, instead of opening the macOS install dialog or hanging. (Task 4, `test_given_a_mac_without_python_then_the_failure_is_reported_and_version_1_is_left_alone`)
5. A `User:` line that is not "name, email" is kept as written, nothing is lost. (Task 4, `test_given_a_state_without_a_railway_project_yet_then_the_app_is_named_app`)

## File Structure

| File | Responsibility |
|---|---|
| `scripts/project-directory.sh` (create) | The only place that knows where an app lives: prints the app folder, `--list` prints the app names. |
| `scripts/health-check.sh`, `scripts/database-access.sh` (modify) | Take `--project <slug>` and work in that app's `saas-project/`. |
| `scripts/migrate-state.sh` (create) | Wrapper: guards (no state, no Python), then runs the Python module. |
| `scripts/migrate_state.py` (create) | Detect, lock, back up, build, rename, commit, clean up, roll back. |
| `scripts/relink.sh` (create) | Runs `railway link` again for the moved folders of one app, removes the `.relink` marker. |
| `scripts/session-check.sh` (modify) | Runs the migration, resolves the active app, reads both layouts, prints the new lines. |
| `tests/fixtures/state-v1/fixture.sh` (create) | A realistic v1 state with every v1 file and folder. |
| `tests/scripts/support.py` (modify) | `write_v2_state`, `build_state_v1`, `snapshot`. |
| `tests/scripts/test_project_directory.py`, `test_migrate_state.py`, `test_relink.py` (create) | Behaviour tests of the new scripts. |
| `tests/scripts/test_session_check.py`, `test_health_check.py`, `test_database_access.py` (modify) | New cases for the new lines and `--project`. |
| `skills/**` (modify) | `$PROJECT` in every reference, the version 2 schema, the new session lines. |
| `docs/verified-facts.md`, `CLAUDE.md`, `.github/workflows/ci.yml` (modify) | Facts, repo guidance, shellcheck on the fixture. |

## Decisions taken while planning

The spec leaves these open. They are decided here and the code follows them.

- Exit status of `migrate-state.sh`: 0 normally, 3 when the state is from a newer cockpit (after printing the newer line). `session-check.sh` stops reading the state on 3.
- In legacy mode the session prints `active project: legacy` and `project directory: <state directory>`.
- A Mac with no saved setup, and a version 2 setup with a user file but no app folder yet, get `app` as the app name. Onboarding creates `projects/app`.
- `project-directory.sh` exit statuses: 0 found, 1 unknown or unsafe name, 4 several apps and none named, 64 usage. With several apps and no name the session context says `active project: none` plus a note; choosing is the job of a later plan.
- A lock younger than 10 minutes makes a second session wait 3 seconds, then report `migration: failed (another session is migrating the saved setup)` and keep working on v1.
- The root files are removed after the commit point only when they are byte for byte the backed-up copy. A file changed in the meantime stays where it is.
- `secrets/` is renamed, never copied: a backup must not spread keys.
- The v1 line `- Clone: ~/.cockpit/repo` is dropped (the clone is always `$PROJECT/repo`). A `User:` line that is not "name, email" stays as written in `cockpit.md`.
- `.relink` is created only when `saas-project/` or `tools-project/` existed.

---

### Task 0: Branch and clean start

**Files:** none.

- [ ] **Step 1: Look at the tree**

Run: `git status --short && git branch --show-current`
Expected: branch `develop`. The owner's pending changes may show (`CHANGELOG.md`, `README.md`, a renamed plan, the untracked `CLAUDE.md` and the spec). Do not touch them and never stage them with this work.

- [ ] **Step 2: Create the branch**

Run: `git switch -c feat/state-v2`
Expected: `Switched to a new branch 'feat/state-v2'`

- [ ] **Step 3: Baseline**

Run: `sh tests/scripts/run.sh`
Expected: `Ran 61 tests in ...s` then `OK`. Install `shellcheck` if missing (`brew install shellcheck` or `sudo pacman -S shellcheck`), then run `shellcheck scripts/*.sh tests/scripts/*.sh evals/*/fixture.sh`. Expected: no output.

- [ ] **Step 4: Commit the plan and the spec if they are still untracked**

Run: `git status --short docs/superpowers CLAUDE.md`
If `CLAUDE.md`, the spec or this plan show as `??`, commit them on their own so that Task 8 shows only its own diff to `CLAUDE.md`:

```bash
git add CLAUDE.md docs/superpowers/specs/2026-10-09-state-v2-design.md docs/superpowers/plans/2026-10-09-state-v2-foundation.md
git commit -F - -- CLAUDE.md docs/superpowers/specs/2026-10-09-state-v2-design.md docs/superpowers/plans/2026-10-09-state-v2-foundation.md <<'EOF'
docs: add CLAUDE.md, the state v2 spec and its first plan

The spec describes one folder per app, searchable memory and a welcome
briefing. The plan covers its build order steps 1 and 2.
EOF
```

---

### Task 1: One script that knows where an app lives

**Files:**
- Create: `scripts/project-directory.sh`
- Create: `tests/scripts/test_project_directory.py`
- Modify: `tests/scripts/support.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `sh scripts/project-directory.sh [--project <slug>]` prints the absolute app folder on stdout. `--project ''` means "not given". `sh scripts/project-directory.sh --list` prints one app name per line (nothing on a v1 layout). Exit status 0 found, 1 unknown or unsafe name (message on stderr that names the known apps), 4 several apps and none named (message names them), 64 usage. Rules, in this order: no `cockpit.md` and a `state.md` at the root means v1 layout (legacy): the app folder is the state directory itself and `--project` is ignored. Otherwise the apps are the folders `projects/<slug>/` with a `state.md` and a slug of `a-z`, `0-9`, `-`; none gives `<state directory>/projects/app`, one gives it, several need `--project`. `COCKPIT_HOME` moves the state directory. Test helper `ScriptTestCase.write_v2_state(*slugs, onboarding="complete")` writes `cockpit-home/cockpit.md` and one `projects/<slug>/state.md` per slug.

- [ ] **Step 1: Write the helper and the failing tests**

In `tests/scripts/support.py`, replace:

```text
    def install_command(self, name, body, directory="bin"):
```

with:

```text
    def write_v2_state(self, *slugs, onboarding="complete"):
        self.write(
            "cockpit-home/cockpit.md",
            "---\nschema_version: 2\nlanguage: en\nplugin_version: 1.0.0\ndependencies: git, railway\n---\n\n"
            "## User\n- Name: Alex Morgan\n- Email: alex@example.com\n",
        )
        for slug in slugs:
            self.write(
                "cockpit-home/projects/{}/state.md".format(slug),
                "---\nprovider: railway\nonboarding: {}\nonboarding_step: check\n---\n\n"
                "## SaaS project\n- Project: {} (11111111-1111-1111-1111-111111111111)\n".format(onboarding, slug),
            )

    def install_command(self, name, body, directory="bin"):
```

Create `tests/scripts/test_project_directory.py`:

```python
from support import ScriptTestCase


class ProjectDirectoryTest(ScriptTestCase):
    def directory(self, *arguments):
        return self.run_script("project-directory.sh", *arguments)

    def test_given_a_version_1_layout_then_the_app_folder_is_the_state_folder(self):
        self.write("cockpit-home/state.md", "---\nschema_version: 1\n---\n")

        result = self.directory()
        named = self.directory("--project", "whatever")

        self.assertEqual(result.stdout, self.home + "\n")
        self.assertEqual(named.stdout, self.home + "\n")
        self.assertEqual(self.directory("--list").stdout, "")

    def test_given_one_app_then_it_is_used_without_naming_it(self):
        self.write_v2_state("acme-studio")

        result = self.directory()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, self.home + "/projects/acme-studio\n")
        self.assertEqual(self.directory("--list").stdout, "acme-studio\n")

    def test_given_no_state_at_all_then_the_first_app_will_be_named_app(self):
        result = self.directory()

        self.assertEqual(result.stdout, self.home + "/projects/app\n")

    def test_given_several_apps_then_the_one_asked_for_is_used(self):
        self.write_v2_state("acme-studio", "beta-shop")

        result = self.directory("--project", "beta-shop")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, self.home + "/projects/beta-shop\n")

    def test_given_several_apps_and_no_choice_then_the_error_names_them_all(self):
        self.write_v2_state("acme-studio", "beta-shop")

        result = self.directory()

        self.assertEqual(result.returncode, 4)
        self.assertEqual(result.stdout, "")
        self.assertIn("acme-studio, beta-shop", result.stderr)
        self.assertIn("--project", result.stderr)

    def test_given_an_unknown_or_unsafe_app_name_then_it_is_refused_with_the_known_apps(self):
        self.write_v2_state("acme-studio")

        unknown = self.directory("--project", "gamma")
        unsafe = self.directory("--project", "../acme-studio")

        self.assertEqual(unknown.returncode, 1)
        self.assertIn("Apps: acme-studio", unknown.stderr)
        self.assertEqual(unsafe.returncode, 1)
        self.assertEqual(unsafe.stdout, "")

    def test_given_folders_that_are_not_apps_then_they_are_ignored(self):
        self.write_v2_state("acme-studio")
        self.write("cockpit-home/projects/Not An App/state.md", "---\n---\n")
        self.write("cockpit-home/projects/no-state/notes.md", "")

        self.assertEqual(self.directory("--list").stdout, "acme-studio\n")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `sh tests/scripts/run.sh -k test_project_directory`
Expected: FAIL, every new test (the script does not exist yet, `sh` answers `No such file`).

- [ ] **Step 3: Write the script**

Create `scripts/project-directory.sh`:

```sh
#!/bin/sh
set -eu

state_home=${COCKPIT_HOME:-${HOME:-}/.cockpit}
default_slug=app
usage='Usage: project-directory.sh [--project <slug>] | --list'
several_apps_status=4

fail() {
  printf '%s\n' "$1" >&2
  exit "${2:-1}"
}

is_slug() {
  case $1 in
    '' | *[!a-z0-9-]*) return 1 ;;
    *) return 0 ;;
  esac
}

list_slugs() {
  for entry in "$state_home"/projects/*/; do
    slug=${entry%/}
    slug=${slug##*/}

    if is_slug "$slug" && [ -f "${entry}state.md" ]; then
      printf '%s\n' "$slug"
    fi
  done
}

is_legacy_layout() {
  [ ! -f "$state_home/cockpit.md" ] && [ -e "$state_home/state.md" ]
}

project=
list_only=0

while [ "$#" -gt 0 ]; do
  case $1 in
    --list)
      list_only=1
      shift
      ;;
    --project)
      if [ "$#" -lt 2 ]; then
        fail "$usage" 64
      fi

      project=$2
      shift 2
      ;;
    *)
      fail "$usage" 64
      ;;
  esac
done

if is_legacy_layout; then
  if [ "$list_only" = 0 ]; then
    printf '%s\n' "$state_home"
  fi
  exit 0
fi

if [ "$list_only" = 1 ]; then
  list_slugs
  exit 0
fi

count=0
only=
names=

while IFS= read -r slug; do
  if [ -z "$slug" ]; then
    continue
  fi

  count=$((count + 1))
  only=$slug
  names=${names:+$names, }$slug
done <<EOF
$(list_slugs)
EOF

if [ -n "$project" ]; then
  if ! is_slug "$project"; then
    fail "'$project' is not an app name: an app name has only lowercase letters, digits and dashes."
  fi

  if [ ! -f "$state_home/projects/$project/state.md" ]; then
    fail "There is no app named '$project' here. Apps: ${names:-none}."
  fi

  printf '%s\n' "$state_home/projects/$project"
  exit 0
fi

case $count in
  0) printf '%s\n' "$state_home/projects/$default_slug" ;;
  1) printf '%s\n' "$state_home/projects/$only" ;;
  *) fail "Several apps are saved here ($names). Say which one with --project <app>." "$several_apps_status" ;;
esac
```

- [ ] **Step 4: Run the whole suite**

Run: `sh tests/scripts/run.sh`
Expected: `Ran 68 tests in ...s` then `OK`.

- [ ] **Step 5: Lint**

Run: `shellcheck scripts/project-directory.sh`
Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add scripts/project-directory.sh tests/scripts/test_project_directory.py tests/scripts/support.py
git commit -F - -- scripts/project-directory.sh tests/scripts/test_project_directory.py tests/scripts/support.py <<'EOF'
refactor(scripts): find the active app folder in one script

project-directory.sh prints the folder of the app a script works on:
the state directory itself on the layout of today, projects/<slug> on
the next one, with --project to pick one and an error that names the
apps when it cannot decide. Nothing calls it yet.
EOF
```

---

### Task 2: `--project` on the app scripts and the two new context lines

**Files:**
- Modify: `scripts/health-check.sh`
- Modify: `scripts/database-access.sh`
- Modify: `scripts/session-check.sh`
- Modify: `tests/scripts/test_health_check.py`
- Modify: `tests/scripts/test_database_access.py`
- Modify: `tests/scripts/test_session_check.py`

**Interfaces:**
- Consumes: `project-directory.sh [--project <slug>]` from Task 1.
- Produces: `health-check.sh [--project <slug>]` (empty value allowed, means none; an app it cannot resolve ends silently with status 0, because it runs inside the hook). `database-access.sh --service <name> [--private] [--project <slug>]` (an unresolvable app is an error on stderr, status 1, with the message of `project-directory.sh`). Session context: after `state directory:` the lines `active project: legacy` and `project directory: <state directory>` on a v1 layout, `active project: app` and `project directory: <state directory>/projects/app` with no state, `active project: none` when the folder cannot be resolved. Shell variables set by `announce_project` in `session-check.sh`: `project_directory`, `project_slug`. Existing tests of the two scripts now write a v1 `state.md` next to the `saas-project` folder, because "no state at all" now means a fresh Mac.

- [ ] **Step 1: Write the failing tests**

Make the existing set-ups explicit about the layout they use.

In `tests/scripts/test_health_check.py`, replace:

```text
        self.write("cockpit-home/saas-project/.keep", "")
```

with:

```text
        self.write("cockpit-home/state.md", "---\nschema_version: 1\n---\n")
        self.write("cockpit-home/saas-project/.keep", "")
```

In `tests/scripts/test_database_access.py`, replace:

```text
        self.write("cockpit-home/saas-project/.keep", "")
```

with:

```text
        self.write("cockpit-home/state.md", "---\nschema_version: 1\n---\n")
        self.write("cockpit-home/saas-project/.keep", "")
```

Append to the end of `class HealthCheckTest` in `tests/scripts/test_health_check.py`:

```python
    def test_given_several_apps_then_the_one_named_is_checked_in_its_own_folder(self):
        self.write_v2_state("acme-studio", "beta-shop")
        self.write("cockpit-home/projects/beta-shop/saas-project/.keep", "")
        self.write("status.json", json.dumps(project(("web", "FAILED"))))
        self.install_fake_railway('pwd >"' + self.path("where") + '"\ncat "' + self.path("status.json") + '"\n')

        result = self.run_script("health-check.sh", "--project", "beta-shop")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('service "web"', result.stdout)
        self.assertEqual(self.read("where").strip(), self.path("cockpit-home/projects/beta-shop/saas-project"))

    def test_given_several_apps_and_none_named_then_nothing_is_checked(self):
        self.write_v2_state("acme-studio", "beta-shop")
        self.write("cockpit-home/projects/beta-shop/saas-project/.keep", "")
        self.railway_answers(project(("web", "FAILED")))

        result = self.check()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
```

Append to the end of `class DatabaseAccessTest` in `tests/scripts/test_database_access.py`:

```python
    def test_given_several_apps_then_the_service_is_read_in_the_folder_of_the_app_named(self):
        self.write_v2_state("acme-studio", "beta-shop")
        self.write("cockpit-home/projects/beta-shop/saas-project/.keep", "")
        self.write("variables.json", json.dumps({"DATABASE_PUBLIC_URL": PUBLIC_URL}))
        self.install_fake_railway('pwd >"' + self.path("where") + '"\ncat "' + self.path("variables.json") + '"\n')

        result = self.access("--service", "Postgres", "--project", "beta-shop")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read("where").strip(), self.path("cockpit-home/projects/beta-shop/saas-project"))

    def test_given_several_apps_and_none_named_then_the_error_names_the_apps(self):
        self.write_v2_state("acme-studio", "beta-shop")

        result = self.access("--service", "Postgres")

        self.assertEqual(result.returncode, 1)
        self.assertIn("acme-studio, beta-shop", result.stderr)
```

Append to the end of `tests/scripts/test_session_check.py`, after two blank lines:

```python
class SessionCheckLayoutTest(ScriptTestCase):
    def setUp(self):
        super().setUp()
        self.env["PATH"] = os.environ["PATH"]
        self.install_fake_railway("exit 1\n")

    def check(self, **environment):
        return self.run_script("session-check.sh", env=environment)

    def lines(self, **environment):
        return self.check(**environment).stdout.splitlines()

    def test_given_no_state_then_the_first_app_is_announced_as_app(self):
        lines = self.lines()

        self.assertIn("active project: app", lines)
        self.assertIn("project directory: " + self.home + "/projects/app", lines)
        self.assertIn("state directory: " + self.home, lines)
        self.assertTrue(any(line.startswith("onboarding: absent") for line in lines))

    def test_given_a_half_written_version_1_state_then_the_app_folder_is_the_state_folder(self):
        self.write("cockpit-home/state.md", "---\nschema_version: 1\nlanguage: fr\n")

        lines = self.lines()

        self.assertIn("active project: legacy", lines)
        self.assertIn("project directory: " + self.home, lines)
        self.assertIn("onboarding: unknown", lines)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `sh tests/scripts/run.sh`
Expected: `FAILED (failures=6)`: the two `several apps` tests of `HealthCheckTest`, the two of `DatabaseAccessTest` and the two tests of `SessionCheckLayoutTest`. Every other test passes.

- [ ] **Step 3: Teach the scripts**

In `scripts/health-check.sh`, replace:

```text
state_home=${COCKPIT_HOME:-${HOME:-}/.cockpit}
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
saas_dir=$state_home/saas-project
```

with:

```text
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
usage='Usage: health-check.sh [--project <slug>]'
project=

while [ "$#" -gt 0 ]; do
  case $1 in
    --project)
      if [ "$#" -lt 2 ]; then
        printf '%s\n' "$usage" >&2
        exit 2
      fi

      project=$2
      shift 2
      ;;
    *)
      printf '%s\n' "$usage" >&2
      exit 2
      ;;
  esac
done

project_directory=$(sh "$script_dir/project-directory.sh" --project "$project" 2>/dev/null) || exit 0
saas_dir=$project_directory/saas-project
```

In `scripts/database-access.sh`, replace:

```text
state_home=${COCKPIT_HOME:-$HOME/.cockpit}
```

with:

(nothing: delete those lines)

In `scripts/database-access.sh`, replace:

```text
usage='Usage: database-access.sh --service <postgres service> [--private]'
variable_name=DATABASE_PUBLIC_URL
service=
```

with:

```text
usage='Usage: database-access.sh --service <postgres service> [--private] [--project <slug>]'
variable_name=DATABASE_PUBLIC_URL
service=
project=
```

In `scripts/database-access.sh`, replace:

```text
      service=$2
      shift 2
      ;;
```

with:

```text
      service=$2
      shift 2
      ;;
    --project)
      if [ "$#" -lt 2 ]; then
        fail "$usage" 2
      fi

      project=$2
      shift 2
      ;;
```

In `scripts/database-access.sh`, replace:

```text
saas_dir=$state_home/saas-project
```

with:

```text
project_directory=$(sh "$script_dir/project-directory.sh" --project "$project") || exit 1
saas_dir=$project_directory/saas-project
```

In `scripts/session-check.sh`, replace:

```text
scripts_directory() {
```

with:

```text
known_slug() {
  case $1 in
    '' | *[!a-z0-9-]*) printf 'unknown' ;;
    *) printf '%s' "$1" ;;
  esac
}

scripts_directory() {
```

In `scripts/session-check.sh`, replace:

```text
print_context() {
```

with:

```text
announce_project() {
  if [ -z "${scripts_dir:-}" ] || ! project_directory=$(sh "$scripts_dir/project-directory.sh" 2>/dev/null); then
    printf 'active project: none\n'
    return 0
  fi

  project_slug=legacy

  if [ "$project_directory" != "$state_home" ]; then
    project_slug=$(known_slug "${project_directory##*/}")
  fi

  printf 'active project: %s\n' "$project_slug"
  printf 'project directory: %s\n' "$project_directory"
}

print_context() {
```

In `scripts/session-check.sh`, replace:

```text
  printf 'state directory: %s\n' "$state_home"
```

with:

```text
  printf 'state directory: %s\n' "$state_home"
  announce_project
```

- [ ] **Step 4: Run the whole suite and lint**

Run: `sh tests/scripts/run.sh`
Expected: `Ran 74 tests in ...s` then `OK`.

Run: `shellcheck scripts/*.sh tests/scripts/*.sh evals/*/fixture.sh`
Expected: no output.

- [ ] **Step 5: Look at the real context**

Run: `T=$(mktemp -d) && printf -- '---\nschema_version: 1\nlanguage: en\nonboarding: complete\ndependencies: git\n---\n' >"$T/state.md" && COCKPIT_HOME=$T sh scripts/session-check.sh | sed -n 4,9p`
Expected: `state directory: <T>`, `active project: legacy`, `project directory: <T>`, then `state schema version: 1`, `language: en`, `onboarding: complete` exactly as before.

- [ ] **Step 6: Commit**

```bash
git add scripts/health-check.sh scripts/database-access.sh scripts/session-check.sh tests/scripts/test_health_check.py tests/scripts/test_database_access.py tests/scripts/test_session_check.py
git commit -F - -- scripts/health-check.sh scripts/database-access.sh scripts/session-check.sh tests/scripts/test_health_check.py tests/scripts/test_database_access.py tests/scripts/test_session_check.py <<'EOF'
refactor(scripts): give the app scripts a --project option

health-check.sh and database-access.sh work in the saas-project folder
of the app they are asked for, and the session context now names the
active project and its folder. On the layout of today nothing changes:
the folder is the state directory and the project is called legacy.
EOF
```

---

### Task 3: Reference files write `$PROJECT`

**Files:**
- Modify: `skills/cockpit/SKILL.md`, `skills/onboard/SKILL.md`, `skills/report/SKILL.md`
- Modify: `skills/cockpit/references/undo.md`, `tools.md`, `status.md`, `code-changes.md`, `escalation.md`, `repair.md`, `onboarding.md`

**Interfaces:**
- Consumes: the `project directory:` line of the session context from Task 2.
- Produces: the placeholder `$PROJECT` in the skills, explained once in `skills/cockpit/SKILL.md` step 1, equal to `~/.cockpit` on the layout of today. Every path that belongs to one app (`saas-project/`, `tools-project/`, `repo/`, `secrets/`, `journal.md`, `handoff.md`, `report.txt`, `state.md`) is written `$PROJECT/...`. `~/.cockpit/proposals.md` stays as it is (it belongs to the user). Left for Task 6 on purpose: `onboarding.md` line 7 (creation of `state.md`), `memory.md`, the Desktop copy of `repair.md`, `state-schema.md`.

- [ ] **Step 1: Save the replacement script**

Save this as `/tmp/cockpit-task3.py` (outside the repo, never committed). Every replacement states how many occurrences it expects and the script stops without writing when a count differs.

```python
import pathlib
import sys

ROOT = pathlib.Path(sys.argv[1])

REPLACEMENTS = [
    (
        "skills/cockpit/SKILL.md",
        "1. Read `~/.cockpit/state.md`. The session context gives the full path of that folder as `state directory`: use it for every file of `~/.cockpit/`.",
        "1. Read `$PROJECT/state.md`. `$PROJECT` is a placeholder, not a shell variable, like `$SCRIPTS`: replace it with the `project directory:` line of the session context in every path and command. It holds everything that belongs to the app. The `state directory:` line names `~/.cockpit/`, for what belongs to the user.",
        1,
    ),
    (
        "skills/cockpit/SKILL.md",
        "Run these from `~/.cockpit/saas-project/` (linked to the SaaS project) or `~/.cockpit/tools-project/`.",
        "Run these from `$PROJECT/saas-project/` (linked to the SaaS project) or `$PROJECT/tools-project/`.",
        1,
    ),
    (
        "skills/cockpit/SKILL.md",
        "the code in `~/.cockpit/repo/`",
        "the code in `$PROJECT/repo/`",
        1,
    ),
    (
        "skills/cockpit/SKILL.md",
        "Always run the scripts with `sh`.",
        "Always run the scripts with `sh`. A script that works on one app takes `--project <slug>`, the `active project:` line of the session context. Without it, it uses the only app.",
        1,
    ),
    ("skills/onboard/SKILL.md", "- `~/.cockpit/state.md` missing:", "- `$PROJECT/state.md` missing:", 1),
    ("skills/report/SKILL.md", "Read `~/.cockpit/journal.md` and `~/.cockpit/proposals.md`.", "Read `$PROJECT/journal.md` and `~/.cockpit/proposals.md`.", 1),
    ("skills/report/SKILL.md", "~/.cockpit/report.txt", "$PROJECT/report.txt", 2),
    ("skills/cockpit/references/undo.md", "`~/.cockpit/journal.md`", "`$PROJECT/journal.md`", 1),
    ("skills/cockpit/references/tools.md", "~/.cockpit/tools-project", "$PROJECT/tools-project", 6),
    ("skills/cockpit/references/tools.md", "~/.cockpit/saas-project", "$PROJECT/saas-project", 2),
    ("skills/cockpit/references/tools.md", "~/.cockpit/secrets", "$PROJECT/secrets", 3),
    ("skills/cockpit/references/status.md", "~/.cockpit/saas-project/", "$PROJECT/saas-project/", 1),
    ("skills/cockpit/references/status.md", "~/.cockpit/tools-project/", "$PROJECT/tools-project/", 1),
    ("skills/cockpit/references/code-changes.md", "~/.cockpit/repo", "$PROJECT/repo", 2),
    ("skills/cockpit/references/escalation.md", "~/.cockpit/handoff.md", "$PROJECT/handoff.md", 2),
    ("skills/cockpit/references/repair.md", "~/.cockpit/saas-project/", "$PROJECT/saas-project/", 1),
    ("skills/cockpit/references/repair.md", "~/.cockpit/tools-project/", "$PROJECT/tools-project/", 1),
    ("skills/cockpit/references/repair.md", "~/.cockpit/repo", "$PROJECT/repo", 2),
    ("skills/cockpit/references/onboarding.md", "~/.cockpit/saas-project", "$PROJECT/saas-project", 3),
    ("skills/cockpit/references/onboarding.md", "<repo> ~/.cockpit/repo`", "<repo> $PROJECT/repo`", 1),
    ("skills/cockpit/references/onboarding.md", "From `~/.cockpit/repo/`", "From `$PROJECT/repo/`", 1),
]

failures = []
for relative, old, new, expected in REPLACEMENTS:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        failures.append("{}: expected {} of {!r}, found {}".format(relative, expected, old[:50], count))
        continue
    path.write_text(text.replace(old, new), encoding="utf-8")

if failures:
    print("\n".join(failures))
    sys.exit(1)
print("{} replacements applied".format(len(REPLACEMENTS)))
```

- [ ] **Step 2: Apply it from the repo root**

Run: `python3 /tmp/cockpit-task3.py .`
Expected: `21 replacements applied`

- [ ] **Step 3: Check what is left**

Run: `grep -rn '~/\.cockpit/\(saas-project\|tools-project\|repo\|secrets\|journal\|handoff\|report\|state\)' skills | cut -c1-110`
Expected: exactly two lines, both on purpose: `skills/cockpit/references/state-schema.md:55:- Clone: ~/.cockpit/repo` and `skills/cockpit/references/onboarding.md:7:`. Task 6 handles both.

Run: `git diff --stat -- skills`
Expected: 10 files changed, no file outside `skills/`.

- [ ] **Step 4: Commit**

```bash
git add skills/cockpit/SKILL.md skills/onboard/SKILL.md skills/report/SKILL.md skills/cockpit/references/undo.md skills/cockpit/references/tools.md skills/cockpit/references/status.md skills/cockpit/references/code-changes.md skills/cockpit/references/escalation.md skills/cockpit/references/repair.md skills/cockpit/references/onboarding.md
git commit -F - -- skills/cockpit/SKILL.md skills/onboard/SKILL.md skills/report/SKILL.md skills/cockpit/references/undo.md skills/cockpit/references/tools.md skills/cockpit/references/status.md skills/cockpit/references/code-changes.md skills/cockpit/references/escalation.md skills/cockpit/references/repair.md skills/cockpit/references/onboarding.md <<'EOF'
docs(skills): point the references at the active app folder

Everything that belongs to one app is written $PROJECT/..., a
placeholder for the project directory line of the session context, the
same way scripts are written $SCRIPTS. On the layout of today it is
~/.cockpit itself, so no behaviour changes.
EOF
```

---

### Task 4: The migration

**Files:**
- Create: `tests/fixtures/state-v1/fixture.sh`
- Create: `scripts/migrate-state.sh`
- Create: `scripts/migrate_state.py`
- Create: `tests/scripts/test_migrate_state.py`
- Modify: `tests/scripts/support.py`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `ScriptTestCase.write_v2_state` from Task 1.
- Produces: `sh scripts/migrate-state.sh` (no argument; `COCKPIT_HOME` or `~/.cockpit`). Prints at most one line: `state: updated to version 2`, `migration: failed (<reason>)` or `state: written by a newer cockpit, left untouched`. Exit status 0, or 3 for the newer line. Nothing to do (no state, already version 2, state that cannot be read as version 1): silent, status 0. Result of a migration: see the tests. Test-only seams, honoured only when `COCKPIT_TEST=1` (the wrapper unsets them otherwise): `COCKPIT_MIGRATION_FAIL_AT=<backed-up|built|renamed>` raises an error right after that stage, `COCKPIT_MIGRATION_KILL_AT=<backed-up|built|renamed|committed>` exits at once without any cleanup (an interrupted run), `COCKPIT_MIGRATION_LOCK_WAIT=<seconds>` (default 3). Test helpers: `ScriptTestCase.build_state_v1(home=None)` builds the fixture in `home` (default `self.home`), `ScriptTestCase.snapshot(directory=None)` returns `{relative path: (kind, mode, bytes or None)}` for a whole tree. The fixture: `tests/fixtures/state-v1/fixture.sh`, honours `COCKPIT_HOME`, app named "Acme Studio" so the folder is `projects/acme-studio`.

- [ ] **Step 1: Write the fixture**

Create `tests/fixtures/state-v1/fixture.sh`. It has every v1 file (`state.md`, `domain.md`, `schema.md`, `codebase.md`, `tools.md`, `preferences.md`, `journal.md`, `proposals.md`, `handoff.md`, `report.txt`) and folder (`saas-project/`, `tools-project/`, `repo/`, `secrets/` with a key in mode 600), with accents in the memory files so that byte-for-byte copies are tested.

```sh
#!/bin/sh
set -eu

state_home=${COCKPIT_HOME:-$HOME/.cockpit}

mkdir -p "$state_home/saas-project" "$state_home/tools-project" "$state_home/repo/src" "$state_home/secrets"

cat >"$state_home/state.md" <<'STATE'
---
schema_version: 1
language: fr
onboarding: complete
onboarding_step: check
plugin_version: 1.6.0
dependencies: git, railway, gh
---

## Profile
- Usages: tools, app changes, health, diagnosis
- Tools wanted: metabase (reads app data)
- User: Alex Morgan, alex@example.com
- Developer: Sam, @sam-dev, channel: github

## Plan
- profile: done
- plan: done
- dependencies: done
- railway: done
- backups: done
- settings: done
- github: done
- tools: done
- discovery: done
- check: done

## Dependencies
- railway 5.64.1
- gh 2.102.0

## SaaS project
- Project: Acme Studio (11111111-1111-1111-1111-111111111111)
- Production environment: production
- App service: web, repository acme/app, deployed branch main
- Postgres service: Postgres
- Test environment: none
- Backups: schedule daily, weekly, first backup 2026-10-01
- Spending alert: 50 USD per month

## Code
- Merge policy: ask-me
- Clone: ~/.cockpit/repo

## Tools project
- Project: Acme Studio tools (22222222-2222-2222-2222-222222222222)

## Tools
- metabase: project tools, template metabase, services metabase and metabase-db, URL https://metabase.example.com, driven by mcp, app data connected

## Open escalations
- 2026-10-08: signup page fails on Safari, https://github.com/acme/app/issues/7
STATE

cat >"$state_home/domain.md" <<'DOMAIN'
- Client actif : un compte avec une facture payée sur les 30 derniers jours.
- Essai : un compte créé il y a moins de 14 jours, sans abonnement.
DOMAIN

cat >"$state_home/schema.md" <<'SCHEMA'
- accounts : un compte client, la table qui possède tout le reste.
- invoices : les factures, `paid_at` est vide tant qu'elles ne sont pas payées.
SCHEMA

cat >"$state_home/codebase.md" <<'CODEBASE'
- Stack : Next.js, Postgres, déployé depuis la branche main.
- Les textes des écrans vivent dans `src/locales`.
CODEBASE

cat >"$state_home/tools.md" <<'TOOLS'
- Metabase : tableau de bord "Pilotage" (clients actifs par semaine), fiche client.
TOOLS

cat >"$state_home/preferences.md" <<'PREFERENCES'
- Réponses courtes, les chiffres en euros, le lundi matin.
PREFERENCES

cat >"$state_home/journal.md" <<'JOURNAL'
- 2026-10-07: deployed metabase in the tools project, undo: delete services metabase and metabase-db (content lost)
- 2026-10-08: changed the signup button label to "Start free" (pull request 42), undo: gh pr revert 42
JOURNAL

cat >"$state_home/proposals.md" <<'PROPOSALS'
- 2026-10-08: the backup step should say what a daily schedule costs.
PROPOSALS

cat >"$state_home/handoff.md" <<'HANDOFF'
Request: the signup page fails on Safari.
HANDOFF

printf 'cockpit report\n' >"$state_home/report.txt"

printf '' >"$state_home/saas-project/.keep"
printf '' >"$state_home/tools-project/.keep"
printf 'export const label = "Start free"\n' >"$state_home/repo/src/app.txt"

printf 'X-API-KEY: not-a-real-key\n' >"$state_home/secrets/metabase.key"
chmod 700 "$state_home/secrets"
chmod 600 "$state_home/secrets/metabase.key"
```

- [ ] **Step 2: Write the test helpers**

In `tests/scripts/support.py`, replace:

```text
import shutil
import subprocess
```

with:

```text
import shutil
import stat
import subprocess
```

In `tests/scripts/support.py`, replace:

```text
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
```

with:

```text
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
FIXTURES_DIR = os.path.join(REPO_ROOT, "tests", "fixtures")
```

In `tests/scripts/support.py`, replace:

```text
    def write_v2_state(self, *slugs, onboarding="complete"):
```

with:

```text
    def build_state_v1(self, home=None):
        subprocess.run(
            [SHELL, os.path.join(FIXTURES_DIR, "state-v1", "fixture.sh")],
            env={**self.env, "COCKPIT_HOME": home or self.home},
            check=True,
            stdout=subprocess.DEVNULL,
        )

    def snapshot(self, directory=None):
        root = directory or self.home
        entries = {}

        for current, directories, files in os.walk(root):
            for name in directories + files:
                full = os.path.join(current, name)
                mode = stat.S_IMODE(os.lstat(full).st_mode)

                if os.path.isdir(full):
                    entries[os.path.relpath(full, root)] = ("directory", mode, None)
                    continue

                with open(full, "rb") as handle:
                    entries[os.path.relpath(full, root)] = ("file", mode, handle.read())

        return entries

    def write_v2_state(self, *slugs, onboarding="complete"):
```

- [ ] **Step 3: Write the failing tests**

Create `tests/scripts/test_migrate_state.py`:

```python
import os
import time

from support import ScriptTestCase

PROJECT = "projects/acme-studio"
UPDATED = "state: updated to version 2\n"
NEWER = "state: written by a newer cockpit, left untouched\n"
IMPORTED = "## Imported\n\n".encode()
ROOT_TEXT_FILES = (
    "state.md",
    "domain.md",
    "schema.md",
    "codebase.md",
    "tools.md",
    "preferences.md",
    "journal.md",
    "proposals.md",
    "handoff.md",
    "report.txt",
)
MIGRATED_FILES = {
    "cockpit.md",
    "proposals.md",
    "memory/preferences.md",
    PROJECT + "/state.md",
    PROJECT + "/journal.md",
    PROJECT + "/handoff.md",
    PROJECT + "/report.txt",
    PROJECT + "/.relink",
    PROJECT + "/memory/domain.md",
    PROJECT + "/memory/schema.md",
    PROJECT + "/memory/codebase.md",
    PROJECT + "/memory/tools.md",
    PROJECT + "/saas-project/.keep",
    PROJECT + "/tools-project/.keep",
    PROJECT + "/repo/src/app.txt",
    PROJECT + "/secrets/metabase.key",
}
COCKPIT_FILE = (
    "---\n"
    "schema_version: 2\n"
    "language: fr\n"
    "plugin_version: 1.6.0\n"
    "dependencies: git, railway, gh\n"
    "---\n"
    "\n"
    "## User\n"
    "- Name: Alex Morgan\n"
    "- Email: alex@example.com\n"
)
PROJECT_STATE_HEADER = "---\nprovider: railway\nonboarding: complete\nonboarding_step: check\n---\n"


def files_of(snapshot):
    return {name for name, (kind, _, _) in snapshot.items() if kind == "file"}


def without_backups(snapshot):
    return {name: entry for name, entry in snapshot.items() if not name.startswith("backups")}


class MigrateStateTest(ScriptTestCase):
    def migrate(self, home=None, **environment):
        return self.run_script("migrate-state.sh", env={"COCKPIT_HOME": home or self.home, **environment})

    def backup_directories(self, home=None):
        backups = os.path.join(home or self.home, "backups")
        return sorted(os.listdir(backups)) if os.path.isdir(backups) else []

    def test_given_a_version_1_state_then_the_app_gets_its_own_folder_and_nothing_is_lost(self):
        self.build_state_v1()
        before = self.snapshot()

        result = self.migrate()
        after = self.snapshot()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, UPDATED)
        self.assertEqual(files_of(without_backups(after)), MIGRATED_FILES)
        self.assertEqual(after["cockpit.md"][2].decode(), COCKPIT_FILE)

        project_state = after[PROJECT + "/state.md"][2].decode()
        self.assertTrue(project_state.startswith(PROJECT_STATE_HEADER + "\n## Profile\n"))
        self.assertNotIn("- User:", project_state)
        self.assertNotIn("- Clone:", project_state)
        self.assertIn("- Project: Acme Studio (11111111-1111-1111-1111-111111111111)", project_state)
        self.assertIn("- Project: Acme Studio tools (22222222-2222-2222-2222-222222222222)", project_state)
        self.assertIn("- 2026-10-08: signup page fails on Safari", project_state)

        for topic in ("domain", "schema", "codebase", "tools"):
            self.assertEqual(after["{}/memory/{}.md".format(PROJECT, topic)][2], IMPORTED + before[topic + ".md"][2])
        self.assertEqual(after["memory/preferences.md"][2], IMPORTED + before["preferences.md"][2])

        for name in ("journal.md", "handoff.md", "report.txt"):
            self.assertEqual(after[PROJECT + "/" + name], before[name])
        self.assertEqual(after["proposals.md"], before["proposals.md"])

        for name in ("saas-project/.keep", "tools-project/.keep", "repo/src/app.txt", "secrets/metabase.key"):
            self.assertEqual(after[PROJECT + "/" + name], before[name])
        self.assertEqual(after[PROJECT + "/secrets/metabase.key"][1], 0o600)
        self.assertEqual(after[PROJECT + "/secrets"][1], 0o700)

        self.assertFalse(self.exists("cockpit-home/.migrating"))
        for leftover in ("state.md", "domain.md", "preferences.md", "journal.md", "repo", "secrets", "saas-project"):
            self.assertFalse(self.exists("cockpit-home/" + leftover), leftover)

    def test_given_a_version_1_state_then_every_root_text_file_is_in_the_backup(self):
        self.build_state_v1()
        before = self.snapshot()

        self.migrate()
        after = self.snapshot()
        backups = self.backup_directories()

        self.assertEqual(len(backups), 1)
        self.assertTrue(backups[0].startswith("v1-"))
        for name in ROOT_TEXT_FILES:
            self.assertEqual(after["backups/{}/{}".format(backups[0], name)], before[name], name)
        for rebuildable in ("repo", "saas-project", "tools-project", "secrets"):
            self.assertNotIn("backups/{}/{}".format(backups[0], rebuildable), after)

    def test_given_a_migration_already_done_then_a_rerun_prints_and_changes_nothing(self):
        self.build_state_v1()
        self.migrate()
        done = self.snapshot()

        rerun = self.migrate()

        self.assertEqual(rerun.returncode, 0, rerun.stderr)
        self.assertEqual(rerun.stdout, "")
        self.assertEqual(self.snapshot(), done)

    def test_given_a_state_without_a_railway_project_yet_then_the_app_is_named_app(self):
        self.write("cockpit-home/state.md", "---\nschema_version: 1\nlanguage: en\nonboarding: in-progress\nonboarding_step: plan\n---\n\n## Profile\n- User: Alex\n")

        result = self.migrate()

        self.assertEqual(result.stdout, UPDATED)
        self.assertTrue(self.exists("cockpit-home/projects/app/state.md"))
        self.assertIn("- User: Alex\n", self.read("cockpit-home/cockpit.md"))
        self.assertFalse(self.exists("cockpit-home/projects/app/.relink"))

    def test_given_a_project_name_with_accents_and_symbols_then_the_folder_name_is_plain(self):
        self.write("cockpit-home/state.md", "---\nschema_version: 1\n---\n\n## SaaS project\n- Project: Caf\u00e9 & Co! (11111111-1111-1111-1111-111111111111)\n")

        result = self.migrate()

        self.assertEqual(result.stdout, UPDATED)
        self.assertTrue(self.exists("cockpit-home/projects/cafe-co/state.md"))

    def test_given_a_state_folder_with_spaces_and_brackets_then_the_migration_still_works(self):
        home = self.path("my home [work]/.cockpit")
        self.build_state_v1(home)

        result = self.migrate(home)

        self.assertEqual(result.stdout, UPDATED)
        self.assertTrue(os.path.isfile(os.path.join(home, "projects", "acme-studio", "secrets", "metabase.key")))

    def test_given_a_state_whose_header_never_closes_then_nothing_is_attempted(self):
        self.write("cockpit-home/state.md", "---\nschema_version: 1\nlanguage: fr\n")
        before = self.snapshot()

        result = self.migrate()

        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertEqual(self.snapshot(), before)

    def test_given_a_mac_without_python_then_the_failure_is_reported_and_version_1_is_left_alone(self):
        self.build_state_v1()
        before = self.snapshot()

        result = self.migrate(PATH=self.isolated_path("dirname", "uname"))

        self.assertIn("migration: failed (python3 is not available)", result.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_given_an_interruption_at_any_step_then_the_next_run_ends_in_the_same_state(self):
        reference_home = self.path("reference")
        self.build_state_v1(reference_home)
        self.migrate(reference_home)
        expected = without_backups(self.snapshot(reference_home))

        for stage in ("backed-up", "built", "renamed", "committed"):
            with self.subTest(stage=stage):
                home = self.path("interrupted-" + stage)
                self.build_state_v1(home)

                interrupted = self.migrate(home, COCKPIT_MIGRATION_KILL_AT=stage)
                self.assertNotEqual(interrupted.returncode, 0)

                old = time.time() - 3600
                os.utime(os.path.join(home, ".migrating"), (old, old))
                resumed = self.migrate(home)

                self.assertEqual(resumed.stdout, UPDATED)
                snapshot = without_backups(self.snapshot(home))
                self.assertEqual(snapshot, expected)
                self.assertFalse(os.path.exists(os.path.join(home, ".migrating")))

    def test_given_a_failure_before_the_commit_point_then_version_1_is_left_byte_for_byte(self):
        for stage in ("backed-up", "built", "renamed"):
            with self.subTest(stage=stage):
                home = self.path("failing-" + stage)
                self.build_state_v1(home)
                before = self.snapshot(home)

                result = self.migrate(home, COCKPIT_MIGRATION_FAIL_AT=stage)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("migration: failed (stopped on purpose after {})".format(stage), result.stdout)
                self.assertEqual(self.snapshot(home), before)

    def test_given_a_file_where_the_projects_folder_should_go_then_the_failure_is_real_and_clean(self):
        self.build_state_v1()
        self.write("cockpit-home/projects", "not a folder")
        before = self.snapshot()

        result = self.migrate()

        self.assertIn("migration: failed (", result.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_given_another_session_is_migrating_then_this_one_leaves_everything_alone(self):
        self.build_state_v1()
        os.makedirs(self.path("cockpit-home/.migrating"))
        before = self.snapshot()

        result = self.migrate(COCKPIT_MIGRATION_LOCK_WAIT="0")

        self.assertIn("migration: failed (another session is migrating the saved setup)", result.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_given_a_state_written_by_a_newer_cockpit_then_it_is_left_untouched(self):
        for name, content in (
            ("cockpit.md", "---\nschema_version: 3\nlanguage: fr\n---\n"),
            ("state.md", "---\nschema_version: 3\nlanguage: fr\n---\n"),
        ):
            with self.subTest(file=name):
                home = self.path("newer-" + name)
                os.makedirs(home)
                with open(os.path.join(home, name), "w", encoding="utf-8") as handle:
                    handle.write(content)
                before = self.snapshot(home)

                result = self.migrate(home)

                self.assertEqual(result.returncode, 3)
                self.assertEqual(result.stdout, NEWER)
                self.assertEqual(self.snapshot(home), before)

    def test_given_no_state_then_nothing_happens(self):
        result = self.migrate()

        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertEqual(self.snapshot(), {})
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `sh tests/scripts/run.sh -k test_migrate_state`
Expected: FAIL (the script does not exist). `sh tests/scripts/run.sh` as a whole still passes for every other file.

- [ ] **Step 5: Write the Python module**

Create `scripts/migrate_state.py`:

```python
import filecmp
import os
import re
import shutil
import sys
import time
import unicodedata
from datetime import datetime, timezone

SCHEMA_VERSION = 2
NEWER_SCHEMA_STATUS = 3
HEADER_LINE_LIMIT = 50
LOCK_NAME = ".migrating"
LOCK_STALE_SECONDS = 600
LOCK_WAIT_SECONDS = 3
DEFAULT_SLUG = "app"
IMPORTED_HEADING = b"## Imported\n\n"
CLONE_LINE = "- Clone: ~/.cockpit/repo"
MOVED_DIRECTORIES = ("saas-project", "tools-project", "repo", "secrets")
LINKED_DIRECTORIES = ("saas-project", "tools-project")
PROJECT_FILES = ("journal.md", "handoff.md", "report.txt")
PROJECT_TOPICS = ("domain", "schema", "codebase", "tools")
USER_HEADER_KEYS = ("language", "plugin_version", "dependencies")
PROJECT_HEADER_KEYS = ("onboarding", "onboarding_step")
KNOWN_HEADER_KEYS = ("schema_version",) + USER_HEADER_KEYS + PROJECT_HEADER_KEYS
LEGACY_ROOT_FILES = (
    "domain.md",
    "schema.md",
    "codebase.md",
    "tools.md",
    "preferences.md",
    "journal.md",
    "handoff.md",
    "report.txt",
    "state.md",
)
USER_LINE = re.compile(r"^- User:[ \t]*(.*?)\r?$")


class MigrationError(Exception):
    pass


def reach(stage, can_fail=True):
    if can_fail and os.environ.get("COCKPIT_MIGRATION_FAIL_AT") == stage:
        raise MigrationError("stopped on purpose after " + stage)

    if os.environ.get("COCKPIT_MIGRATION_KILL_AT") == stage:
        os._exit(70)


def split_header(text):
    lines = text.split("\n")

    if lines[0].rstrip("\r") != "---":
        return None

    for index in range(1, min(len(lines), HEADER_LINE_LIMIT)):
        if lines[index].rstrip("\r") == "---":
            header = [line.rstrip("\r") for line in lines[1:index]]
            return header, "\n".join(lines[index + 1 :])

    return None


def read_header(lines):
    known = {}
    extra = []

    for line in lines:
        key, separator, value = line.partition(":")

        if separator and key in KNOWN_HEADER_KEYS and key not in known:
            known[key] = value.strip()
        else:
            extra.append(line)

    return known, extra


def read_state(path):
    with open(path, encoding="utf-8", errors="surrogateescape", newline="") as handle:
        parsed = split_header(handle.read())

    if parsed is None:
        return None

    known, extra = read_header(parsed[0])
    return known, extra, parsed[1]


def schema_of(known):
    value = known.get("schema_version", "")
    return int(value) if re.fullmatch(r"[0-9]{1,5}", value) else None


def heading_of(line):
    text = line.rstrip("\r")
    return text[3:].strip() if text.startswith("## ") else None


def slug_from(body):
    section = None

    for line in body.split("\n"):
        section = heading_of(line) or section

        if section == "SaaS project" and line.startswith("- Project:"):
            name = re.sub(r"\([^()]*\)\s*$", "", line[len("- Project:") :].rstrip("\r").rstrip())
            plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
            return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-") or DEFAULT_SLUG

    return DEFAULT_SLUG


def split_user(body):
    section = None
    kept = []
    user = None

    for line in body.split("\n"):
        section = heading_of(line) or section
        match = USER_LINE.match(line)

        if section == "Profile" and match and user is None:
            user = match.group(1)
            continue

        if line.rstrip("\r") == CLONE_LINE:
            continue

        kept.append(line)

    return "\n".join(kept), user


def user_lines(user):
    if not user or not user.strip():
        return []

    name, separator, email = user.rpartition(",")

    if separator and name.strip() and "@" in email and " " not in email.strip():
        return ["- Name: " + name.strip(), "- Email: " + email.strip()]

    return ["- User: " + user]


def user_file_text(known, user):
    lines = ["schema_version: {}".format(SCHEMA_VERSION)]
    lines += ["{}: {}".format(key, known[key]) for key in USER_HEADER_KEYS if key in known]

    return "---\n" + "\n".join(lines) + "\n---\n\n## User\n" + "".join(line + "\n" for line in user_lines(user))


def project_file_text(known, extra, body):
    lines = ["provider: railway"]
    lines += ["{}: {}".format(key, known[key]) for key in PROJECT_HEADER_KEYS if key in known]
    lines += extra

    return "---\n" + "\n".join(lines) + "\n---\n" + body


def write_new(path, data, text=False):
    if text:
        handle = open(path, "x", encoding="utf-8", errors="surrogateescape", newline="")
    else:
        handle = open(path, "xb")

    with handle:
        handle.write(data)


def read_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def remove_file(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def remove_if_empty(path):
    try:
        os.rmdir(path)
    except OSError:
        pass


def backup_names(root, partial):
    try:
        names = sorted(os.listdir(os.path.join(root, "backups")))
    except FileNotFoundError:
        return []

    return [name for name in names if name.startswith("v1-") and name.endswith(".partial") == partial]


def latest_backup(root):
    names = backup_names(root, partial=False)
    return os.path.join(root, "backups", names[-1]) if names else None


def remove_unchanged(path, backup):
    if backup is None:
        return

    saved = os.path.join(backup, os.path.basename(path))

    try:
        if os.path.isfile(path) and os.path.isfile(saved) and filecmp.cmp(path, saved, shallow=False):
            os.remove(path)
    except OSError:
        pass


class Lock:
    def __init__(self, root):
        self.path = os.path.join(root, LOCK_NAME)

    def is_stale(self):
        try:
            return time.time() - os.stat(self.path).st_mtime > LOCK_STALE_SECONDS
        except FileNotFoundError:
            return True

    def __enter__(self):
        wait = float(os.environ.get("COCKPIT_MIGRATION_LOCK_WAIT", LOCK_WAIT_SECONDS))
        deadline = time.monotonic() + wait

        while True:
            try:
                os.mkdir(self.path)
                return self
            except FileExistsError:
                pass

            if self.is_stale():
                try:
                    os.rmdir(self.path)
                except FileNotFoundError:
                    pass
                continue

            if time.monotonic() >= deadline:
                raise MigrationError("another session is migrating the saved setup")

            time.sleep(0.2)

    def __exit__(self, *_):
        remove_if_empty(self.path)


class Migration:
    def __init__(self, root, state):
        self.root = root
        self.known, self.extra, body = state
        self.app_body, user = split_user(body)
        self.user_text = user_file_text(self.known, user)
        self.slug = slug_from(body)
        self.project = os.path.join(root, "projects", self.slug)
        self.backup = None

    def at_root(self, *parts):
        return os.path.join(self.root, *parts)

    def in_project(self, *parts):
        return os.path.join(self.project, *parts)

    def discard_leftovers(self):
        for name in MOVED_DIRECTORIES:
            source = self.at_root(name)
            target = self.in_project(name)

            if not os.path.lexists(source) and os.path.lexists(target):
                os.rename(target, source)

        for name in ("state.md", ".relink") + PROJECT_FILES:
            remove_file(self.in_project(name))

        shutil.rmtree(self.in_project("memory"), ignore_errors=True)
        remove_file(self.at_root("memory", "preferences.md"))
        remove_file(self.at_root(".cockpit.md.tmp"))

        for name in backup_names(self.root, partial=True):
            shutil.rmtree(self.at_root("backups", name), ignore_errors=True)

        for directory in (self.at_root("memory"), self.project, self.at_root("projects"), self.at_root("backups")):
            remove_if_empty(directory)

    def roll_back(self):
        self.discard_leftovers()

        if self.backup:
            shutil.rmtree(self.backup, ignore_errors=True)

        remove_if_empty(self.at_root("backups"))

    def back_up(self):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        final = self.at_root("backups", "v1-" + stamp)
        repeat = 1

        while os.path.exists(final):
            repeat += 1
            final = self.at_root("backups", "v1-{}-{}".format(stamp, repeat))

        partial = final + ".partial"

        os.makedirs(self.at_root("backups"), mode=0o700, exist_ok=True)
        os.mkdir(partial, 0o700)

        for name in os.listdir(self.root):
            path = self.at_root(name)

            if os.path.isfile(path) and not os.path.islink(path):
                shutil.copy2(path, partial)

        os.rename(partial, final)
        self.backup = final

    def import_memory(self):
        os.makedirs(self.in_project("memory"))

        for topic in PROJECT_TOPICS:
            source = self.at_root(topic + ".md")

            if os.path.isfile(source):
                write_new(self.in_project("memory", topic + ".md"), IMPORTED_HEADING + read_bytes(source))

        preferences = self.at_root("preferences.md")

        if os.path.isfile(preferences):
            os.makedirs(self.at_root("memory"), exist_ok=True)
            write_new(self.at_root("memory", "preferences.md"), IMPORTED_HEADING + read_bytes(preferences))

    def build(self):
        os.makedirs(self.project, exist_ok=True)
        write_new(self.in_project("state.md"), project_file_text(self.known, self.extra, self.app_body), text=True)
        self.import_memory()

        for name in PROJECT_FILES:
            if os.path.isfile(self.at_root(name)):
                shutil.copy2(self.at_root(name), self.in_project(name))

        if any(os.path.lexists(self.at_root(name)) for name in LINKED_DIRECTORIES):
            write_new(self.in_project(".relink"), b"")

    def move_directories(self):
        for name in MOVED_DIRECTORIES:
            source = self.at_root(name)
            target = self.in_project(name)

            if not os.path.lexists(source):
                continue

            if os.path.lexists(target):
                raise MigrationError("projects/{}/{} already exists".format(self.slug, name))

            os.rename(source, target)

    def commit(self):
        temporary = self.at_root(".cockpit.md.tmp")

        with open(temporary, "w", encoding="utf-8", errors="surrogateescape", newline="") as handle:
            handle.write(self.user_text)
            handle.flush()
            os.fsync(handle.fileno())

        os.rename(temporary, self.at_root("cockpit.md"))

    def clean_up(self):
        for name in LEGACY_ROOT_FILES:
            remove_unchanged(self.at_root(name), self.backup)


def describe(error):
    if isinstance(error, MigrationError):
        text = str(error)
    elif isinstance(error, OSError):
        text = "{} ({})".format(error.strerror or "file error", os.path.basename(error.filename or ""))
    else:
        text = type(error).__name__

    return re.sub(r"[^A-Za-z0-9 ._()/-]", "", text)[:100]


def announce_update():
    print("state: updated to version {}".format(SCHEMA_VERSION))


def migrate(root, state):
    with Lock(root):
        migration = Migration(root, state)

        try:
            migration.discard_leftovers()
            migration.back_up()
            reach("backed-up")
            migration.build()
            reach("built")
            migration.move_directories()
            reach("renamed")
            migration.commit()
        except Exception:
            migration.roll_back()
            raise

        reach("committed", can_fail=False)
        migration.clean_up()

    announce_update()
    return 0


def finish_cleanup(root, state_path):
    backup = latest_backup(root)

    with Lock(root):
        if backup is None or not os.path.isfile(state_path):
            return 0

        state = read_state(state_path)

        if state is None:
            return 0

        migration = Migration(root, state)
        migration.backup = backup
        migration.clean_up()

    announce_update()
    return 0


def announce_newer():
    print("state: written by a newer cockpit, left untouched")
    return NEWER_SCHEMA_STATUS


def run(root):
    cockpit_path = os.path.join(root, "cockpit.md")
    state_path = os.path.join(root, "state.md")

    if os.path.isfile(cockpit_path):
        installed = read_state(cockpit_path)
        schema = schema_of(installed[0]) if installed else None

        if schema is not None and schema > SCHEMA_VERSION:
            return announce_newer()

        legacy = read_state(state_path) if os.path.isfile(state_path) else None

        if legacy is not None and schema_of(legacy[0]) == 1:
            return finish_cleanup(root, state_path)

        return 0

    if not os.path.isfile(state_path):
        return 0

    state = read_state(state_path)
    schema = schema_of(state[0]) if state else None

    if schema is not None and schema > SCHEMA_VERSION:
        return announce_newer()

    if schema != 1:
        return 0

    return migrate(root, state)


def main():
    try:
        return run(sys.argv[1])
    except Exception as error:
        print("migration: failed ({})".format(describe(error)))
        return 0


sys.exit(main())
```

- [ ] **Step 6: Write the wrapper**

Create `scripts/migrate-state.sh`:

```sh
#!/bin/sh
set -eu

if [ "${COCKPIT_TEST:-}" != 1 ]; then
  unset COCKPIT_MIGRATION_FAIL_AT COCKPIT_MIGRATION_KILL_AT COCKPIT_MIGRATION_LOCK_WAIT
fi

state_home=${COCKPIT_HOME:-${HOME:-}/.cockpit}
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)

if [ ! -e "$state_home/state.md" ] && [ ! -e "$state_home/cockpit.md" ]; then
  exit 0
fi

python_is_ready() {
  if [ "$(uname -s)" = Darwin ] && ! xcode-select -p >/dev/null 2>&1; then
    return 1
  fi

  command -v python3 >/dev/null 2>&1
}

if ! python_is_ready; then
  if [ ! -e "$state_home/cockpit.md" ]; then
    printf '%s\n' 'migration: failed (python3 is not available)'
  fi
  exit 0
fi

exec python3 "$script_dir/migrate_state.py" "$state_home"
```

- [ ] **Step 7: Run the tests**

Run: `sh tests/scripts/run.sh -k test_migrate_state`
Expected: `Ran 14 tests in ...s` then `OK`.

Run: `sh tests/scripts/run.sh`
Expected: `Ran 88 tests in ...s` then `OK`.

- [ ] **Step 8: Prove the tests can fail**

Break the rollback on purpose and watch the guard react, then restore it:

Run: `cp scripts/migrate_state.py /tmp/migrate_state.keep && sed -i.bak 's/migration.roll_back()/pass/' scripts/migrate_state.py && sh tests/scripts/run.sh -k test_migrate_state 2>&1 | tail -3; cp /tmp/migrate_state.keep scripts/migrate_state.py && rm -f scripts/migrate_state.py.bak`
Expected: `FAILED (failures=3)`. Then `git status --short scripts` lists only the new files and no `.bak`.

- [ ] **Step 9: Run the migration on every v1 state the evals build**

The 10 eval fixtures build v1 states that must migrate without a word from the user:

Run: `for f in evals/*/fixture.sh; do d=$(mktemp -d); HOME=$d bash "$f" >/dev/null && env -u COCKPIT_HOME HOME=$d sh scripts/session-check.sh | grep -E '^(state:|migration:|active project:|onboarding:)' | tr '\n' ' '; echo; done`
Expected: 10 lines, each `state: updated to version 2 active project: acme onboarding: complete`.

- [ ] **Step 10: Lint and CI glob**

In `.github/workflows/ci.yml`, replace:

```text
      - run: shellcheck scripts/*.sh tests/scripts/*.sh evals/*/fixture.sh
```

with:

```text
      - run: shellcheck scripts/*.sh tests/scripts/*.sh tests/fixtures/*/fixture.sh evals/*/fixture.sh
```

Run: `shellcheck scripts/*.sh tests/scripts/*.sh tests/fixtures/*/fixture.sh evals/*/fixture.sh`
Expected: no output.

- [ ] **Step 11: Commit**

```bash
git add tests/fixtures/state-v1/fixture.sh scripts/migrate-state.sh scripts/migrate_state.py tests/scripts/test_migrate_state.py tests/scripts/support.py .github/workflows/ci.yml
git commit -F - -- tests/fixtures/state-v1/fixture.sh scripts/migrate-state.sh scripts/migrate_state.py tests/scripts/test_migrate_state.py tests/scripts/support.py .github/workflows/ci.yml <<'EOF'
chore(state): add the version 2 migration script and its fixture

migrate-state.sh moves a version 1 setup to projects/<slug>/ behind a
lock, after a backup of the text files, and writes cockpit.md last as
the commit point. Any error before that point undoes the renames and
leaves version 1 as it was; a rerun after an interruption finishes the
job. Nothing calls it yet. Tests run it on tests/fixtures/state-v1.
EOF
```

---

### Task 5: Link the Railway folders again

**Files:**
- Create: `scripts/relink.sh`
- Create: `tests/scripts/test_relink.py`
- Modify: `docs/verified-facts.md`

**Interfaces:**
- Consumes: `project-directory.sh --project` from Task 1, the `.relink` marker and the `## SaaS project` and `## Tools project` sections of an app's `state.md` (Task 4 writes the marker and keeps the sections).
- Produces: `sh scripts/relink.sh [--project <slug>]`. With no `.relink` marker in the app folder it prints `The Railway links are already up to date.` and exits 0. Otherwise, from the app folder: `railway link -p <saas project id> -e <production environment> -s <app service>` run inside `saas-project/`, and `railway link -p <tools project id> -e production` run inside `tools-project/` (only for folders that exist), then removes the marker and prints `The Railway links are rebuilt.`. A failure prints a message that names what to check on stderr, exits 1 and keeps the marker. Ids and names that are empty or start with `-` are refused before `railway` runs. `RAILWAY_BIN` overrides the CLI when `COCKPIT_TEST=1`.

- [ ] **Step 1: Check the CLI behaviour `relink.sh` relies on (manual, with a Railway 5.x binary)**

`relink.sh` assumes that a folder moved after `railway link` reports no linked project, that `railway link -p <id> -e <environment>` re-links it with no terminal, and that two folders keep their own project. Facts only say it for CLI 4.68 reading `~/.railway/config.json`. Check it on 5.x with two throwaway projects in the owner's own workspace, never a client project.

Get a 5.x binary the way `docs/verified-facts.md` did (a release binary of `railwayapp/cli`, run by absolute path, nothing installed): list the assets with `gh release view --repo railwayapp/cli --json assets --jq '.assets[].name'`, download the one for the machine with `gh release download --repo railwayapp/cli --pattern '<asset name>' --dir /tmp/railway5`, unpack it, and `chmod +x` the binary. Then, with `<workspace>` the owner's workspace name (`railway whoami` lists it):

```bash
RAILWAY=/tmp/railway5/railway
"$RAILWAY" --version </dev/null
WORK=$(mktemp -d)
mkdir "$WORK/a" "$WORK/b"
(cd "$WORK/a" && "$RAILWAY" init -n cockpit-relink-probe-a -w "<workspace>" </dev/null)
(cd "$WORK/b" && "$RAILWAY" init -n cockpit-relink-probe-b -w "<workspace>" </dev/null)
id_of() { "$RAILWAY" list --json </dev/null | python3 -c 'import json,sys; print(next(p["id"] for p in json.load(sys.stdin) if p["name"] == sys.argv[1]))' "$1"; }
ID_A=$(id_of cockpit-relink-probe-a)
mv "$WORK/a" "$WORK/a-moved"
(cd "$WORK/a-moved" && "$RAILWAY" status --json </dev/null; echo "status after the move: exit $?")
(cd "$WORK/a-moved" && "$RAILWAY" link -p "$ID_A" -e production </dev/null; echo "link: exit $?")
(cd "$WORK/a-moved" && "$RAILWAY" status --json </dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["name"])')
(cd "$WORK/b" && "$RAILWAY" status --json </dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["name"])')
```

Expected, in this order: `railway 5.` followed by a version; the status in the moved folder fails (no linked project) with a non-zero exit; `link: exit 0`; then `cockpit-relink-probe-a`, then `cockpit-relink-probe-b`.

Clean up: delete the two probe projects from the Railway dashboard (`railway open -p` in a probe folder prints its address), then `trash "$WORK"`.

If the move did not lose the link, or the link needs a terminal, or the two folders cross over: stop here. Do not write `relink.sh`. Report the output to the owner: the fallback is that the session asks Claude to follow the Railway step of `onboarding.md`, and `repair.md` gets that row instead of `relink.sh`.

If it all matched, record it in `docs/verified-facts.md`. First the facts of the 4.68 config and the one assumption that stays open:

In `docs/verified-facts.md`, replace:

```text
## Not verified
```

with:

```text
## State layout v2 (checked 2026-10-09 by a real run)

- Railway keeps the link of a folder in its own config, not in the folder: `~/.railway/config.json` (CLI 4.68.0) has a `projects` object keyed by absolute directory path. Each entry holds `project`, `name`, `environment`, `environmentName`, `service` and `projectPath`. A moved folder is therefore no longer linked.
- Two directories linked to two different Railway projects coexist in that file (CLI 4.68.0).

## Not verified
```

In `docs/verified-facts.md`, replace:

```text
- `railway link` with all of `-p -e -s -w` and no TTY; `railway init -n -w` outside a terminal; a second linked project in another directory.
```

with:

```text
- `railway link` with all of `-p -e -s -w` and no TTY; `railway init -n -w` outside a terminal.
- The environment of a tools project created by `railway init` is `production`: `relink.sh` links `tools-project/` with `-e production`.
```

Then add under the `## State layout v2` heading of that file one more bullet with the version `--version` printed: `- Railway CLI <that version>: a folder moved after railway link reports no linked project; railway link -p <id> -e production run in the moved folder, with no terminal, links it again (exit 0); a second folder linked to another project keeps its own project.`

- [ ] **Step 2: Write the failing tests**

Create `tests/scripts/test_relink.py`:

```python
from support import ScriptTestCase

SAAS_ID = "11111111-1111-1111-1111-111111111111"
TOOLS_ID = "22222222-2222-2222-2222-222222222222"
APP_STATE = (
    "---\nprovider: railway\nonboarding: complete\nonboarding_step: check\n---\n\n"
    "## SaaS project\n"
    "- Project: Acme Studio ({})\n"
    "- Production environment: production\n"
    "- App service: web, repository acme/app, deployed branch main\n"
    "- Postgres service: Postgres\n\n"
    "## Tools project\n"
    "- Project: Acme Studio tools ({})\n"
).format(SAAS_ID, TOOLS_ID)


class RelinkTest(ScriptTestCase):
    def setUp(self):
        super().setUp()
        self.write_v2_state("acme-studio")
        self.write("cockpit-home/projects/acme-studio/state.md", APP_STATE)
        self.write("cockpit-home/projects/acme-studio/saas-project/.keep", "")
        self.write("cockpit-home/projects/acme-studio/tools-project/.keep", "")
        self.write("cockpit-home/projects/acme-studio/.relink", "")
        self.log = self.path("railway.log")

    def railway_records(self, exit_code=0):
        self.install_fake_railway('{ pwd; echo "$@"; } >>"' + self.log + '"\nexit ' + str(exit_code) + "\n")

    def relink(self, *arguments):
        return self.run_script("relink.sh", *arguments)

    def test_given_the_folders_were_moved_then_each_one_is_linked_again_and_the_marker_goes(self):
        self.railway_records()
        project = self.path("cockpit-home/projects/acme-studio")

        result = self.relink("--project", "acme-studio")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.read("railway.log").splitlines(),
            [
                project + "/saas-project",
                "link -p {} -e production -s web".format(SAAS_ID),
                project + "/tools-project",
                "link -p {} -e production".format(TOOLS_ID),
            ],
        )
        self.assertFalse(self.exists("cockpit-home/projects/acme-studio/.relink"))

    def test_given_railway_refuses_then_the_marker_stays_and_the_error_says_what_to_check(self):
        self.railway_records(exit_code=1)

        result = self.relink()

        self.assertEqual(result.returncode, 1)
        self.assertIn("railway whoami", result.stderr)
        self.assertTrue(self.exists("cockpit-home/projects/acme-studio/.relink"))

    def test_given_nothing_to_refresh_then_railway_is_not_called(self):
        self.railway_records()
        self.relink()
        self.write("railway.log", "")

        result = self.relink()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read("railway.log"), "")

    def test_given_an_id_that_could_pass_for_an_option_then_railway_is_not_called(self):
        self.railway_records()
        self.write("cockpit-home/projects/acme-studio/state.md", APP_STATE.replace(SAAS_ID, "--help"))

        result = self.relink()

        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.exists("railway.log"))
        self.assertTrue(self.exists("cockpit-home/projects/acme-studio/.relink"))
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `sh tests/scripts/run.sh -k test_relink`
Expected: FAIL (the script does not exist).

- [ ] **Step 4: Write the script**

Create `scripts/relink.sh`:

```sh
#!/bin/sh
set -eu

if [ "${COCKPIT_TEST:-}" != 1 ]; then
  unset RAILWAY_BIN
fi

PATH=$PATH:${HOME:-}/.railway/bin:${HOME:-}/.local/bin
railway_bin=${RAILWAY_BIN:-railway}
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
usage='Usage: relink.sh [--project <slug>]'
tools_environment=production
project=

fail() {
  printf '%s\n' "$1" >&2
  exit "${2:-1}"
}

while [ "$#" -gt 0 ]; do
  case $1 in
    --project)
      if [ "$#" -lt 2 ]; then
        fail "$usage" 2
      fi

      project=$2
      shift 2
      ;;
    *)
      fail "$usage" 2
      ;;
  esac
done

project_directory=$(sh "$script_dir/project-directory.sh" --project "$project") || exit 1
state_file=$project_directory/state.md
marker=$project_directory/.relink

if [ ! -e "$marker" ]; then
  printf '%s\n' "The Railway links are already up to date."
  exit 0
fi

if [ ! -f "$state_file" ]; then
  fail "The saved setup of this app cannot be read ($state_file), so its Railway links cannot be rebuilt."
fi

section_line() {
  sed -n "/^## $1\$/,/^## /{/^$2/p;}" "$state_file" | sed -n '1p' | tr -d '\r'
}

is_identifier() {
  case $1 in
    '' | -* | *[!0-9A-Za-z._-]*) return 1 ;;
    *) return 0 ;;
  esac
}

is_name() {
  case $1 in
    '' | -*) return 1 ;;
    *) return 0 ;;
  esac
}

project_id_of() {
  line=$(section_line "$1" '- Project:')
  id=${line##*\(}
  id=${id%\)*}

  if ! is_identifier "$id"; then
    return 1
  fi

  printf '%s' "$id"
}

value_of() {
  line=$(section_line "$1" "$2")
  value=${line#"$2"}
  value=${value#"${value%%[! ]*}"}
  value=${value%%,*}
  value=${value%"${value##*[! ]}"}

  if ! is_name "$value"; then
    return 1
  fi

  printf '%s' "$value"
}

link_folder() {
  if ! (cd "$project_directory/$1" && shift && "$railway_bin" link "$@" >/dev/null 2>&1); then
    fail "Railway did not link the folder '$1'. Check that 'railway whoami' answers and that this account is a member of the project, then run this again."
  fi
}

if [ -d "$project_directory/saas-project" ]; then
  saas_id=$(project_id_of 'SaaS project') || fail "The SaaS project of $state_file has no readable id, so its folder cannot be linked again."
  production=$(value_of 'SaaS project' '- Production environment:') || fail "The production environment of $state_file cannot be read, so the SaaS folder cannot be linked again."
  app_service=$(value_of 'SaaS project' '- App service:') || fail "The app service of $state_file cannot be read, so the SaaS folder cannot be linked again."

  link_folder saas-project -p "$saas_id" -e "$production" -s "$app_service"
fi

if [ -d "$project_directory/tools-project" ]; then
  tools_id=$(project_id_of 'Tools project') || fail "The tools project of $state_file has no readable id, so its folder cannot be linked again."

  link_folder tools-project -p "$tools_id" -e "$tools_environment"
fi

rm -f "$marker"
printf '%s\n' "The Railway links are rebuilt."
```

- [ ] **Step 5: Run the suite and lint**

Run: `sh tests/scripts/run.sh`
Expected: `Ran 92 tests in ...s` then `OK`.

Run: `shellcheck scripts/*.sh`
Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add scripts/relink.sh tests/scripts/test_relink.py docs/verified-facts.md
git commit -F - -- scripts/relink.sh tests/scripts/test_relink.py docs/verified-facts.md <<'EOF'
chore(scripts): add relink.sh to link the Railway folders again

Railway keys a folder link by its absolute path, so the folders the
migration moves lose theirs. relink.sh runs railway link again for
them from the ids in state.md and removes the .relink marker. Nothing
calls it yet. The facts it relies on are recorded in verified-facts.
EOF
```

---

### Task 6: The skills describe version 2

**Files:**
- Modify: `skills/cockpit/references/state-schema.md` (rewrite)
- Modify: `skills/cockpit/SKILL.md`, `skills/cockpit/references/onboarding.md`, `memory.md`, `repair.md`

**Interfaces:**
- Consumes: the placeholder of Task 3, the context lines of Task 2 and Task 4, `relink.sh` of Task 5.
- Produces: the written contract of layout version 2 in `state-schema.md` ("Current `schema_version`: 2"), including the legacy mapping table that every `$PROJECT/...` path relies on in legacy mode. `SKILL.md` step 3 says what Claude does with each of the four new session lines, and a "Where the files are" section. Onboarding on a Mac with no saved setup creates `~/.cockpit/cockpit.md` and `~/.cockpit/projects/app/state.md`. There is no memory script yet: `memory.md` keeps its prose procedure at the new paths and says how to treat a `## Imported` section.

- [ ] **Step 1: Rewrite the schema**

Replace the whole content of `skills/cockpit/references/state-schema.md` with:

````markdown
# State schema

Current `schema_version`: 2.

Everything lives in `~/.cockpit/`. Only Claude writes there. No personal data of end users, no secret.

## Layout

```
~/.cockpit/
  cockpit.md                 the user: schema_version, language, plugin_version, dependencies, name, email
  memory/preferences.md      how this user wants answers
  proposals.md               changes wanted in the plugin
  projects/<slug>/           one app, written $PROJECT in the references
    state.md                 onboarding status, profile, plan, SaaS project, code, tools project, tools, open escalations
    memory/                  domain.md, schema.md, codebase.md, tools.md
    journal.md  handoff.md  report.txt
    saas-project/  tools-project/  repo/  secrets/
  backups/v1-<timestamp>/    text files of the previous layout, kept by the migration
```

- `<slug>`: the Railway project name in lowercase, reduced to `a-z`, `0-9` and `-`. `app` when no Railway project is known yet, which is the case for a Mac that starts with no saved setup. It never changes afterwards: the display name stays in `state.md`.
- `$PROJECT` is the `project directory:` line of the session context.

## cockpit.md

The header is read by a script at every session start. Keep it exactly in this shape: flat keys, one per line, no quotes, no nesting.

```
---
schema_version: 2
language: fr
plugin_version: 1.6.0
dependencies: git, railway, gh
---

## User
- Name: <name>
- Email: <email>
```

- `schema_version`: lives here only.
- `language`: language code of the user.
- `plugin_version`: the plugin version the user was last told about, from the session context. Written at the end of onboarding and after each "what is new".
- `dependencies`: command names of the plan, comma separated: `git`, `railway`, `gh`, `node`.
- `User`: the name and the email the user signs changes with. A line that could not be split into a name and an email by the migration stays as `- User: <text>`.

## state.md of an app

Same rules for the header: flat keys, one per line.

```
---
provider: railway
onboarding: in-progress
onboarding_step: github
---
```

- `provider`: `railway`, the only value today. Nothing reads it yet.
- `onboarding`: `in-progress` or `complete`.
- `onboarding_step`: the next step to run, not the last one finished, one of `profile`, `plan`, `dependencies`, `railway`, `backups`, `settings`, `github`, `tools`, `discovery`, `check`.

The body below the header uses these sections, in this order. Leave a section empty until it is known. A tool line without `project` means `tools`.

```
## Profile
- Usages: tools, app changes, health, diagnosis
- Tools wanted: metabase (reads app data), n8n
- Developer: <name>, <github handle or email>, channel: github | email | none

## Plan
- <step>: done | pending | failed twice (<date>, <reason>)

## Dependencies
- railway 5.64.1
- gh 2.102.0

## SaaS project
- Project: <name> (<id>)
- Production environment: <name>
- App service: <name>, repository <owner/repo>, deployed branch <branch>
- Postgres service: <name>
- Test environment: <name>, branch <branch>, URL <url> | none
- Backups: schedule <daily, weekly>, first backup <date>
- Spending alert: <amount> USD per month | none

## Code
- Merge policy: ask-me | developer-reviews

## Tools project
- Project: <name> (<id>)

## Tools
- <tool>: project <tools | app>, template <code>, services <names>, URL <url>, driven by <mcp | api | user>, app data <connected | none>

## Open escalations
- <date>: <subject>, <link>
```

The clone of the app is always `$PROJECT/repo`, so no line records it.

## Other files

| File | Content | Language |
|---|---|---|
| `$PROJECT/memory/domain.md` | Business terms mapped to tables, columns, statuses, rules | user's |
| `$PROJECT/memory/schema.md` | What each table is for, traps, sensitive tables | user's |
| `$PROJECT/memory/codebase.md` | Stack, where things live, conventions, files that always need a developer | user's |
| `$PROJECT/memory/tools.md` | What was built in each tool, for which question | user's |
| `~/.cockpit/memory/preferences.md` | Answer format, figures followed, habits | user's |
| `$PROJECT/journal.md` | One dated line per change, merge, escalation, memory write, a change that can be reversed ends with `undo:` and the way back | user's |
| `~/.cockpit/proposals.md` | Changes wanted in the plugin: date, what happened, what should change, why | English |

A memory file can start with a `## Imported` section: text carried over untouched from the previous layout.

Managed by the scripts and by onboarding, never edited by hand: the directories `saas-project/` (linked to the SaaS project, for reading), `tools-project/` (linked to the tools project), `repo/` (clone of the app) and `secrets/` (API keys of tools, mode 600) of the app, its file `report.txt`, and `backups/`. `handoff.md` holds the last hand-off, written by `escalation.md` and overwritten each time. `.relink` in the app folder is a marker left by the migration: the Railway links of its folders are to refresh (`relink.sh`).

## Version 1 layout (legacy mode)

Before version 2 everything sat flat in `~/.cockpit/`, for one app. The session check migrates it by itself. While it has not (`active project: legacy` in the session context), `$PROJECT` is `~/.cockpit/` itself and the paths of this file map like this:

| Version 2 | Version 1 |
|---|---|
| `cockpit.md` (settings, name, email) | the header and the `Profile` section of `state.md` |
| `$PROJECT/state.md` | `~/.cockpit/state.md` |
| `$PROJECT/memory/<topic>.md` | `~/.cockpit/<topic>.md` |
| `~/.cockpit/memory/preferences.md` | `~/.cockpit/preferences.md` |
| every other `$PROJECT/...` path | the same name in `~/.cockpit/` |

The version 1 header of `state.md` holds `schema_version: 1`, `language`, `onboarding`, `onboarding_step`, `plugin_version` and `dependencies`, and its `Profile` section has a `User: <name>, <email>` line and the `Code` section a `Clone: ~/.cockpit/repo` line.

## Migration

`scripts/migrate-state.sh` moves a version 1 setup to version 2. The session check runs it before reading anything, so Claude never runs it: the session context reports the result and `SKILL.md` says what to do with each line. A change to this layout bumps `schema_version` above and extends `scripts/migrate_state.py` in the same commit.
````

- [ ] **Step 2: Save the replacement script**

Save this as `/tmp/cockpit-task6.py` (outside the repo, never committed):

```python
import pathlib
import sys

ROOT = pathlib.Path(sys.argv[1])

WHERE_THE_FILES_ARE = """## Where the files are

`$PROJECT` holds everything that belongs to the active app, `~/.cockpit/` everything that belongs to the user.

| File | Holds |
|---|---|
| `~/.cockpit/cockpit.md` | `language`, `plugin_version`, `dependencies`, name and email |
| `~/.cockpit/memory/preferences.md` | how the user wants answers |
| `~/.cockpit/proposals.md` | changes wanted in the plugin |
| `$PROJECT/state.md` | onboarding status, profile, plan, SaaS project, tools |
| `$PROJECT/memory/` | `domain.md`, `schema.md`, `codebase.md`, `tools.md` |
| `$PROJECT/journal.md`, `handoff.md`, `report.txt` | journal, last hand-off, last report |
| `$PROJECT/saas-project/`, `tools-project/`, `repo/`, `secrets/` | linked folders, clone of the app, tool keys |

A file named without a path in the references (`state.md`, `journal.md`, `domain.md`) is in `$PROJECT`. When the session context says `active project: legacy`, the setup has not moved to the new layout yet: `$PROJECT` is `~/.cockpit/` itself, everything sits flat there and `state.md` also holds the user's settings (`references/state-schema.md`, "Version 1 layout"). Never create `cockpit.md` or a `projects/` folder in that mode.

"""

SETUP_LINES = """3. The session context says something about the saved setup:
   - `state: updated to version 2`: the setup moved to the new layout and nothing was lost. Say so in one sentence and add a dated line to `$PROJECT/journal.md`.
   - `migration: failed (<reason>)`: the setup still works as it was. Say in one sentence that the update of the saved setup will be tried again, and write the reason to `~/.cockpit/proposals.md`, in English. Move no file yourself.
   - `state: written by a newer cockpit, left untouched`: write nothing in `~/.cockpit/` this session. Say in one sentence that the saved setup comes from a newer version of cockpit and that updating the plugin fixes it.
   - `railway links: to refresh`: run `sh $SCRIPTS/relink.sh` before the first Railway command of the session. It says nothing on success. If it fails, follow `references/repair.md`."""

REPLACEMENTS = [
    (
        "skills/cockpit/SKILL.md",
        "The `state directory:` line names `~/.cockpit/`, for what belongs to the user.",
        "The `state directory:` line names `~/.cockpit/`, for what belongs to the user. Where each file lives: \"Where the files are\" below.",
        1,
    ),
    (
        "skills/cockpit/SKILL.md",
        "3. `schema_version` lower than the one in `references/state-schema.md`: migrate as described there.",
        SETUP_LINES,
        1,
    ),
    (
        "skills/cockpit/SKILL.md",
        "then write the new `plugin_version` in the header of `state.md`.",
        "then write the new `plugin_version` in the header of `cockpit.md`.",
        1,
    ),
    (
        "skills/cockpit/SKILL.md",
        "Their language is the `language` field of `state.md`",
        "Their language is the `language` field of `cockpit.md`",
        1,
    ),
    (
        "skills/cockpit/SKILL.md",
        "6. Read the state files the request touches (`domain.md`, `schema.md`, `codebase.md`, `tools.md`, `preferences.md`) before exploring anything.",
        "6. Read the memory files the request touches (`domain.md`, `schema.md`, `codebase.md`, `tools.md` in `$PROJECT/memory/`, `preferences.md` in `~/.cockpit/memory/`) before exploring anything.",
        1,
    ),
    (
        "skills/cockpit/SKILL.md",
        "## Who you are talking to\n",
        WHERE_THE_FILES_ARE + "## Who you are talking to\n",
        1,
    ),
    (
        "skills/cockpit/SKILL.md",
        "| `github-login.sh` | GitHub sign-in in the browser |",
        "| `github-login.sh` | GitHub sign-in in the browser |\n| `relink.sh` | Links the Railway folders of the app again after the saved setup moved |",
        1,
    ),
    (
        "skills/cockpit/references/onboarding.md",
        "Create `~/.cockpit/state.md` from `state-schema.md` as soon as the language is known.",
        "Create `~/.cockpit/cockpit.md` and `$PROJECT/state.md` from `state-schema.md` as soon as the language is known. On a Mac with no saved setup `$PROJECT` is `~/.cockpit/projects/app`.",
        1,
    ),
    (
        "skills/cockpit/references/onboarding.md",
        "Record the answers under `profile` in `state.md`.",
        "Record the answers under `profile` in `state.md`, except their name and email: those go to the `User` section of `cockpit.md`.",
        1,
    ),
    (
        "skills/cockpit/references/onboarding.md",
        "One confirmation. Record the plan.",
        "One confirmation. Record the plan, and its dependencies in the `dependencies` header of `cockpit.md`.",
        1,
    ),
    (
        "skills/cockpit/references/onboarding.md",
        "with the user's name and email from the profile",
        "with the user's name and email from `cockpit.md`",
        1,
    ),
    (
        "skills/cockpit/references/onboarding.md",
        "Set `onboarding: complete` and `plugin_version` to the version of the session context.",
        "Set `onboarding: complete` in `state.md`, and `plugin_version` in `cockpit.md` to the version of the session context.",
        1,
    ),
    (
        "skills/cockpit/references/memory.md",
        "What Claude learns at this client lives in `~/.cockpit/`.",
        "What Claude learns at this client lives in `~/.cockpit/`: about an app in `$PROJECT/memory/`, about the user in `~/.cockpit/memory/`.",
        1,
    ),
    ("skills/cockpit/references/memory.md", "| `domain.md` |", "| `$PROJECT/memory/domain.md` |", 1),
    ("skills/cockpit/references/memory.md", "| `schema.md` |", "| `$PROJECT/memory/schema.md` |", 1),
    ("skills/cockpit/references/memory.md", "| `codebase.md` |", "| `$PROJECT/memory/codebase.md` |", 1),
    ("skills/cockpit/references/memory.md", "| `tools.md` |", "| `$PROJECT/memory/tools.md` |", 1),
    ("skills/cockpit/references/memory.md", "| `preferences.md` |", "| `~/.cockpit/memory/preferences.md` |", 1),
    (
        "skills/cockpit/references/memory.md",
        "Anything that changed something (deployment",
        "In legacy mode (`state-schema.md`) the topic files sit directly in `$PROJECT` and `preferences.md` in `~/.cockpit/`. A memory file can start with a `## Imported` section: text carried over untouched from the previous layout. Write new notes in a `## Notes` section above it and leave the imported text as it is, unless the user corrects it.\n\nAnything that changed something (deployment",
        1,
    ),
    (
        "skills/cockpit/references/repair.md",
        "rm -rf ~/Desktop/cockpit-memory/secrets ~/Desktop/cockpit-memory/repo`",
        "find ~/Desktop/cockpit-memory \\( -name secrets -o -name repo \\) -type d -prune -exec rm -rf {} +`",
        1,
    ),
    (
        "skills/cockpit/references/repair.md",
        "| `gh auth status --hostname github.com`, when GitHub is in the plan |",
        "| `railway links: to refresh` in the session context | the folders moved with the saved setup | `sh $SCRIPTS/relink.sh` |\n| `gh auth status --hostname github.com`, when GitHub is in the plan |",
        1,
    ),
]

failures = []
for relative, old, new, expected in REPLACEMENTS:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        failures.append("{}: expected {} of {!r}, found {}".format(relative, expected, old[:60], count))
        continue
    path.write_text(text.replace(old, new), encoding="utf-8")

if failures:
    print("\n".join(failures))
    sys.exit(1)
print("{} replacements applied".format(len(REPLACEMENTS)))
```

- [ ] **Step 3: Apply it from the repo root**

Run: `python3 /tmp/cockpit-task6.py .`
Expected: `21 replacements applied`

- [ ] **Step 4: Check**

Run: `grep -rn --exclude=state-schema.md '~/\.cockpit/\(saas-project\|tools-project\|repo\|secrets\|journal\|handoff\|report\|state\.md\)' skills`
Expected: no output.

Run: `grep -rn 'schema_version' skills | cut -c1-120`
Expected: only lines in `state-schema.md`.

Run: `git diff --stat -- skills`
Expected: 5 files changed here (the 4 edited ones and the schema), all under `skills/`.

- [ ] **Step 5: Commit**

```bash
git add skills/cockpit/references/state-schema.md skills/cockpit/SKILL.md skills/cockpit/references/onboarding.md skills/cockpit/references/memory.md skills/cockpit/references/repair.md
git commit -F - -- skills/cockpit/references/state-schema.md skills/cockpit/SKILL.md skills/cockpit/references/onboarding.md skills/cockpit/references/memory.md skills/cockpit/references/repair.md <<'EOF'
docs(skills): describe the version 2 layout in the references

state-schema.md now describes one folder per app, the user file and
the legacy mode of the old layout; the prose migration section is
replaced by a pointer to the script. SKILL.md says what to do with
the new session lines, memory.md and onboarding.md use the new paths,
and the Desktop copy of repair.md no longer leaks nested secrets.
EOF
```

---

### Task 7: The session check migrates, and reads both layouts

**Files:**
- Modify: `scripts/session-check.sh` (replace the whole file)
- Modify: `tests/scripts/test_session_check.py`

**Interfaces:**
- Consumes: `migrate-state.sh` (Task 4, status 3 means newer), `project-directory.sh` (Task 1, status 4 means several apps), `health-check.sh --project` (Task 2), the `.relink` marker (Task 4).
- Produces: the final session context, in this order. `cockpit session context`, `plugin version:`, `scripts directory:`, `state directory:`, then the migration line if any (`state: updated to version 2`, `migration: failed (<reason>)`; on `state: written by a newer cockpit, left untouched` nothing else follows but the last line), `active project: <slug>`, `project directory: <path>`, `railway links: to refresh` when the app folder holds `.relink`, then the existing lines (`state schema version:` and `language:` from `cockpit.md`, `onboarding:` from the app's `state.md`, `dependency ...`, `health:`, `plugin version changed:`), always ending with `Load the cockpit skill before answering the first request of this session.` Slug `legacy` and project directory = state directory while `cockpit.md` does not exist. Several apps: `active project: none`, a `note:` line, `state schema version:`, `language:` and `dependency` lines, no `onboarding:`. A user file with no app folder yet: `active project: app` and `onboarding: in progress, step reached: profile`.

- [ ] **Step 1: Add the tests**

Append to `class SessionCheckLayoutTest` in `tests/scripts/test_session_check.py` (the class created in Task 2):

```python
    def test_given_a_version_1_state_then_it_is_migrated_once_and_the_session_runs_on_the_new_layout(self):
        self.build_state_v1()

        first = self.lines()
        second = self.lines()

        for line in (
            "state: updated to version 2",
            "active project: acme-studio",
            "project directory: " + self.home + "/projects/acme-studio",
            "railway links: to refresh",
            "state schema version: 2",
            "language: fr",
            "onboarding: complete",
            "health: not checked, Railway did not answer (sign-in expired or no network)",
        ):
            self.assertIn(line, first)
        self.assertNotIn("state: updated to version 2", second)
        self.assertIn("railway links: to refresh", second)

    def test_given_a_failed_migration_then_the_session_runs_on_the_version_1_state_as_before(self):
        self.build_state_v1()
        before = self.snapshot()

        lines = self.lines(COCKPIT_MIGRATION_FAIL_AT="built")

        self.assertIn("migration: failed (stopped on purpose after built)", lines)
        self.assertIn("active project: legacy", lines)
        self.assertIn("project directory: " + self.home, lines)
        self.assertIn("state schema version: 1", lines)
        self.assertIn("onboarding: complete", lines)
        self.assertNotIn("railway links: to refresh", lines)
        self.assertEqual(self.snapshot(), before)

    def test_given_a_state_from_a_newer_cockpit_then_nothing_is_read_or_changed(self):
        self.write("cockpit-home/cockpit.md", "---\nschema_version: 3\nlanguage: fr\n---\n")
        before = self.snapshot()

        result = self.check()

        self.assertEqual(result.returncode, 0)
        self.assertIn("state: written by a newer cockpit, left untouched", result.stdout)
        for line in ("active project", "language:", "onboarding:", "health:"):
            self.assertNotIn(line, result.stdout)
        self.assertEqual(result.stdout.splitlines()[-1], "Load the cockpit skill before answering the first request of this session.")
        self.assertEqual(self.snapshot(), before)

    def test_given_a_version_2_state_with_one_app_then_that_app_is_the_active_one(self):
        self.write_v2_state("acme-studio", onboarding="in-progress")

        lines = self.lines()

        self.assertIn("active project: acme-studio", lines)
        self.assertIn("project directory: " + self.home + "/projects/acme-studio", lines)
        self.assertIn("state schema version: 2", lines)
        self.assertIn("language: en", lines)
        self.assertIn("onboarding: in progress, step reached: check", lines)
        self.assertNotIn("railway links: to refresh", lines)

    def test_given_a_user_file_and_no_app_folder_yet_then_the_onboarding_resumes_at_the_profile(self):
        self.write_v2_state()

        lines = self.lines()

        self.assertIn("active project: app", lines)
        self.assertIn("onboarding: in progress, step reached: profile", lines)

    def test_given_several_apps_then_no_app_is_chosen_for_the_session(self):
        self.write_v2_state("acme-studio", "beta-shop")

        lines = self.lines()

        self.assertIn("active project: none", lines)
        self.assertFalse(any(line.startswith("project directory:") for line in lines))
        self.assertIn("state schema version: 2", lines)
        self.assertFalse(any(line.startswith("onboarding:") for line in lines))
```

- [ ] **Step 2: Run them to verify they fail**

Run: `sh tests/scripts/run.sh -k SessionCheckLayoutTest`
Expected: `FAILED (failures=6)`, the six new tests (nothing migrates yet and version 2 is not read).

- [ ] **Step 3: Replace the script**

Replace the whole content of `scripts/session-check.sh` with:

```sh
#!/bin/sh
set -eu

state_home=${COCKPIT_HOME:-${HOME:-}/.cockpit}
header_line_limit=50
carriage_return=$(printf '\r')
newer_schema_status=3
several_apps_status=4

trim() {
  trimmed=$1
  trimmed=${trimmed#"${trimmed%%[! ]*}"}
  trimmed=${trimmed%"${trimmed##*[! ]}"}
  printf '%s' "$trimmed"
}

state_value() {
  in_header=0
  lines_read=0

  if [ ! -f "$2" ] || [ ! -r "$2" ]; then
    return 0
  fi

  while IFS= read -r line || [ -n "$line" ]; do
    lines_read=$((lines_read + 1))

    if [ "$lines_read" -gt "$header_line_limit" ]; then
      break
    fi

    line=${line%"$carriage_return"}

    if [ "$line" = '---' ]; then
      if [ "$in_header" = 1 ]; then
        break
      fi
      in_header=1
      continue
    fi

    if [ "$in_header" = 0 ]; then
      break
    fi

    case $line in
      "$1":*)
        trim "${line#"$1":}"
        break
        ;;
    esac
  done <"$2"
}

known_schema_version() {
  case $1 in
    '' | *[!0-9]* | ??????*) printf 'unknown' ;;
    *) printf '%s' "$1" ;;
  esac
}

known_language() {
  case $1 in
    [a-z][a-z] | [a-z][a-z]-[A-Za-z][A-Za-z]) printf '%s' "$1" ;;
    *) printf 'unknown' ;;
  esac
}

known_step() {
  case $1 in
    profile | plan | dependencies | railway | backups | settings | github | tools | discovery | check) printf '%s' "$1" ;;
    *) printf 'unknown' ;;
  esac
}

known_version() {
  case $1 in
    '' | *[!A-Za-z0-9.+-]* | ????????????????????????????????*) printf 'unknown' ;;
    *) printf '%s' "$1" ;;
  esac
}

known_slug() {
  case $1 in
    '' | *[!a-z0-9-]*) printf 'unknown' ;;
    *) printf '%s' "$1" ;;
  esac
}

scripts_directory() {
  CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P
}

plugin_version() {
  manifest=$1/../.claude-plugin/plugin.json

  if [ -f "$manifest" ]; then
    sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$manifest" | sed -n '1p'
  fi
}

dependency_status() {
  if [ "$1" = git ] && [ "$(uname -s)" = Darwin ]; then
    if xcode-select -p >/dev/null 2>&1; then
      printf 'present'
    else
      printf 'missing'
    fi
    return 0
  fi

  if PATH="$PATH:${HOME:-}/.railway/bin:${HOME:-}/.local/bin" command -v "$1" >/dev/null 2>&1; then
    printf 'present'
  else
    printf 'missing'
  fi
}

print_dependencies() {
  set -f
  old_ifs=$IFS
  IFS=,
  for entry in $1; do
    IFS=$old_ifs
    name=$(trim "$entry")

    case $name in
      '') ;;
      git | railway | gh | node) printf 'dependency %s: %s\n' "$name" "$(dependency_status "$name")" ;;
      *) printf 'dependency unknown: ignored\n' ;;
    esac
  done
  IFS=$old_ifs
  set +f
}

run_migration() {
  migration_status=0

  if [ -n "${scripts_dir:-}" ]; then
    sh "$scripts_dir/migrate-state.sh" 2>/dev/null || migration_status=$?
  fi
}

announce_project() {
  project_status=0
  project_directory=
  project_slug=
  project_file=$user_file

  if [ -n "${scripts_dir:-}" ]; then
    project_directory=$(sh "$scripts_dir/project-directory.sh" 2>/dev/null) || project_status=$?
  else
    project_status=1
  fi

  if [ "$project_status" != 0 ]; then
    printf 'active project: none\n'

    if [ "$project_status" = "$several_apps_status" ]; then
      project_file=
      printf 'note: several apps are saved here, this version of cockpit works on one app at a time\n'
    fi
    return 0
  fi

  project_file=$project_directory/state.md

  if [ "$project_directory" = "$state_home" ]; then
    project_slug=legacy
  else
    project_slug=$(known_slug "${project_directory##*/}")
  fi

  printf 'active project: %s\n' "$project_slug"
  printf 'project directory: %s\n' "$project_directory"

  if [ -e "$project_directory/.relink" ]; then
    printf 'railway links: to refresh\n'
  fi
}

print_health() {
  health_project=$project_slug

  if [ "$project_slug" = legacy ]; then
    health_project=
  fi

  sh "$scripts_dir/health-check.sh" --project "$health_project" 2>/dev/null || :
}

print_context() {
  printf 'cockpit session context\n'

  current_version=unknown

  if scripts_dir=$(scripts_directory); then
    current_version=$(known_version "$(plugin_version "$scripts_dir")")
    printf 'plugin version: %s\n' "$current_version"
    printf 'scripts directory: %s\n' "$scripts_dir"
  else
    printf 'plugin version: unknown\n'
    printf 'note: the scripts directory of the plugin could not be located\n'
  fi

  printf 'state directory: %s\n' "$state_home"

  run_migration

  if [ "$migration_status" = "$newer_schema_status" ]; then
    return 0
  fi

  user_file=$state_home/state.md

  if [ -f "$state_home/cockpit.md" ]; then
    user_file=$state_home/cockpit.md
  fi

  announce_project

  if [ ! -e "$user_file" ]; then
    printf 'onboarding: absent (no state file yet, onboarding has to run first)\n'
    return 0
  fi

  if [ ! -r "$user_file" ] || [ ! -f "$user_file" ]; then
    printf 'note: the state file cannot be read, onboarding status is unknown\n'
    return 0
  fi

  printf 'state schema version: %s\n' "$(known_schema_version "$(state_value schema_version "$user_file")")"
  printf 'language: %s\n' "$(known_language "$(state_value language "$user_file")")"

  if [ -z "$project_file" ]; then
    print_dependencies "$(state_value dependencies "$user_file")"
    return 0
  fi

  onboarding=$(state_value onboarding "$project_file")
  onboarding_step=$(state_value onboarding_step "$project_file")

  if [ "$project_file" != "$user_file" ] && [ ! -e "$project_file" ]; then
    onboarding=in-progress
    onboarding_step=profile
  fi

  case $onboarding in
    complete)
      printf 'onboarding: complete\n'
      ;;
    in-progress)
      printf 'onboarding: in progress, step reached: %s\n' "$(known_step "$onboarding_step")"
      ;;
    *)
      printf 'onboarding: unknown\n'
      printf 'note: the state file has no readable onboarding status, rerun onboarding to repair it\n'
      ;;
  esac

  print_dependencies "$(state_value dependencies "$user_file")"

  if [ "$onboarding" = complete ] && [ -n "${scripts_dir:-}" ]; then
    print_health
  fi

  recorded_version=$(known_version "$(state_value plugin_version "$user_file")")

  if [ "$onboarding" != complete ] || [ "$current_version" = unknown ]; then
    return 0
  fi

  if [ "$recorded_version" = unknown ]; then
    printf 'plugin version: not recorded in the state file yet\n'
  elif [ "$recorded_version" != "$current_version" ]; then
    printf 'plugin version changed: from %s to %s since the last session, changelog: %s/CHANGELOG.md\n' "$recorded_version" "$current_version" "$(dirname -- "$scripts_dir")"
  fi
}

(print_context) || printf 'note: cockpit could not finish its session check, the state may need a repair\n'
printf 'Load the cockpit skill before answering the first request of this session.\n'

exit 0
```

- [ ] **Step 4: Run everything**

Run: `sh tests/scripts/run.sh`
Expected: `Ran 98 tests in ...s` then `OK`. The 61 original tests, untouched except for the two set-ups of Task 2, still pass: they are the proof that a v1 session reads as before.

Run: `shellcheck scripts/*.sh tests/scripts/*.sh tests/fixtures/*/fixture.sh evals/*/fixture.sh`
Expected: no output.

- [ ] **Step 5: Real run on the fixture**

Run: `T=$(mktemp -d) && HOME=$T COCKPIT_HOME= sh tests/fixtures/state-v1/fixture.sh && env -u COCKPIT_HOME HOME=$T sh scripts/session-check.sh && echo ---- && env -u COCKPIT_HOME HOME=$T sh scripts/session-check.sh | sed -n 3,8p`
Expected for the first session, in this order: `state directory: <T>/.cockpit`, `state: updated to version 2`, `active project: acme-studio`, `project directory: <T>/.cockpit/projects/acme-studio`, `railway links: to refresh`, `state schema version: 2`, `language: fr`, `onboarding: complete`, the `dependency` lines, a `health:` line when the Railway CLI is not signed in here, a `plugin version changed:` line, and the last line asking for the skill. For the second session the same, without the `state: updated to version 2` line, and `railway links: to refresh` still there until `relink.sh` runs.

Run: `command ls -A "$T/.cockpit" "$T/.cockpit/projects/acme-studio" "$T/.cockpit/backups"`
Expected: the root holds `backups cockpit.md memory projects proposals.md` and nothing else (no `state.md`, no `.migrating`); the app folder holds `.relink handoff.md journal.md memory repo report.txt saas-project secrets state.md tools-project`; `backups` holds one `v1-<date>-<time>` folder.

- [ ] **Step 6: Commit**

```bash
git add scripts/session-check.sh tests/scripts/test_session_check.py
git commit -F - -- scripts/session-check.sh tests/scripts/test_session_check.py <<'EOF'
feat(state): move the saved setup to version 2 by itself, with a backup

The session check now runs the migration before it reads anything. A
setup saved by an earlier version gets one folder for its app, its
memory files are carried over untouched, and a backup of the old files
is kept. Nothing to type: a failure leaves the old layout working and
is reported, and a setup from a newer cockpit is never touched.
EOF
```

---

### Task 8: Facts, repo guidance and the proof that nothing regressed

**Files:**
- Modify: `docs/verified-facts.md`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: everything above.
- Produces: the recorded facts, the updated repo guidance, and the evidence for "done".

- [ ] **Step 1: Record the hook facts**

In `docs/verified-facts.md`, replace:

```text
- Two directories linked to two different Railway projects coexist in that file (CLI 4.68.0).
```

with:

```text
- Two directories linked to two different Railway projects coexist in that file (CLI 4.68.0).
- A SessionStart hook receives `session_id`, `transcript_path`, `cwd`, `hook_event_name` and `source` as JSON on stdin (`source: startup` in the CLI), and `CLAUDE_ENV_FILE` is set.
```

In `docs/verified-facts.md`, replace:

```text
- The environment of a tools project created by `railway init` is `production`: `relink.sh` links `tools-project/` with `-e production`.
```

with:

```text
- The environment of a tools project created by `railway init` is `production`: `relink.sh` links `tools-project/` with `-e production`.
- A SessionStart hook run again with the same `session_id` after a compaction and after a resume.
```

- [ ] **Step 2: Update `CLAUDE.md`**

In `CLAUDE.md`, replace:

```text
- `~/.cockpit/` belongs to the client. A change to its layout or to the `state.md` format bumps `schema_version` in `skills/cockpit/references/state-schema.md`, ships its migration in the same commit, and is tested against a state written by the previous version.
```

with:

```text
- `~/.cockpit/` belongs to the client. A change to its layout or to the `state.md` format bumps `schema_version` in `skills/cockpit/references/state-schema.md`, ships its migration in `scripts/migrate_state.py` in the same commit, and is tested against a state written by the previous version (`tests/fixtures/state-v1/` for version 1). The session check runs the migration before it reads anything: it backs up before it moves, and a failure leaves the old layout working (legacy mode).
```

In `CLAUDE.md`, replace:

```text
shellcheck scripts/*.sh tests/scripts/*.sh evals/*/fixture.sh
```

with:

```text
shellcheck scripts/*.sh tests/scripts/*.sh tests/fixtures/*/fixture.sh evals/*/fixture.sh
```

In `CLAUDE.md`, replace:

```text
1. `hooks/hooks.json` runs `scripts/session-check.sh` at every session start. Its output is the "session context": plugin version, scripts directory, state directory, onboarding status, missing dependencies, `health:` lines, and a `plugin version changed` line after an update.
```

with:

```text
1. `hooks/hooks.json` runs `scripts/session-check.sh` at every session start. It first migrates an older saved setup (`scripts/migrate-state.sh`), then prints the "session context": plugin version, scripts directory, state directory, active project and its directory, onboarding status, missing dependencies, `health:` lines, and a `plugin version changed` line after an update.
```

In `CLAUDE.md`, replace:

```text
- Each script is a `sh` wrapper, with the logic in a sibling `.py` file when it needs parsing.
```

with:

```text
- Each script is a `sh` wrapper, with the logic in a sibling `.py` file when it needs parsing.
- A script that works on one app takes `--project <slug>` and finds the app folder through `scripts/project-directory.sh`.
```

In `CLAUDE.md`, replace:

```text
Reference files write `$SCRIPTS` as a placeholder for the absolute path given by the session context.
```

with:

```text
Reference files write `$SCRIPTS` as a placeholder for the absolute path given by the session context, and `$PROJECT` for the `project directory:` line (everything that belongs to the active app).
```

- [ ] **Step 3: Check the English rules**

Run: `LC_ALL=C.UTF-8 grep -rnP '\x{2014}|\x{2013}' scripts tests skills docs/verified-facts.md CLAUDE.md docs/superpowers/plans/2026-10-09-state-v2-foundation.md`
Expected: no output.

Run: `grep -n '^ *#[^!]' scripts/*.sh scripts/*.py tests/scripts/*.py | grep -v 'shellcheck'`
Expected: no output (no comment in any script or test).

- [ ] **Step 4: Full checks, with the output**

Run: `sh tests/scripts/run.sh`
Expected: `Ran 98 tests in ...s` then `OK`.

Run: `shellcheck scripts/*.sh tests/scripts/*.sh tests/fixtures/*/fixture.sh evals/*/fixture.sh`
Expected: no output.

Run: `claude plugin validate .`
Expected: validation passes. If a warning shows, run the same command on `develop` and check that it is not new.

Run the suite once more on Python 3.9 if it is available (`python3.9 -m unittest discover -s tests/scripts -p 'test_*.py'`): CI does it anyway.

- [ ] **Step 5: Behaviour evals**

The 11 evals are the guard of the migration: ten of them build a v1 state and now pass through it on every run, none is edited.

Run: `claude plugin eval . --scaffold --runs 1`
Results land in `evals/results/` (ignored by git). Expected: 11 cases, all passing. What to look at, in the report or the traces, when one fails:

- `onboarding-starts-without-state`: with no state the model must start the onboarding and create `cockpit.md` and `projects/app/state.md` (no root `state.md`).
- `update-is-announced`: the model must read the changelog and write `plugin_version` into `cockpit.md`, and tell what is new in one or two sentences, without dwelling on the migration line.
- `undo-finds-the-way-back`: the model must find the journal under `projects/acme/journal.md` through the `project directory:` line and name the pull request to revert.
- `memory-keeps-what-the-user-says`: a short acknowledgement, a write under `projects/acme/memory/domain.md`, and at most one sentence about the update of the saved setup.
- `hand-off-becomes-an-issue`, `standard-setup-fits-the-app`, `empty-tool-gets-an-offer`: paths used in the traces must start with the project directory, never `~/.cockpit/saas-project` or `~/.cockpit/repo`.
- `rollback-request-is-carried-out`, `risky-diff-is-flagged`, `schema-change-names-the-risk`, `instruction-in-tool-output-is-data`: the answers must not change; each now starts with the one-sentence notice of the update, which must not crowd out the answer.

A failure is fixed in the skill prose (Task 3 or 6 files), never in an eval or a fixture, then the eval is run again.

- [ ] **Step 6: Whole-branch review**

Write the diff to a file: `git diff develop...HEAD > /tmp/state-v2.diff`. Then run reviewers in parallel, each with its own angle, each reading whole files and verifying every suspicion before reporting it: a bug reviewer on Opus (migration ordering, rollback, lock, rerun, byte-for-byte), a regressions reviewer on Sonnet (a v1 session, the 61 original tests, the 11 evals), a conventions reviewer on Sonnet (this repo's `CLAUDE.md` compared field by field with `scripts/health-check.sh` and `scripts/database-access.sh` for style, the global code rules for comments and blank lines). A confirmed defect gets a test and a fix commit, then Steps 4 and 5 run again.

- [ ] **Step 7: Commit**

```bash
git add docs/verified-facts.md CLAUDE.md
git commit -F - -- docs/verified-facts.md CLAUDE.md <<'EOF'
docs: record the state v2 facts and update CLAUDE.md

The hook input and the Railway folder links are recorded as checked
facts, the compaction behaviour as not verified. CLAUDE.md now says
where the migration lives, how it is tested and what $PROJECT means.
EOF
```

- [ ] **Step 8: Hand over**

Report to the owner: the 98 passing tests with the real output, the eval results, what was not verified (macOS run, Python 3.9 locally if absent, `shellcheck` if it could not be installed), and that the branch is ready for a pull request toward `develop`.

---

## Self-review

**Spec coverage.** Section 2 contract: v1 session unchanged (Task 2 tests, original 61 tests, evals), no lost file (backup test, byte comparisons), failure keeps v1 (Task 4 failure tests, legacy session test in Task 7), newer untouched (Task 4 and 7 tests), `feat` not `feat!` (Task 7 commit). Section 3 layout: Task 4 (tree test), Task 6 (schema). Section 4: `$PROJECT` and `--project` (Tasks 1 to 3); the session record, `project.sh`, `/cockpit:switch` and the question "which app" are out of scope. Section 5 steps 1 to 6 and every rule: Task 4 (detect, lock, backup, build, renames, commit point, cleanup, rollback, rerun, legacy) and Task 7 (hook lines), `relink.sh` Task 5; the prose lines for Claude (tell the user once, proposals.md, journal line, run relink) in Task 6. Section 6: import of the memory files only (Task 4); `memory.sh` and the new topics are for the next plan. Section 9: every test listed for migration, session context (no state, v1 migrated, one app, legacy, several apps), `--project` resolution, relink. Not covered here because they belong to later plans: `project.sh use`, a session record, `memory.sh`. Facts of section 9: Tasks 5 and 8. Section 10 steps 1 and 2: Tasks 1 to 3 and 4 to 7.

**Placeholder scan.** No unfinished marker, no "same as above": every code step carries its code, and each edit to an existing file gives the exact old and new text. The one value that a human measures is the Railway version in the fact recorded at the end of Task 5 Step 1, which the step says to copy from `--version`.

**Type consistency.** `project-directory.sh` statuses (0, 1, 4, 64) are used the same way in `session-check.sh` (4) and the tests. The migration stages `backed-up`, `built`, `renamed`, `committed` are the same in `migrate_state.py` and the tests, and the three test seams (`COCKPIT_MIGRATION_FAIL_AT`, `COCKPIT_MIGRATION_KILL_AT`, `COCKPIT_MIGRATION_LOCK_WAIT`) are the same in the module, the wrapper's unset list and the tests. `build_state_v1(home=None)` and `snapshot(directory=None)` have the same signature where they are defined (Task 4) and used (Tasks 4 and 7). The `.relink` marker name is the same in the migration, the session check, `relink.sh` and the schema. Context line texts match the Global Constraints character for character.

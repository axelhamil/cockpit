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

import json
import os
import zipfile

from support import ScriptTestCase

FAKE_UNAME = """
case "$1" in
  -s) printf '%s\\n' "${FAKE_SYSTEM:-Darwin}" ;;
  -m) printf '%s\\n' "${FAKE_MACHINE:-arm64}" ;;
esac
"""

FAKE_CURL = """
printf '%s\\n' "$*" >>"$FAKE_CURL_LOG"
if [ -n "${FAKE_CURL_FAILS:-}" ]; then
  echo "curl: (22) The requested URL returned error: 403" >&2
  exit 22
fi
case "$*" in
  *api.github.com*) cat "$FAKE_RELEASE" ;;
  *)
    while [ $# -gt 1 ]; do
      if [ "$1" = -o ]; then
        cp "$FAKE_ZIP" "$2"
      fi
      shift
    done
    ;;
esac
"""


class InstallGhTest(ScriptTestCase):
    def setUp(self):
        super().setUp()
        self.install_command("uname", FAKE_UNAME)
        self.install_command("curl", FAKE_CURL)
        self.env["PATH"] = self.path("bin") + os.pathsep + self.env["PATH"]
        self.env["HOME"] = self.path("ho me")
        os.makedirs(self.env["HOME"])
        self.env["COCKPIT_BIN_DIR"] = self.path("ho me", "tools bin")
        self.env["COCKPIT_SHELL_PROFILE"] = self.path("ho me", ".zshrc")
        self.env["FAKE_CURL_LOG"] = self.path("curl.log")
        self.env["FAKE_RELEASE"] = self.write(
            "release.json",
            json.dumps(
                {
                    "assets": [
                        {"name": "gh_9.9.9_linux_arm64.tar.gz", "browser_download_url": "https://example.com/linux.tar.gz"},
                        {"name": "gh_9.9.9_macOS_amd64.zip", "browser_download_url": "https://example.com/gh_amd64.zip"},
                        {"name": "gh_9.9.9_macOS_arm64.zip", "browser_download_url": "https://example.com/gh_arm64.zip"},
                    ]
                }
            ),
        )
        self.env["FAKE_ZIP"] = self.make_zip("gh_9.9.9_macOS_arm64/bin/gh")

    def make_zip(self, member):
        target = self.path("release.zip")
        with zipfile.ZipFile(target, "w") as archive:
            archive.writestr(member, "#!/bin/sh\necho 'gh version 9.9.9 (fake)'\n")
        return target

    def install(self):
        return self.run_script("install-gh.sh")

    def home_content(self):
        return sorted(os.listdir(self.env["HOME"]))

    def test_given_a_mac_then_the_binary_is_installed_and_the_path_line_is_written_once(self):
        first = self.install()
        second = self.install()

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("gh version 9.9.9", first.stdout)
        self.assertTrue(os.access(self.path("ho me", "tools bin", "gh"), os.X_OK))
        self.assertEqual(self.read(os.path.join("ho me", ".zshrc")).count("tools bin"), 1)
        self.assertIn("https://example.com/gh_arm64.zip", self.read("curl.log"))
        self.assertEqual(self.home_content(), [".zshrc", "tools bin"])

    def test_given_an_intel_mac_then_the_intel_archive_is_downloaded(self):
        self.env["FAKE_MACHINE"] = "x86_64"

        result = self.install()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("https://example.com/gh_amd64.zip", self.read("curl.log"))

    def test_given_another_system_than_macos_then_nothing_is_downloaded_or_written(self):
        self.env["FAKE_SYSTEM"] = "Linux"

        result = self.install()

        self.assertEqual(result.returncode, 1)
        self.assertIn("macOS", result.stderr)
        self.assertFalse(self.exists("curl.log"))
        self.assertEqual(self.home_content(), [])

    def test_given_github_answers_with_an_error_then_the_message_is_readable_and_nothing_is_written(self):
        self.env["FAKE_CURL_FAILS"] = "1"

        result = self.install()

        self.assertEqual(result.returncode, 1)
        self.assertIn("GitHub", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.home_content(), [])

    def test_given_an_unexpected_answer_or_archive_then_the_message_is_readable_and_nothing_is_written(self):
        cases = (
            ("release", '{"message": "API rate limit exceeded"}'),
            ("release", "<html>busy</html>"),
            ("release", '{"assets": [{"name": "gh_9.9.9_macOS_arm64.zip", "browser_download_url": "http://insecure.example.com/gh.zip"}]}'),
            ("zip", "other/bin/gh"),
            ("zip", "gh_9.9.9_macOS_arm64/gh"),
            ("zip", None),
        )

        for kind, content in cases:
            with self.subTest(kind=kind, content=content):
                env = {}
                if kind == "release":
                    env["FAKE_RELEASE"] = self.write("bad-release.json", content)
                elif content is None:
                    env["FAKE_ZIP"] = self.write("not-a-zip.zip", "plain text")
                else:
                    env["FAKE_ZIP"] = self.make_zip(content)

                result = self.run_script("install-gh.sh", env=env)

                self.assertEqual(result.returncode, 1)
                self.assertTrue(result.stderr.strip())
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(self.home_content(), [])

    def test_given_folder_overrides_without_the_test_switch_then_the_real_locations_are_used(self):
        del self.env["COCKPIT_TEST"]

        result = self.install()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.home_content(), [".local", ".zshrc"])
        self.assertTrue(os.access(self.path("ho me", ".local", "bin", "gh"), os.X_OK))

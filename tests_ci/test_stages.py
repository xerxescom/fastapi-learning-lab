import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from stages import README_HEADINGS, build_matrix, discover_stages, run_tests


class StageChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def stage(self, name):
        directory = self.root / name
        directory.mkdir()
        for filename in ("main.py", "test_main.py", "requirements.txt"):
            (directory / filename).write_text("# test fixture\n", encoding="utf-8")
        (directory / "README.md").write_text("\n".join(f"## {heading}" for heading in README_HEADINGS), encoding="utf-8")
        return directory

    def test_discovery_and_matrix(self):
        self.stage("stage02_second")
        self.stage("stage01_first")
        stages = discover_stages(self.root)
        self.assertEqual([path.name for path in stages], ["stage01_first", "stage02_second"])
        self.assertEqual(build_matrix(stages)["include"], [
            {"stage": "stage01_first", "os": "ubuntu-latest"},
            {"stage": "stage02_second", "os": "ubuntu-latest"},
        ])

    def test_windows_capstone_matrix(self):
        matrix = build_matrix([Path("stage25_mini_api")])["include"]
        self.assertEqual(len(matrix), 2)
        self.assertEqual(matrix[1]["os"], "windows-latest")

    def test_empty_repository_fails(self):
        with self.assertRaises(ValueError):
            discover_stages(self.root)

    def test_gap_fails(self):
        self.stage("stage01_first")
        self.stage("stage03_third")
        with self.assertRaises(ValueError):
            discover_stages(self.root)

    def test_duplicate_number_fails(self):
        self.stage("stage01_first")
        self.stage("stage01_duplicate")
        with self.assertRaises(ValueError):
            discover_stages(self.root)

    def test_invalid_name_fails(self):
        self.stage("stage01_bad-name")
        with self.assertRaises(ValueError):
            discover_stages(self.root)

    def test_missing_required_file_fails(self):
        directory = self.stage("stage01_first")
        (directory / "requirements.txt").unlink()
        with self.assertRaises(ValueError):
            discover_stages(self.root)

    def test_empty_required_file_fails(self):
        directory = self.stage("stage01_first")
        (directory / "main.py").write_text("", encoding="utf-8")
        with self.assertRaises(ValueError):
            discover_stages(self.root)

    def test_readme_headings_required(self):
        directory = self.stage("stage01_first")
        (directory / "README.md").write_text("# Missing headings", encoding="utf-8")
        with self.assertRaises(ValueError):
            discover_stages(self.root)

    @patch("stages.subprocess.run")
    def test_runner_isolates_processes_and_continues_on_failure(self, run):
        stages = [self.stage("stage01_first"), self.stage("stage02_second")]
        run.side_effect = [subprocess.CompletedProcess([], 1), subprocess.CompletedProcess([], 0)]
        with patch.dict(os.environ, {"LAB_DATABASE_URL": "must-not-be-inherited"}):
            self.assertEqual(run_tests(stages, self.root / "reports"), 1)
        self.assertEqual(run.call_count, 2)
        for index, call in enumerate(run.call_args_list):
            self.assertEqual(call.kwargs["cwd"], stages[index])
            self.assertNotIn("LAB_DATABASE_URL", call.kwargs["env"])
            self.assertEqual(call.args[0][:3], [sys.executable, "-m", "pytest"])
            self.assertIn(f"--junitxml={self.root / 'reports' / (stages[index].name + '.xml')}", call.args[0])

    @patch("stages.subprocess.run", return_value=subprocess.CompletedProcess([], 0))
    def test_success_returns_zero(self, run):
        self.assertEqual(run_tests([self.stage("stage01_first")], self.root / "reports"), 0)

    @patch("stages.subprocess.run", side_effect=subprocess.TimeoutExpired("pytest", 300))
    def test_timeout_is_failure(self, run):
        self.assertEqual(run_tests([self.stage("stage01_first")], self.root / "reports"), 1)


if __name__ == "__main__":
    unittest.main()

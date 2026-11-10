"""The suites CLI seam: real processes with disposable, synthetic suites."""

from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class SuiteRunner(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="suite-runner-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "tests" / "suites").mkdir(parents=True)
        stub = self.root / "generator" / "govern-repository" / "scripts" / "govlib"
        stub.mkdir(parents=True)
        (stub / "__init__.py").write_text("")
        (stub / "storedform.py").write_text("")

    def prepare(self, bodies):
        source = (ROOT / "tests" / "run.py").read_text()
        registry = tuple((name, "test_" + name.replace("-", "_"), job)
                         for name, job, _ in bodies)
        source = re.sub(r"SUITES = \(.*?\n\)", "SUITES = " + repr(registry), source,
                        count=1, flags=re.S)
        (self.root / "tests" / "run.py").write_text(source)
        for (_, module, _), (_, _, body) in zip(registry, bodies):
            (self.root / "tests" / "suites" / (module + ".py")).write_text(body)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(self.root / "tests" / "run.py"),
                               "suites"] + list(args), cwd=str(self.root),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, timeout=30)

    def test_success_reports_whole_output_counts_and_same_interpreter(self):
        self.prepare([(name, "linux", "import unittest, sys\n"
                       "class Example(unittest.TestCase):\n"
                       "    def test_example(self):\n"
                       "        print('BEGIN-%s')\n"
                       "        print(sys.executable)\n"
                       "        print('END-%s')\n" % (name, name))
                      for name in ("alpha", "beta")])
        result = self.run_cli("--all", "--workers", "2")
        self.assertEqual(result.returncode, 0, result.stdout)
        for name in ("alpha", "beta"):
            self.assertIn("BEGIN-%s\n%s\nEND-%s" % (name, sys.executable, name), result.stdout)
            self.assertRegex(result.stdout, r"PASS %s: 1 tests, [0-9.]+s" % name)
        self.assertRegex(result.stdout, r"PASS total: 2 tests, [0-9.]+s wall")

    def test_crash_fails_command_and_preserves_output_and_passing_sibling(self):
        self.prepare([
            ("broken", "linux", "import os\nprint('before crash', flush=True)\nos._exit(7)\n"),
            ("sibling", "linux", "import unittest\nclass Good(unittest.TestCase):\n"
             "    def test_good(self): pass\n"),
        ])
        result = self.run_cli("--all", "--workers", "1")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("before crash", result.stdout)
        self.assertRegex(result.stdout, r"FAIL broken: unknown tests, [0-9.]+s")
        self.assertIn("PASS sibling: 1 tests", result.stdout)
        self.assertRegex(result.stdout, r"FAIL total: 1 tests \(incomplete\), [0-9.]+s wall")

    def test_failure_error_and_load_failure_do_not_hide_passing_sibling(self):
        for body, diagnostic in (
            ("import unittest\nclass Bad(unittest.TestCase):\n"
             "    def test_bad(self): self.fail('planted failure')\n", "planted failure"),
            ("import unittest\nclass Bad(unittest.TestCase):\n"
             "    def test_bad(self): raise RuntimeError('planted error')\n", "planted error"),
            ("raise ImportError('planted load failure')\n", "planted load failure"),
        ):
            with self.subTest(diagnostic=diagnostic):
                self.prepare([("broken", "linux", body), ("sibling", "linux",
                              "import unittest\nclass Good(unittest.TestCase):\n"
                              "    def test_good(self): pass\n")])
                result = self.run_cli("--all")
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn(diagnostic, result.stdout)
                self.assertIn("FAIL broken: 1 tests", result.stdout)
                self.assertIn("PASS sibling: 1 tests", result.stdout)
                self.assertIn("FAIL total: 2 tests", result.stdout)

    def test_concurrent_suites_rendezvous_and_output_blocks_never_interleave(self):
        self.prepare([(name, "linux", "import pathlib, time, unittest\n"
                       "class Rendezvous(unittest.TestCase):\n"
                       "    def test_overlap(self):\n"
                       "        print('BEGIN-%s', flush=True)\n"
                       "        pathlib.Path('%s.ready').touch()\n"
                       "        deadline = time.monotonic() + 10\n"
                       "        while not pathlib.Path('%s.ready').exists():\n"
                       "            self.assertLess(time.monotonic(), deadline, 'no overlap')\n"
                       "            time.sleep(0.01)\n"
                       "        print('END-%s', flush=True)\n" % (name, name, other, name))
                      for name, other in (("alpha", "beta"), ("beta", "alpha"))])
        result = self.run_cli("--all", "--workers", "2")
        self.assertEqual(result.returncode, 0, result.stdout)
        markers = re.findall(r"(?:BEGIN|END)-(?:alpha|beta)", result.stdout)
        self.assertIn(markers, [
            ["BEGIN-alpha", "END-alpha", "BEGIN-beta", "END-beta"],
            ["BEGIN-beta", "END-beta", "BEGIN-alpha", "END-alpha"],
        ])

    def test_one_worker_is_serial_and_longest_suites_start_first(self):
        self.prepare([(name, "linux", "import pathlib, time, unittest\n"
                       "class Serial(unittest.TestCase):\n"
                       "    def test_order(self):\n"
                       "        with pathlib.Path('events').open('a') as f: f.write('start-%s\\n')\n"
                       "        time.sleep(0.03)\n"
                       "        with pathlib.Path('events').open('a') as f: f.write('end-%s\\n')\n"
                       % (name, name)) for name in ("short", "owner", "machine-wizard")])
        result = self.run_cli("--all", "--workers", "1")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual((self.root / "events").read_text().splitlines(), [
            "start-machine-wizard", "end-machine-wizard", "start-owner", "end-owner",
            "start-short", "end-short",
        ])

    def test_selection_default_worker_count_and_invalid_arguments(self):
        import os

        self.prepare([(name, job, "import unittest\nclass Good(unittest.TestCase):\n"
                       "    def test_good(self): pass\n")
                      for name, job in (("alpha", "linux"), ("beta", "macos"))])
        for args, expected in ((["--job", "linux"], ["alpha"]),
                               (["--job", "macos"], ["beta"]),
                               (["alpha", "beta"], ["alpha", "beta"]),
                               (["--all"], ["alpha", "beta"])):
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertIn("workers: %d" % (os.cpu_count() or 1), result.stdout)
                self.assertEqual(re.findall(r"^PASS (\w+):", result.stdout, re.M), expected + ["total"])
        for args in ([], ["missing"], ["--all", "--workers", "0"],
                     ["--all", "--workers", "-1"], ["--all", "--workers", "many"]):
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertNotIn("===", result.stdout)

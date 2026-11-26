"""The suites CLI seam: real processes with disposable, synthetic suites."""

import json
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

    def prepare(self, bodies, durations=None, chunks=None):
        source = (ROOT / "tests" / "run.py").read_text()
        registry = tuple((name, "test_" + name.replace("-", "_"), job)
                         for name, job, _ in bodies)
        source = re.sub(r"SUITES = \(.*?\n\)", "SUITES = " + repr(registry), source,
                        count=1, flags=re.S)
        source = re.sub(r"CHUNKS = \{.*?\n\}", "CHUNKS = " + repr(chunks or {}), source,
                        count=1, flags=re.S)
        (self.root / "tests" / "run.py").write_text(source)
        if durations is not None:
            (self.root / "tests" / "unit_durations.json").write_text(json.dumps(durations))
        for (_, module, _), (_, _, body) in zip(registry, bodies):
            (self.root / "tests" / "suites" / (module + ".py")).write_text(body)

    def run_cli(self, *args, command="suites"):
        return subprocess.run([sys.executable, str(self.root / "tests" / "run.py"),
                               command] + list(args), cwd=str(self.root),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, timeout=30)

    def events(self):
        return (self.root / "events").read_text().splitlines()

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

    def test_one_worker_is_serial_and_longest_measured_units_start_first(self):
        logging = ("    def test_order(self):\n"
                   "        with pathlib.Path('events').open('a') as f: f.write('start-%s\\n')\n"
                   "        time.sleep(0.03)\n"
                   "        with pathlib.Path('events').open('a') as f: f.write('end-%s\\n')\n")
        self.prepare([("short", "linux", "import pathlib, time, unittest\n"
                       "class Quick(unittest.TestCase):\n" + logging % ("quick", "quick") +
                       "class Slow(unittest.TestCase):\n" + logging % ("slow", "slow")),
                      ("other", "linux", "import pathlib, time, unittest\n"
                       "class Middle(unittest.TestCase):\n" + logging % ("middle", "middle"))],
                     durations={"test_short.Quick": 1.0, "test_short.Slow": 30.0, "test_other.Middle": 5.0})
        result = self.run_cli("--all", "--workers", "1")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.events(), ["start-slow", "end-slow", "start-middle", "end-middle",
                                         "start-quick", "end-quick"])
        # Per-unit lines follow scheduling order; per-suite lines keep registry order.
        self.assertEqual(re.findall(r"^unit PASS (\S+): 1 tests", result.stdout, re.M),
                         ["test_short.Slow", "test_other.Middle", "test_short.Quick"])
        self.assertEqual(re.findall(r"^PASS (\w+): (\d+) tests", result.stdout, re.M),
                         [("short", "2"), ("other", "1"), ("total", "3")])

    def test_classes_of_one_suite_run_as_concurrent_units(self):
        self.prepare([("alpha", "linux", "import pathlib, time, unittest\n" + "".join(
            "class %s(unittest.TestCase):\n"
            "    def test_overlap(self):\n"
            "        pathlib.Path('%s.ready').touch()\n"
            "        deadline = time.monotonic() + 10\n"
            "        while not pathlib.Path('%s.ready').exists():\n"
            "            self.assertLess(time.monotonic(), deadline, 'no overlap')\n"
            "            time.sleep(0.01)\n" % (name, name, other)
            for name, other in (("First", "Second"), ("Second", "First"))))])
        result = self.run_cli("--all", "--workers", "2")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("=== test_alpha.First ===", result.stdout)
        self.assertIn("=== test_alpha.Second ===", result.stdout)
        self.assertIn("PASS alpha: 2 tests", result.stdout)

    def test_a_chunked_class_runs_every_method_once_across_its_chunks(self):
        self.prepare([("alpha", "linux", "import pathlib, unittest\n"
                       "class Big(unittest.TestCase):\n" + "".join(
                           "    def test_%s(self):\n"
                           "        with pathlib.Path('events').open('a') as f: f.write('%s\\n')\n" % (n, n)
                           for n in ("a", "b", "c", "d", "e")))],
                     chunks={"test_alpha.Big": 2})
        result = self.run_cli("--all", "--workers", "1")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(sorted(self.events()), ["a", "b", "c", "d", "e"])
        self.assertIn("unit PASS test_alpha.Big[1/2]: 3 tests", result.stdout)
        self.assertIn("unit PASS test_alpha.Big[2/2]: 2 tests", result.stdout)
        self.assertIn("PASS alpha: 5 tests", result.stdout)

    def shard_suites(self, durations):
        body = ("import pathlib, unittest\n" + "".join(
            "class %s(unittest.TestCase):\n"
            "    def test_run(self):\n"
            "        with pathlib.Path('events').open('a') as f: f.write('%s\\n')\n" % (name, name)
            for name in ("One", "Two", "Three")))
        self.prepare([("alpha", "linux", body), ("beta", "macos", body.replace("One", "Four")
                                                   .replace("Two", "Five").replace("Three", "Six"))],
                     durations=durations)

    MEASURED = {"test_alpha.One": 9.0, "test_alpha.Two": 7.0, "test_alpha.Three": 2.0,
                "test_beta.Four": 6.0, "test_beta.Five": 5.0, "test_beta.Six": 1.0}

    def test_shards_partition_the_units_by_measured_duration_and_their_reports_check(self):
        self.shard_suites(self.MEASURED)
        reports, ran = [], []
        for shard in ("1/2", "2/2"):
            (self.root / "events").write_text("")
            report = self.root / ("report-%s.json" % shard[0])
            result = self.run_cli("--all", "--workers", "1", "--shard", shard, "--report", str(report))
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("shard %s" % shard, result.stdout)
            reports.append(report.read_text())
            ran.append(self.events())
        # Longest first, each to the lighter shard: 9|7, 6 to the 7, 5 to the 9, 2 to the 13, 1 to the 14.
        self.assertEqual(ran, [["One", "Five", "Six"], ["Two", "Four", "Three"]])
        parsed = [json.loads(text) for text in reports]
        self.assertEqual(parsed[0]["units"], parsed[1]["units"])
        self.assertEqual(sorted(parsed[0]["ran"] + parsed[1]["ran"]), sorted(self.MEASURED))
        check = self.run_cli(*reports, command="shard-check")
        self.assertEqual(check.returncode, 0, check.stdout)
        self.assertIn("PASS shard-check: 6 units, each run by exactly one of 2 shards", check.stdout)
        # Without --shard the same selection runs all six on one machine.
        (self.root / "events").write_text("")
        whole = self.run_cli("--all", "--workers", "1")
        self.assertEqual(whole.returncode, 0, whole.stdout)
        self.assertEqual(sorted(self.events()), ["Five", "Four", "One", "Six", "Three", "Two"])

    def test_shard_check_fails_an_unassigned_or_doubly_assigned_unit(self):
        self.shard_suites(self.MEASURED)
        reports = []
        for shard in ("1/2", "2/2"):
            report = self.root / ("report-%s.json" % shard[0])
            result = self.run_cli("--all", "--shard", shard, "--report", str(report))
            self.assertEqual(result.returncode, 0, result.stdout)
            reports.append(json.loads(report.read_text()))
        first, second = reports
        planted = {
            "unassigned": ([dict(first, ran=first["ran"][1:]), second],
                           "FAIL shard-check: %s is run by no shard" % first["ran"][0]),
            "doubly assigned": ([dict(first, ran=first["ran"] + second["ran"][:1]), second],
                                "FAIL shard-check: %s is run by shards 1/2 and 2/2" % second["ran"][0]),
            "a shard missing": ([first], "FAIL shard-check: shard 2/2 reported nothing"),
            "plans differ": ([first, dict(second, units=second["units"][1:])],
                             "FAIL shard-check: shard 2/2 planned different units from shard 1/2"),
            "a failed shard": ([first, dict(second, passed=False)], "FAIL shard-check: shard 2/2 did not pass"),
        }
        for name, (planted_reports, line) in planted.items():
            with self.subTest(planted=name):
                check = self.run_cli(*[json.dumps(report) for report in planted_reports], command="shard-check")
                self.assertEqual(check.returncode, 1, check.stdout)
                self.assertIn(line, check.stdout)
                self.assertNotIn("PASS shard-check", check.stdout)

    def test_a_shard_refuses_an_unmeasured_or_stale_unit_before_running_anything(self):
        for name, durations, line in (
            ("unmeasured", {k: v for k, v in self.MEASURED.items() if k != "test_beta.Five"},
             "test_beta.Five has no measured duration"),
            ("stale", dict(self.MEASURED, **{"test_alpha.Renamed": 3.0}),
             "test_alpha.Renamed is measured but no longer a unit"),
            ("no table", None, "test_alpha.One has no measured duration"),
        ):
            with self.subTest(table=name):
                table = self.root / "tests" / "unit_durations.json"
                if table.exists():
                    table.unlink()
                self.shard_suites(durations)
                (self.root / "events").write_text("")
                result = self.run_cli("--all", "--shard", "1/2")
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn(line, result.stdout)
                self.assertNotIn("===", result.stdout)
                self.assertEqual(self.events(), [])
                # Without --shard an unmeasured unit still runs, estimated as long.
                self.assertEqual(self.run_cli("--all").returncode, 0)

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
                     ["--all", "--workers", "-1"], ["--all", "--workers", "many"],
                     ["--all", "--shard", "0/2"], ["--all", "--shard", "3/2"], ["--all", "--shard", "2"]):
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertNotIn("===", result.stdout)

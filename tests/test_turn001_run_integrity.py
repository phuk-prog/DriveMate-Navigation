"""TURN-001 fresh-retet evidence integrity, not a real-road execution."""
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from benchmarks import turn001_restrictions as turn


class Turn001ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.cohort = self.work / "cohort.json"
        self.cohort.write_text(json.dumps({
            "contract": "TURN-001 v1",
            "frozen_before_engine_runs": True,
            "source_sha256": "a" * 64,
            "cases": [],
        }))
        (self.work / "prepared.json").write_text("[]\n")
        self.patchers = [
            patch.object(turn, "WORK", self.work),
            patch.object(turn, "COHORT", self.cohort),
            patch.object(turn, "_revision", return_value="b" * 40),
        ]
        for p in self.patchers:
            p.start()
            self.addCleanup(p.stop)

    def provenance(self, engine="DMN"):
        return turn._provenance(engine)

    def test_new_run_has_pinned_provenance(self):
        result = turn._load_run("DMN", self.provenance())
        self.assertEqual(result["_provenance"]["revision"], "b" * 40)
        self.assertEqual(result["_provenance"]["source_sha256"], "a" * 64)
        self.assertEqual(result["_provenance"]["engine"], "DMN")

    def test_same_revision_and_inputs_may_resume_interrupted_run(self):
        prov = self.provenance()
        original = {"_provenance": prov, "123": {"verdict": "PASS", "clip_sha256": "c"}}
        (self.work / "run-DMN.json").write_text(json.dumps(original))
        self.assertEqual(turn._load_run("DMN", prov), original)

    def test_old_unprovenanced_results_are_not_reused(self):
        (self.work / "run-DMN.json").write_text('{"123":{"verdict":"PASS"}}')
        with self.assertRaisesRegex(RuntimeError, "missing or mismatched"):
            turn._load_run("DMN", self.provenance())

    def test_changed_revision_or_prepared_cohort_blocks_reuse(self):
        old = self.provenance()
        (self.work / "run-DMN.json").write_text(json.dumps({"_provenance": old}))
        with patch.object(turn, "_revision", return_value="c" * 40):
            with self.assertRaisesRegex(RuntimeError, "missing or mismatched"):
                turn._load_run("DMN", self.provenance())
        (self.work / "prepared.json").write_text('[{"relation":1}]\n')
        with self.assertRaisesRegex(RuntimeError, "missing or mismatched"):
            turn._load_run("DMN", self.provenance())
        (self.work / "prepared.json").write_text("[]\n")
        self.cohort.write_text(json.dumps({
            "frozen_before_engine_runs": True,
            "source_sha256": "d" * 64,
            "cases": [],
        }))
        with self.assertRaisesRegex(RuntimeError, "missing or mismatched"):
            turn._load_run("DMN", self.provenance())

    def test_fresh_rerun_archives_exact_old_bytes(self):
        original = b'{"123":{"verdict":"FAIL_PROHIBITED"}}\n'
        path = self.work / "run-DMN.json"
        path.write_bytes(original)
        result = turn._load_run("DMN", self.provenance(), fresh=True)
        self.assertEqual(set(result), {"_provenance"})
        archived = list(self.work.glob("run-DMN-prior-*.json"))
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0].read_bytes(), original)
        self.assertEqual(path.read_bytes(), original)  # caller writes new results
        self.assertEqual(turn._load_run("DMN", self.provenance(), fresh=True), result)
        self.assertEqual(archived[0].read_bytes(), original)

    def test_score_rejects_historical_competitor_data(self):
        (self.work / "run-OSRM.json").write_text('{"123":{"verdict":"PASS"}}')
        with self.assertRaisesRegex(RuntimeError, "stale/unprovenanced"):
            turn.score()

    def test_score_rejects_mismatched_clip_even_with_current_revision(self):
        prepared = [{
            "relation": 123, "geometry": {"status": "TESTABLE"},
            "clip_sha256": "expected",
        }]
        (self.work / "prepared.json").write_text(json.dumps(prepared))
        prov = self.provenance()
        (self.work / "run-DMN.json").write_text(json.dumps({
            "_provenance": prov,
            "123": {"verdict": "PASS", "clip_sha256": "wrong"},
        }))
        with self.assertRaisesRegex(RuntimeError, "mismatched case clip"):
            turn.score()

    def test_frozen_cohort_cannot_be_reselected_in_place(self):
        with self.assertRaisesRegex(RuntimeError, "frozen cohort exists"):
            turn.select(self.work / "not-needed.osm.pbf")

    def test_container_cleanup_does_not_require_sudo(self):
        scratch = self.work / "osrm"
        scratch.mkdir()

        def container_cleanup(*args, **kwargs):
            scratch.rmdir()
            return subprocess.CompletedProcess(args[0], 0, "", "")

        with patch.object(turn.shutil, "rmtree", side_effect=PermissionError), \
                patch.object(turn.subprocess, "run", side_effect=container_cleanup) as run:
            turn._remove_engine_work(scratch, "OSRM")
        command = run.call_args.args[0]
        self.assertNotIn("sudo", command)
        self.assertIn("--entrypoint", command)
        self.assertFalse(scratch.exists())


if __name__ == "__main__":
    unittest.main()

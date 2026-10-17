"""Shared work register (tools/work_status.py): claims, done fingerprints, refusals."""
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from tools import work_status as ws


class WorkRegister(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patches = [mock.patch.object(ws, "ITEMS", Path(self.tmp.name) / "items"),
                   mock.patch.object(ws, "_remote", return_value=[]),
                   mock.patch.object(ws, "_branch", return_value="branch-a"),
                   mock.patch.object(ws, "REGISTER", Path(self.tmp.name) / "REGISTER.md"),
                   mock.patch.object(ws, "INDEX", Path(self.tmp.name) / "index.json")]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)

    def run_cli(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = ws.main(list(argv))
        return code, out.getvalue()

    def test_finished_work_is_seen_and_not_restarted(self):
        self.run_cli("finish", "T-1", "--title", "t", "--fingerprint", "v1|abc")
        self.assertEqual(self.run_cli("seen", "v1|abc")[0], 1)
        self.assertEqual(self.run_cli("seen", "v2|abc")[0], 0)
        self.assertEqual(self.run_cli("start", "T-1")[0], 2)
        self.assertEqual(self.run_cli("start", "T-1", "--reason", "owner asked for a rerun")[0], 0)

    def test_work_held_on_another_branch_is_refused(self):
        held = {"id": "T-2", "state": "in_progress", "branch": "branch-b", "agent": "Codex", "updated": ws._now()}
        with mock.patch.object(ws, "_remote", return_value=[held]):
            code, text = self.run_cli("start", "T-2", "--agent", "Claude")
            self.assertEqual(code, 2)
            self.assertIn("Codex", text)
            self.assertIn("T-2", ws.show(ws.collect()))

    def test_stale_claim_can_be_taken(self):
        held = {"id": "T-3", "state": "in_progress", "branch": "branch-b", "agent": "Codex",
                "updated": "2020-01-01T00:00:00+00:00"}
        with mock.patch.object(ws, "_remote", return_value=[held]):
            self.assertIn("STALE", ws.show(ws.collect()))
            self.assertEqual(self.run_cli("start", "T-3", "--agent", "Claude")[0], 0)

    def test_where_lists_cheapest_pointer_first(self):
        if True:
            self.run_cli("source", "Big map", "--where", "branch data/x", "--cost", "large", "--topics", "map")
            self.run_cli("source", "Map notes", "--where", "docs/MAP.md", "--cost", "tiny", "--topics", "map")
            hits = ws.where(ws.load_index(), {}, "map")
            self.assertTrue(hits[0].startswith("[tiny]"))
            self.assertTrue(hits[1].startswith("[large]"))

    def test_register_page_lists_done_pending_and_rules(self):
        self.run_cli("finish", "T-4", "--title", "old test", "--results", "docs/T4.md")
        self.run_cli("plan", "T-5", "--title", "new test", "--why", "owner asked")
        page = ws.REGISTER.read_text()
        self.assertIn("Keep usage low", page)
        self.assertIn("**T-4** old test", page)
        self.assertIn("docs/T4.md", page)
        self.assertLess(page.index("## Start here"), page.index("**T-5**"))


if __name__ == "__main__":
    unittest.main()

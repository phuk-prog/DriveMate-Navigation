import tempfile
import unittest
from pathlib import Path
from tools.public_osm_extract import (
    DATA_AREA, parse_bbox, validate_paths, command_plan, reject_object_metadata,
    prepare,
)
from map_data import OSMImportError


class PublicMapPreparationTests(unittest.TestCase):
    def test_bbox_bounds_and_limits(self):
        self.assertEqual(parse_bbox("-3,53,-2.99,53.01"), "-3.000000,53.000000,-2.990000,53.010000")
        for bad in ("1,2,3", "3,2,1,4", "0,0,10,10", "nan,0,1,1", "x,1,2,3"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    parse_bbox(bad)

    def test_repo_data_remains_ignored_by_git(self):
        with tempfile.TemporaryDirectory() as folder:
            src = Path(folder) / "public-region.osm.pbf"
            src.write_bytes(b"simulated pbf content")
            output = DATA_AREA / "local-test-only.osm"
            validate_paths(src, output)
            plan = command_plan(src, "-3,53,-2.99,53.01", output, Path(folder))
            self.assertEqual(len(plan), 2)
            self.assertIn("complete_ways", plan[0])
            self.assertIn("osm,add_metadata=false", plan[1])
            self.assertNotIn("curl", " ".join(plan))

    def test_output_outside_ignored_directory_is_rejected(self):
        source = Path("open-data.osm.pbf")
        with self.assertRaises(ValueError):
            validate_paths(source, Path("benchmarks/fixtures/do-not-commit.osm"))
        with self.assertRaises(ValueError):
            validate_paths(Path("internal-history.osm.pbf"), DATA_AREA / "subset.osm")

    def test_contributor_metadata_is_forbidden_even_if_xml_is_valid(self):
        payload = b'<osm><node id="1" lat="0" lon="0" uid="22"/></osm>'
        with self.assertRaises(OSMImportError):
            reject_object_metadata(payload)
        reject_object_metadata(b'<osm><node id="1" lat="0" lon="0"/></osm>')

    def test_local_conversion_uses_stub_runner_never_network(self):
        # All data is hand-authored synthetic; no external downloads or personal locations.
        fixture = Path(__file__).resolve().parents[1] / "benchmarks/fixtures/synthetic-osm-junction.xml"
        with tempfile.TemporaryDirectory() as folder:
            src = Path(folder) / "synthetic-public.osm.pbf"
            src.write_bytes(b"synthetic placeholder")
            target = DATA_AREA / "local-preparation-test.osm"
            target.unlink(missing_ok=True)
            calls = []
            def fake_run(argv, **kw):
                calls.append(tuple(argv))
                if argv[1] == "cat":
                    target.write_bytes(fixture.read_bytes())
            try:
                stats = prepare(src, "-3,53,-2.99,53.01", target,
                                snapshot="synthetic-v1", region="fabricated-area", runner=fake_run)
                self.assertEqual(stats["status"], "prototype-import-complete")
                self.assertTrue(stats["does_not_prove_driving_legality"])
                self.assertEqual(stats["uploaded_map_files"], 0)
                self.assertEqual(len(calls), 2)
            finally:
                target.unlink(missing_ok=True)

    def test_failed_conversion_cleans_up_target(self):
        with tempfile.TemporaryDirectory() as folder:
            src = Path(folder) / "synthetic-public.osm.pbf"
            src.write_bytes(b"synthetic placeholder")
            target = DATA_AREA / "should-be-deleted.osm"
            target.unlink(missing_ok=True)
            def fake_run(argv, **kw):
                if argv[1] == "cat":
                    target.write_bytes(b'<osm><node id="1" uid="123"/></osm>')
            with self.assertRaises(OSMImportError):
                prepare(src, "-3,53,-2.99,53.01", target,
                        snapshot="synthetic-v1", region="fabricated-area", runner=fake_run)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()

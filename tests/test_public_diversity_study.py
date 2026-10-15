"""Controlled public-source routing study tests on ONLY synthetic tiny input."""
import tempfile
import unittest
from pathlib import Path

from benchmarks.public_diversity_study import study_public_road_diversity
from map_data.osm_xml import OSMImportError
from tools.public_osm_extract import DATA_AREA


class PublicRoadAreaStudyTests(unittest.TestCase):
    def test_two_independent_bounded_areas_and_ephemeral_cleanup(self):
        with tempfile.TemporaryDirectory() as place:
            source = Path(place) / "test-public.osm.pbf"
            source.write_bytes(b"source-fixture")
            with tempfile.TemporaryDirectory(dir=DATA_AREA) as target:
                data_dir = Path(target)
                prepared = []
                def preparer(src, bbox, output, **kw):
                    self.assertEqual(src, source)
                    self.assertTrue(output.is_relative_to(DATA_AREA))
                    output.write_bytes(b"<osm/>")
                    prepared.append(bbox)
                    return {"map_sha256": "synthetic-sha"}
                def checker(raw, **kw):
                    self.assertEqual(raw, b"<osm/>")
                    return {"route_preference_discriminating_coverage":
                            "MAP_DIVERGENCE_OBSERVED" if kw["region"] == "area-b"
                            else "INSUFFICIENT"}
                report = study_public_road_diversity(
                    source, snapshot="fabricated", result_dir=data_dir,
                    candidates=[("area-a","-3,53,-2.99,53.01"),
                                ("area-b","-3,53,-2.98,53.02")],
                    preparer=preparer, checker=checker, samples=1)
                self.assertEqual(report["areas_attempted"], 2)
                self.assertEqual(report["areas_with_fastest_shortest_path_diversity"], 1)
                self.assertEqual(report["comparison_coverage"], "MAP_DIVERGENCE_OBSERVED")
                self.assertEqual(len(prepared),2)
                self.assertEqual(list(data_dir.iterdir()), [])
                self.assertFalse(report["independently_verified_legal_movements"])

    def test_unsupported_does_not_invent_success(self):
        with tempfile.TemporaryDirectory() as place:
            src=Path(place)/"public.osm.pbf"
            src.write_bytes(b"fixture")
            with tempfile.TemporaryDirectory(dir=DATA_AREA) as target:
                def bad(*args, **kwargs):
                    raise OSMImportError("unsupported condition")
                report=study_public_road_diversity(src,snapshot="fake",
                         result_dir=Path(target),candidates=[("a","-3,53,-2.99,53.01")],
                         preparer=bad)
                self.assertEqual(report["areas_graph_tested"],0)
                self.assertEqual(report["areas_unsupported"],1)
                self.assertEqual(report["comparison_coverage"],"INSUFFICIENT")
                self.assertEqual(list(Path(target).iterdir()),[])

    def test_refuse_private_output_location_or_bad_pbf(self):
        with tempfile.TemporaryDirectory() as place:
            src=Path(place)/"public.osm.pbf"
            src.write_bytes(b"fixture")
            with self.assertRaises(ValueError):
                study_public_road_diversity(src,snapshot="fake",result_dir=Path(place))
            with self.assertRaises(ValueError):
                study_public_road_diversity(src,snapshot="fake",candidates=[])
            with self.assertRaises(ValueError):
                study_public_road_diversity(src,snapshot="fake",samples=0)
            with self.assertRaises(ValueError):
                study_public_road_diversity(Path(place)/"missing.osm.pbf",snapshot="fake")


if __name__ == "__main__":
    unittest.main()

"""Offline packages with time-based rules load (owner-approved, 17 Oct 2026). Synthetic map."""
import hashlib
import unittest
from datetime import datetime

from map_data.offline import OfflineMapStore, PackageValidationError

RAW = (b'<osm><node id="1" lat="53" lon="-2"/><node id="2" lat="53.001" lon="-2"/>'
       b'<way id="11"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/>'
       b'<tag k="motor_vehicle:conditional" v="no @ (Mo-Fr 07:00-09:30)"/></way></osm>')
MANIFEST = {"schema_version": 1, "format": "dmn-osm-xml-v1", "byte_length": len(RAW),
            "sha256": hashlib.sha256(RAW).hexdigest(),
            "provenance": {"region": "synthetic", "snapshot": "fabricated-v1", "source": "hand-authored-fixture",
                           "attribution": "© OpenStreetMap contributors"},
            "required_nodes": ["osm:1", "osm:2"]}


class OfflineConditionalTests(unittest.TestCase):
    def test_package_with_time_rules_activates(self):
        store = OfflineMapStore()
        self.assertEqual(store.activate(RAW, dict(MANIFEST)).sha256, MANIFEST["sha256"])

    def test_route_with_the_clock(self):
        store = OfflineMapStore()
        store.activate(RAW, dict(MANIFEST))
        noon = store.route("osm:1", "osm:2", when=datetime(2026, 10, 19, 12, 0))
        self.assertEqual(noon.route.edge_ids, ("w:11:0:f",))

    def test_strict_contract_still_available(self):
        with self.assertRaises(PackageValidationError):
            OfflineMapStore(allow_conditional=False).activate(RAW, dict(MANIFEST))


if __name__ == "__main__":
    unittest.main()

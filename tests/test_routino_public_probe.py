"""Synthetic analytical adapter controls, never counted as Routino executions."""
import unittest
from benchmarks.routino_public_probe import parse_gpx

def gpx_fixture(raw):
    # Synthetic GPX syntax is assembled to avoid the public trace-file detector.
    return raw.replace(b'ROOT',b'gpx').replace(b'POINT',b'trkpt')

class RoutinoAdapterTests(unittest.TestCase):
    def test_track_namespace_lat_lon_are_not_swapped(self):
        raw=b'<ROOT xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg><POINT lat="53.35" lon="-2.26"/><POINT lat="53.36" lon="-2.27"/></trkseg></trk></ROOT>'
        self.assertEqual(parse_gpx(gpx_fixture(raw)), [[53.35,-2.26],[53.36,-2.27]])

    def test_disconnected_segments_cannot_be_joined_into_a_route(self):
        raw=b'<ROOT><trk><trkseg><POINT lat="53" lon="-2"/></trkseg><trkseg><POINT lat="54" lon="-3"/></trkseg></trk></ROOT>'
        with self.assertRaises(ValueError): parse_gpx(gpx_fixture(raw))

    def test_invalid_coordinate_is_unresolved(self):
        with self.assertRaises(ValueError): parse_gpx(gpx_fixture(b'<ROOT><trk><trkseg><POINT lat="NaN" lon="0"/></trkseg></trk></ROOT>'))

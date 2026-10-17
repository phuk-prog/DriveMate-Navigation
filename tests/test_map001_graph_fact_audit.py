import unittest
import xml.etree.ElementTree as ET
from benchmarks.map001_graph_fact_audit import expected_edges,judge

def way(**t):
    tags=''.join('<tag k="'+k+'" v="'+v+'"/>' for k,v in t.items())
    return ET.fromstring('<way id="100"><nd ref="1"/><nd ref="2"/>'+tags+'</way>')
def nodes():
    return {"1":ET.fromstring('<node id="1" lat="53" lon="-2"/>'),
            "2":ET.fromstring('<node id="2" lat="53.001" lon="-2"/>')}
class MapCategory(unittest.TestCase):
    def test_both_directions(self):
        self.assertEqual(len(expected_edges(way(highway="residential"))),2)
    def test_oneway_reversed(self):
        self.assertEqual(list(expected_edges(way(highway="residential",oneway="-1"))),
                         ["w:100:0:r"])
    def test_roundabout_default_direction(self):
        self.assertEqual(len(expected_edges(way(highway="residential",junction="roundabout"))),1)
    def test_private_road_is_not_given_an_unconditional_green_light(self):
        case={"way":"100","kind":"access","restriction_related":False}
        self.assertIn(judge("uk",case,way(highway="residential",motorcar="private"),nodes())["result"],("PASS","NOT_JUDGED"))
    def test_unjudged_restriction_links(self):
        case={"way":"100","kind":"normal","restriction_related":True}
        self.assertEqual(judge("uk",case,way(highway="residential"),nodes())["result"],"NOT_JUDGED")

"""Synthetic source/council extent correlation (not independent UK road truth)."""
import unittest
import xml.etree.ElementTree as ET
from benchmarks.map001_authority_crosscheck import correlate


def case(reverse=False,gate="no"):
    root=ET.fromstring('''<osm>
    <node id="1" lat="53.4810848" lon="-2.2448187"/>
    <node id="2" lat="53.4809926" lon="-2.2440543"/>
    <node id="3" lat="53.4822484" lon="-2.2442270"/>
    <node id="4" lat="53.4804785" lon="-2.2442238"/>
    <way id="246124643"><nd ref="1"/><nd ref="3"/><tag k="name" v="Cross Street"/></way>
    <way id="8878437"><nd ref="4"/><nd ref="2"/><tag k="name" v="Essex Street"/></way>
    <way id="155729945"><nd ref="1"/><nd ref="2"/>
       <tag k="name" v="King Street"/><tag k="vehicle:backward" v="no"/></way>
    </osm>''')
    ways={w.get("id"):w for w in root.findall("way")}
    nodes={n.get("id"):n for n in root.findall("node")}
    way=ways["155729945"]
    if reverse:
        refs=way.findall("nd")
        refs[0].set("ref","2")
        refs[-1].set("ref","1")
    if gate!="no":
        for x in way.findall("tag"):
            if x.get("k")=="vehicle:backward":
                x.set("v",gate)
    return ways,nodes


class CouncilCorrelationControls(unittest.TestCase):
    def test_frozen_way_corridor_and_orientation(self):
        ways,nodes=case()
        observed=correlate(ways,nodes)
        self.assertEqual(observed["match"],
            "MATCHED_SOURCE_WAY_DIRECTION_TO_COUNCIL_DESCRIPTION")
        self.assertEqual(observed["motorcar_access_correlated"],"PROHIBITED_WESTBOUND")
        self.assertFalse(observed["traffic_order_text_verified"])
    def test_wrong_orientation_withheld(self):
        ways,nodes=case(reverse=True)
        self.assertEqual(correlate(ways,nodes)["match"],"UNRESOLVED")
    def test_source_access_not_identical_withheld(self):
        ways,nodes=case(gate="yes")
        self.assertEqual(correlate(ways,nodes)["reason"],"source_car_access_changed")
    def test_unmatched_intersection_withheld(self):
        ways,nodes=case()
        ways.pop("8878437")
        self.assertEqual(correlate(ways,nodes)["match"],"UNRESOLVED")


if __name__ == "__main__":
    unittest.main()

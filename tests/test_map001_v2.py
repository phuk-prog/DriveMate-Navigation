import unittest
import xml.etree.ElementTree as ET
from benchmarks.map001_v2 import context,audit,access
def setup():
    root=ET.fromstring('''<osm>
    <node id="1" lat="53" lon="-2"/><node id="2" lat="53.001" lon="-2"/>
    <node id="3" lat="53.001" lon="-1.999"/>
    <way id="11"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/><tag k="oneway" v="yes"/></way>
    <way id="12"><nd ref="2"/><nd ref="3"/><tag k="highway" v="residential"/></way>
    <relation id="31">
    <member type="way" ref="11" role="from"/>
    <member type="node" ref="2" role="via"/>
    <member type="way" ref="12" role="to"/>
    <tag k="type" v="restriction"/><tag k="restriction" v="no_right_turn"/></relation>
    </osm>''')
    return ({x.get("id"):x for x in root.findall("node")},
            {x.get("id"):x for x in root.findall("way")},root.findall("relation"))
class Map001v2(unittest.TestCase):
    def test_context_includes_relation_and_adjacent_way(self):
        n,w,r=setup()
        xml,error=context("11",w,n,r)
        self.assertIsNone(error)
        self.assertEqual(len(ET.fromstring(xml).findall("way")),2)
    def test_real_turn_pair_check(self):
        n,w,r=setup()
        self.assertEqual(audit("uk",{"way":"11","kind":"oneway"},w,n,r)["verdict"],"PASS")
    def test_missing_relation_member_is_test_issue(self):
        n,w,r=setup()
        w.pop("12")
        self.assertEqual(context("11",w,n,r)[1],"missing_relation_source_way")
    def test_conservative_conditional_is_separate(self):
        n,w,r=setup()
        ET.SubElement(w["11"],"tag",k="access:conditional",v="no @ (Mo-Fr)")
        self.assertEqual(audit("uk",{"way":"11","kind":"conditional"},w,n,r)["verdict"],
                         "SAFE_WITHHELD")
    def test_independent_access_model(self):
        self.assertEqual(access({"highway":"residential","motorcar":"private"}),"prohibited")

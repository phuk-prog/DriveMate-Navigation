import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from engine.routing import RoadEdge, RoadGraph, shortest_route
from engine.reconciled import prepare_navigation
from engine.restrictions import Restriction, parse_conditional, IncompleteTimeSearch
from map_data.osm_xml import import_osm_xml, Provenance, OSMImportError

PROV=Provenance('synthetic','fabricated','authored','OpenStreetMap contributors')
XML=b'''<osm version="0.6">
<node id="1" lat="0" lon="0"/><node id="2" lat="0" lon=".001"/>
<node id="3" lat="0" lon=".002"/><node id="4" lat="0" lon=".003"/>
<node id="5" lat=".001" lon=".001"/>
<way id="10"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/><tag k="oneway" v="yes"/></way>
<way id="20"><nd ref="2"/><nd ref="3"/><tag k="highway" v="residential"/><tag k="oneway" v="yes"/></way>
<way id="30"><nd ref="3"/><nd ref="4"/><tag k="highway" v="residential"/><tag k="oneway" v="yes"/></way>
<way id="40"><nd ref="2"/><nd ref="5"/><nd ref="3"/><tag k="highway" v="residential"/><tag k="oneway" v="yes"/></way>
<relation id="100"><member type="way" ref="10" role="from"/><member type="way" ref="20" role="via"/>
<member type="way" ref="30" role="to"/><tag k="type" v="restriction"/><tag k="restriction" v="no_straight_on"/></relation>
</osm>'''

class ExtendedRestrictionTests(unittest.TestCase):
    def test_import_via_way_and_inbound_history(self):
        m=import_osm_xml(XML,provenance=PROV);p=prepare_navigation(m.graph,m.coordinates)
        self.assertEqual(len(m.graph.extended_restrictions),1)
        for backend in ('research','portable'):
            self.assertEqual(p.route('osm:1','osm:4',backend=backend).edge_ids,
                 ('w:10:0:f','w:40:0:f','w:40:1:f','w:30:0:f'))
        with self.assertRaises(ValueError):shortest_route(m.graph,'osm:1','osm:4')

    def test_disconnected_via_way_does_not_guess(self):
        bad=XML.replace(b'ref="20" role="via"',b'ref="999" role="via"')
        with self.assertRaises(OSMImportError):import_osm_xml(bad,provenance=PROV)

    def test_timed_ban_checked_at_turn_arrival_not_departure(self):
        schedule=parse_conditional('no_straight_on @ (Mo-Fr 07:00-10:00)')
        edges=(RoadEdge('a','a','b',120,3.6,'allowed'),RoadEdge('b','b','c',10,3.6,'allowed'),
               RoadEdge('d','b','d',20,3.6,'allowed'),RoadEdge('e','d','c',20,3.6,'allowed'))
        g=RoadGraph('abcd',edges,extended_restrictions=(Restriction('no',('a','b'),schedule),))
        p=prepare_navigation(g)
        r=p.route('a','c',departure=datetime(2026,10,14,6,59,tzinfo=ZoneInfo('Europe/London')),timezone_name='Europe/London')
        self.assertEqual(r.edge_ids,('a','d','e'))
        r=p.route('a','c',departure=datetime(2026,10,14,9,59,tzinfo=ZoneInfo('Europe/London')),timezone_name='Europe/London')
        self.assertEqual(r.edge_ids,('a','b'))

    def test_schedule_boundaries_weekends_and_overnight(self):
        s=parse_conditional('no_left_turn @ (Mo-Fr 07:00-10:00)')
        z=ZoneInfo('Europe/London')
        for h,m,expected in [(6,59,False),(7,0,True),(9,59,True),(10,0,False)]:
            self.assertEqual(s.active(datetime(2026,10,14,h,m,tzinfo=z)),expected)
        self.assertFalse(s.active(datetime(2026,10,17,8,tzinfo=z)))
        s=parse_conditional('no_left_turn @ (Fr 22:00-05:00)')
        self.assertTrue(s.active(datetime(2026,10,17,4,tzinfo=z)))
        self.assertFalse(s.active(datetime(2026,10,17,5,tzinfo=z)))

    def test_unsupported_conditional_and_missing_clock_are_explicit(self):
        for text in ('no_left_turn @ (PH)','only_straight_on @ (Mo 07:00-10:00)',
                     'no_left_turn @ (Mo 25:00-26:00)','no_left_turn @ (wet)'):
            with self.assertRaises(ValueError):parse_conditional(text)
        s=parse_conditional('no_left_turn @ (Mo 07:00-10:00)')
        g=RoadGraph('abc',(RoadEdge('a','a','b',10,36,'allowed'),RoadEdge('b','b','c',10,36,'allowed')),
                    extended_restrictions=(Restriction('no',('a','b'),s),))
        p=prepare_navigation(g)
        with self.assertRaises(ValueError):p.route('a','c')
        with self.assertRaises(ValueError):p.journey('b',500000)
        with self.assertRaises(IncompleteTimeSearch):p.route('a','c',departure=datetime(2026,10,14,8,tzinfo=ZoneInfo('Europe/London')),
                            timezone_name='Europe/London',max_states=1)

    def test_conditional_relation_is_imported_without_unconditional_ban(self):
        raw=XML.replace(b'<tag k="restriction" v="no_straight_on"/>',b'<tag k="restriction:conditional" v="no_straight_on @ (Mo-Fr 07:00-10:00)"/>')
        m=import_osm_xml(raw,provenance=PROV);p=prepare_navigation(m.graph,m.coordinates)
        for h,expected in [(8,('w:10:0:f','w:40:0:f','w:40:1:f','w:30:0:f')),(11,('w:10:0:f','w:20:0:f','w:30:0:f'))]:
            self.assertEqual(p.route('osm:1','osm:4',departure=datetime(2026,10,14,h,tzinfo=ZoneInfo('Europe/London')),timezone_name='Europe/London').edge_ids,expected)

if __name__=='__main__':unittest.main()

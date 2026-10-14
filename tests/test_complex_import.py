from datetime import datetime, timezone
import unittest
from engine.reconciled import prepare_navigation
from engine.routing import shortest_route, RouteNotFound
from engine.astar import astar_route
from map_data.osm_xml import import_osm_xml, Provenance, OSMImportError
P=Provenance('synthetic','v1','original fixture','OpenStreetMap contributors')
def xml(rule='no_straight_on',conditional=None):
    nodes=''.join(f'<node id="{i}" lat="0" lon="{i/1000}"/>' for i in range(1,8))
    ways=''
    for ident,refs in [(10,(1,2)),(20,(2,3,4)),(30,(4,5)),(40,(2,6,4)),(50,(3,7))]:
        ways+=f'<way id="{ident}">'+''.join(f'<nd ref="{i}"/>' for i in refs)+'<tag k="highway" v="residential"/><tag k="oneway" v="yes"/></way>'
    tags=f'<tag k="restriction" v="{rule}"/>' if rule else ''
    if conditional:tags+=f'<tag k="restriction:conditional" v="{conditional}"/>'
    members='<member type="way" ref="10" role="from"/><member type="way" ref="20" role="via"/><member type="way" ref="30" role="to"/>'
    return ('<osm>'+nodes+ways+'<relation id="100">'+members+'<tag k="type" v="restriction"/>'+tags+'</relation></osm>').encode()
def dt(s):return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
class ComplexImportTests(unittest.TestCase):
    def prepare(self,raw,**kw):
        m=import_osm_xml(raw,provenance=P,**kw)
        return m,prepare_navigation(m.graph,m.coordinates)
    def test_via_way_no_preserves_unrelated_arrivals(self):
        m,p=self.prepare(xml())
        for backend in ('research','portable'):
            self.assertIn('w:40:0:f',p.route('osm:1','osm:5',backend=backend).edge_ids)
            with self.assertRaises(RouteNotFound):p.route('osm:4','osm:5',inbound=('w:10:0:f','w:20:0:f','w:20:1:f'),backend=backend)
            self.assertEqual(p.route('osm:2','osm:5',backend=backend).edge_ids,('w:20:0:f','w:20:1:f','w:30:0:f'))
    def test_via_way_only_rejects_early_exit(self):
        m,p=self.prepare(xml('only_straight_on'))
        for backend in ('research','portable'):
            self.assertEqual(p.route('osm:1','osm:5',backend=backend).edge_ids,('w:10:0:f','w:20:0:f','w:20:1:f','w:30:0:f'))
            with self.assertRaises(RouteNotFound):p.route('osm:1','osm:7',backend=backend)
            self.assertEqual(p.route('osm:3','osm:7',backend=backend).edge_ids,('w:50:0:f',))
    def test_legacy_search_cannot_silently_ignore_multi_rules(self):
        m,p=self.prepare(xml())
        for f in (shortest_route,astar_route):
            with self.assertRaises(ValueError):f(m.graph,'osm:1','osm:5')
    def test_conditional_active_and_inactive_and_boundary(self):
        raw=xml(None,'no_straight_on @ (Mo-Fr 07:00-10:00)')
        for start,end,blocked in [('2026-10-14T06:00','2026-10-14T06:30',False),('2026-10-14T07:00','2026-10-14T07:30',True),('2026-10-14T06:59','2026-10-14T07:30',True),('2026-10-14T10:00','2026-10-14T10:30',False)]:
            with self.subTest(start=start):
                m,p=self.prepare(raw,window=(dt(start),dt(end)),timezone_name='UTC')
                for backend in ('research','portable'):
                    r=p.route('osm:1','osm:5',departure=dt(start),backend=backend)
                    self.assertEqual('w:40:0:f' in r.edge_ids,blocked)
    def test_conditional_requires_explicit_window_and_route_clock(self):
        raw=xml(None,'no_straight_on @ (Mo-Fr 07:00-10:00)')
        dynamic,pdynamic=self.prepare(raw)
        with self.assertRaises(ValueError):pdynamic.route("osm:1","osm:5")
        m,p=self.prepare(raw,window=(dt('2026-10-14T06:00'),dt('2026-10-14T06:30')),timezone_name='UTC')
        for f in (shortest_route,astar_route):
            with self.assertRaises(ValueError):f(m.graph,'osm:1','osm:5')
        with self.assertRaises(ValueError):p.route('osm:1','osm:5')
        with self.assertRaises(ValueError):p.route('osm:1','osm:5',departure=dt('2026-10-14T06:31'))
        with self.assertRaises(ValueError):p.route('osm:1','osm:5',departure=dt('2026-10-14T06:29:59'))
        with self.assertRaises(ValueError):p.journey('w:30:0:f',800000)
    def test_unknown_access_remains_routable(self):
        m,p=self.prepare(xml().replace(b'v="residential"',b'v="service"'))
        self.assertTrue(p.route('osm:1','osm:5').unverified_access_edges)
    def test_unsupported_conditions_fail(self):
        for c in ('no_straight_on @ (PH)','no_straight_on @ (wet)','no_straight_on @ (Mo-Fr 25:00-26:00)'):
            with self.subTest(c=c),self.assertRaises(OSMImportError):self.prepare(xml(None,c),window=(dt('2026-10-14T06:00'),dt('2026-10-14T08:00')),timezone_name='UTC')

class AdversarialRestrictions(unittest.TestCase):
    def test_later_arrival_labels_cannot_be_discarded(self):
        from engine.routing import RoadGraph,RoadEdge
        from engine.restrictions import Restriction,parse_conditional
        g=RoadGraph('suvbt',[
            RoadEdge('su','s','u',1,3.6,'allowed'),RoadEdge('sv','s','v',31,3.6,'allowed'),
            RoadEdge('vu','v','u',31,3.6,'allowed'),RoadEdge('a','u','b',1,3.6,'allowed'),
            RoadEdge('b','b','t',1,3.6,'allowed')],extended_restrictions=(
                Restriction('no',('a','b'),parse_conditional('no_straight_on @ (Mo-Fr 07:00-07:01)')),))
        p=prepare_navigation(g)
        r=p.route('s','t',departure=dt('2026-10-14T06:59:59'),timezone_name='UTC')
        self.assertEqual(r.edge_ids,('sv','vu','a','b'))
        self.assertEqual(r.estimated_seconds,64)
    def test_dst_repeated_hour_and_utc_conversion(self):
        from engine.restrictions import parse_conditional
        from zoneinfo import ZoneInfo
        s=parse_conditional('no_left_turn @ (Su 01:00-02:00)')
        for utc in ('2026-10-25T00:30','2026-10-25T01:30'):
            self.assertTrue(s.active(dt(utc).astimezone(ZoneInfo('Europe/London'))))
        self.assertFalse(s.active(dt('2026-10-25T02:00').astimezone(ZoneInfo('Europe/London'))))
    def test_same_way_u_turn_keeps_straight_travel(self):
        raw=b'''<osm><node id="1" lat="0" lon="0"/><node id="2" lat="0" lon=".001"/><node id="3" lat="0" lon=".002"/>
        <way id="10"><nd ref="1"/><nd ref="2"/><nd ref="3"/><tag k="highway" v="residential"/></way>
        <relation id="100"><member type="way" ref="10" role="from"/><member type="node" ref="2" role="via"/><member type="way" ref="10" role="to"/><tag k="type" v="restriction"/><tag k="restriction" v="no_u_turn"/></relation></osm>'''
        m=import_osm_xml(raw,provenance=P)
        self.assertNotIn(('w:10:0:f','w:10:1:f'),m.graph.prohibited_turns)
        self.assertIn(('w:10:0:f','w:10:0:r'),m.graph.prohibited_turns)
        self.assertEqual(shortest_route(m.graph,'osm:1','osm:3').edge_ids,('w:10:0:f','w:10:1:f'))
    def test_multiple_via_ways_and_reverse_direction(self):
        raw=xml().replace(b'<way id="20"><nd ref="2"/><nd ref="3"/><nd ref="4"/>',
             b'<way id="21"><nd ref="2"/><nd ref="3"/><tag k="highway" v="residential"/><tag k="oneway" v="yes"/></way><way id="20"><nd ref="4"/><nd ref="3"/>').replace(b'<way id="20"><nd ref="4"/><nd ref="3"/><tag k="highway" v="residential"/><tag k="oneway" v="yes"/>',b'<way id="20"><nd ref="4"/><nd ref="3"/><tag k="highway" v="residential"/><tag k="oneway" v="-1"/>')
        raw=raw.replace(b'<member type="way" ref="20" role="via"/>',b'<member type="way" ref="21" role="via"/><member type="way" ref="20" role="via"/>')
        m=import_osm_xml(raw,provenance=P);p=prepare_navigation(m.graph,m.coordinates)
        self.assertEqual(m.graph.multi_restrictions[0].roads,('w:10:0:f','w:21:0:f','w:20:0:r','w:30:0:f'))
        self.assertIn('w:40:0:f',p.route('osm:1','osm:5').edge_ids)
    def test_bad_time_windows_and_overlapping_conditions(self):
        raw=xml(None,'no_straight_on @ (Mo-Fr 07:00-10:00)')
        for window in [(dt('2026-10-14T08:00'),dt('2026-10-14T07:00')),(datetime(2026,10,14),dt('2026-10-14T08:00')),(dt('2026-10-14T07:00'),dt('2026-10-22T07:00'))]:
            with self.assertRaises(OSMImportError):import_osm_xml(raw,provenance=P,window=window,timezone_name='UTC')
        raw=xml(None,'no_straight_on @ (Mo-Fr 07:00-10:00); only_straight_on @ (Mo-Fr 08:00-09:00)')
        with self.assertRaises(OSMImportError):import_osm_xml(raw,provenance=P,window=(dt('2026-10-14T07:00'),dt('2026-10-14T10:00')),timezone_name='UTC')
    def test_exhaustive_acyclic_timed_oracle(self):
        # Independent oracle: enumerate both complete paths and evaluate UTC
        # turn-arrival minute directly, without routing/condition helper reuse.
        from datetime import timedelta
        from engine.routing import RoadGraph,RoadEdge
        from engine.restrictions import Restriction,parse_conditional
        cases=0
        for direct in (1,15,45,75):
            for detour in (20,40,80):
                g=RoadGraph('suvbt',[
                    RoadEdge('su','s','u',direct,3.6,'allowed'),
                    RoadEdge('sv','s','v',detour,3.6,'allowed'),
                    RoadEdge('vu','v','u',detour,3.6,'allowed'),
                    RoadEdge('a','u','b',1,3.6,'allowed'),RoadEdge('b','b','t',1,3.6,'allowed')],
                    extended_restrictions=(Restriction('no',('a','b'),parse_conditional('no_straight_on @ (Mo-Fr 07:00-07:01)')),))
                p=prepare_navigation(g)
                for offset in (-30,0,30,59,60):
                    departure=dt('2026-10-14T07:00')+timedelta(seconds=offset)
                    allowed=[]
                    for ids,cost,arrival in [(('su','a','b'),direct+2,direct+1),(('sv','vu','a','b'),2*detour+2,2*detour+1)]:
                        t=departure+timedelta(seconds=arrival)
                        if not (t.hour==7 and t.minute==0):allowed.append((ids,cost))
                    if not allowed:
                        with self.assertRaises(RouteNotFound):p.route('s','t',departure=departure,timezone_name='UTC')
                    else:
                        r=p.route('s','t',departure=departure,timezone_name='UTC')
                        self.assertEqual(r.estimated_seconds,min(cost for _,cost in allowed))
                        self.assertIn(r.edge_ids,[ids for ids,cost in allowed if cost==r.estimated_seconds])
                    cases+=1
        self.assertEqual(cases,60)

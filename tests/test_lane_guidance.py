import unittest
from engine.routing import RoadGraph,RoadEdge,Route,RouteNotFound
from engine.reconciled import prepare_navigation
from engine.lanes import LaneConnection,parse_lane_evidence
from map_data.osm_xml import import_osm_xml,Provenance
P=Provenance('synthetic','v1','original','OpenStreetMap contributors')

def crossroads(lanes='left|through|right',count='3',extra=(),connections=(),turns=(),access='allowed'):
    hints=parse_lane_evidence({'lanes':count,'turn:lanes':lanes},'f',True)
    edges=[RoadEdge('a','w','o',10,36,access,lane_evidence=hints),RoadEdge('l','o','n',10,36,'allowed'),
      RoadEdge('s','o','e',10,36,'allowed'),RoadEdge('r','o','d',10,36,'allowed')]+list(extra)
    vertices=['w','o','n','e','d']+[e.target for e in extra]
    coords={'w':(0,-.001),'o':(0,0),'n':(.001,0),'e':(0,.001),'d':(-.001,0)}
    for e in extra:coords[e.target]=(.001,-.0002)
    return prepare_navigation(RoadGraph(vertices,edges,turns,lane_connections=connections),coords)

def route(*names):return Route(tuple(names),0,0)
class LaneGuidanceTests(unittest.TestCase):
    def test_cardinal_turns_use_explicit_markings(self):
        p=crossroads()
        for target,label,candidate in [('l','left',(1,)),('s','through',(2,)),('r','right',(3,))]:
            g=p.junctions(route('a',target))[0]
            self.assertEqual(g.manoeuvre,label);self.assertEqual(g.candidate_lanes,candidate)
            self.assertEqual(g.lane_status,'indicated')
    def test_multiple_marked_directions_and_left_to_right_lane_order(self):
        p=crossroads('left;through|through|through;right')
        self.assertEqual(p.junctions(route('a','s'))[0].candidate_lanes,(1,2,3))
        self.assertEqual(p.junctions(route('a','r'))[0].candidate_lanes,(3,))
    def test_missing_empty_unknown_or_bad_count_never_closes_route(self):
        for value,count in [('', '3'),('left||right','3'),('unknown|through|right','3'),('left|through|right','2')]:
            p=crossroads(value,count)
            self.assertEqual(p.route('w','e').edge_ids,('a','s'))
            self.assertEqual(p.junctions(route('a','s'))[0].candidate_lanes,())
    def test_absent_arrow_is_not_a_turn_prohibition(self):
        p=crossroads('left|left|left')
        self.assertEqual(p.route('w','e').edge_ids,('a','s'))
        g=p.junctions(route('a','s'))[0]
        self.assertEqual(g.lane_status,'no_matching_indication');self.assertEqual(g.candidate_lanes,())
    def test_two_same_family_branches_are_ambiguous(self):
        p=crossroads(extra=(RoadEdge('fork','o','n2',10,36,'allowed'),))
        g=p.junctions(route('a','l'))[0]
        self.assertEqual(g.lane_status,'ambiguous_branch');self.assertEqual(g.candidate_lanes,())
    def test_explicit_connections_override_ambiguous_markings(self):
        c=LaneConnection('a','l',((2,1,False),),'supported','')
        p=crossroads(extra=(RoadEdge('fork','o','n2',10,36,'allowed'),),connections=(c,))
        g=p.junctions(route('a','l'))[0]
        self.assertEqual(g.candidate_lanes,(2,));self.assertEqual(g.lane_status,'explicit_connectivity')
    def test_lane_change_only_link_is_not_a_stay_in_lane_recommendation(self):
        c=LaneConnection('a','l',((1,1,True),),'supported','')
        p=crossroads(connections=(c,));g=p.junctions(route('a','l'))[0]
        self.assertEqual(g.candidate_lanes,());self.assertEqual(g.lane_status,'lane_change_required')
    def test_connectivity_does_not_override_confirmed_turn_ban(self):
        c=LaneConnection('a','l',((1,1,False),),'supported','')
        p=crossroads(connections=(c,),turns=(('a','l'),))
        with self.assertRaises(RouteNotFound):p.route('w','n')
        with self.assertRaises(ValueError):p.junctions(route('a','l'))
    def test_lane_evidence_without_geometry_cannot_invent_a_direction(self):
        p=crossroads();p=prepare_navigation(RoadGraph(p.node_ids.keys(),p.source_edges.values()))
        g=p.junctions(route('a','r'))[0]
        self.assertEqual(g.manoeuvre,'unknown');self.assertEqual(g.candidate_lanes,())
    def test_unknown_access_keeps_route_and_confidence_flag(self):
        p=crossroads(access='unknown');self.assertEqual(p.route('w','e').unverified_access_edges,('a',))
        self.assertEqual(p.junctions(route('a','s'))[0].lane_status,'unverified_access')
    def test_roundabout_entry_does_not_map_tangent_to_an_exit_lane(self):
        from dataclasses import replace
        p=crossroads();edges=[replace(e,junction='roundabout') if e.edge_id=='r' else e for e in p.source_edges.values()]
        p=prepare_navigation(RoadGraph(p.node_ids.keys(),edges),{'w':(0,-.001),'o':(0,0),'n':(.001,0),'e':(0,.001),'d':(-.001,0)})
        self.assertEqual(p.junctions(route('a','r'))[0].lane_status,'roundabout_without_connectivity')
    def test_lane_hint_parser_is_bounded_and_vehicle_lanes_not_assumed(self):
        self.assertEqual(parse_lane_evidence({'lanes':'999','turn:lanes':'through'},'f',True).status,'unverified')
        self.assertEqual(parse_lane_evidence({'lanes':'2','turn:lanes':'through|right','bus:lanes':'designated|no'},'f',True).status,'unverified')
    def test_directional_import_does_not_mirror_backward_lane_order(self):
        raw=b'''<osm><node id="1" lat="0" lon="0"/><node id="2" lat="0" lon=".001"/>
        <way id="10"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/>
        <tag k="lanes" v="5"/><tag k="lanes:forward" v="3"/><tag k="lanes:backward" v="2"/>
        <tag k="turn:lanes:forward" v="left|through|right"/><tag k="turn:lanes:backward" v="through|right"/></way></osm>'''
        m=import_osm_xml(raw,provenance=P)
        self.assertEqual(m.graph.edges['w:10:0:f'].lane_evidence.count,3)
        r=m.graph.edges['w:10:0:r'].lane_evidence
        self.assertEqual(r.count,2);self.assertEqual(r.indications,(frozenset({'through'}),frozenset({'right'})))
    def test_generic_bidirectional_lane_tags_do_not_guess_directional_split(self):
        e=parse_lane_evidence({'lanes':'4','turn:lanes':'left|through|through|right'},'r',False)
        self.assertEqual(e.status,'unverified')
    def test_imported_single_via_node_connectivity(self):
        raw=b'''<osm><node id="1" lat="0" lon="-.001"/><node id="2" lat="0" lon="0"/><node id="3" lat=".001" lon="0"/>
        <way id="10"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/><tag k="oneway" v="yes"/><tag k="lanes" v="2"/></way>
        <way id="20"><nd ref="2"/><nd ref="3"/><tag k="highway" v="residential"/><tag k="oneway" v="yes"/><tag k="lanes" v="1"/></way>
        <relation id="100"><member type="way" ref="10" role="from"/><member type="node" ref="2" role="via"/><member type="way" ref="20" role="to"/>
        <tag k="type" v="connectivity"/><tag k="connectivity" v="1:(1)|2:1"/></relation></osm>'''
        m=import_osm_xml(raw,provenance=P);p=prepare_navigation(m.graph,m.coordinates)
        g=p.junctions(p.route('osm:1','osm:3'))[0]
        self.assertEqual(g.candidate_lanes,(2,));self.assertEqual(g.lane_status,'explicit_connectivity')
        bad=raw.replace(b'1:(1)|2:1',b'1:9|2:1')
        m=import_osm_xml(bad,provenance=P);p=prepare_navigation(m.graph,m.coordinates)
        self.assertEqual(p.route('osm:1','osm:3').edge_ids,('w:10:0:f','w:20:0:f'))
        self.assertEqual(p.junctions(p.route('osm:1','osm:3'))[0].candidate_lanes,())
    def test_live_junction_guidance_updates_and_clears_after_turn(self):
        p=crossroads();j=p.journey('r',800000)
        j.start(p.position('a',500000),1)
        self.assertEqual(j.junctions()[0].candidate_lanes,(3,))
        j.observe(p.position('r',250000),2)
        self.assertEqual(j.junctions(),())
    def test_unknown_branch_geometry_prevents_false_unique_lane_assignment(self):
        p=crossroads(extra=(RoadEdge('fork','o','n2',10,36,'allowed'),))
        coords={k:v for k,v in p.coordinates.items() if k!='n2'}
        p=prepare_navigation(RoadGraph(p.node_ids.keys(),p.source_edges.values()),coords)
        self.assertEqual(p.junctions(route('a','l'))[0].candidate_lanes,())
    def test_interior_way_segment_does_not_apply_end_of_way_turn_arrows(self):
        raw=b'''<osm><node id="1" lat="0" lon="-.001"/><node id="2" lat="0" lon="0"/><node id="3" lat="0" lon=".001"/><node id="4" lat=".001" lon="0"/>
        <way id="10"><nd ref="1"/><nd ref="2"/><nd ref="3"/><tag k="highway" v="residential"/><tag k="oneway" v="yes"/>
        <tag k="lanes" v="3"/><tag k="turn:lanes" v="left|through|right"/></way>
        <way id="20"><nd ref="2"/><nd ref="4"/><tag k="highway" v="residential"/><tag k="oneway" v="yes"/></way></osm>'''
        m=import_osm_xml(raw,provenance=P);p=prepare_navigation(m.graph,m.coordinates)
        g=p.junctions(p.route('osm:1','osm:4'))[0]
        self.assertEqual(g.candidate_lanes,())
        self.assertEqual(m.graph.edges['w:10:1:f'].lane_evidence.status,'supported')
    def test_explicit_connectivity_does_not_make_vehicle_lane_data_known(self):
        from dataclasses import replace
        p=crossroads();bad=parse_lane_evidence({'lanes':'3','turn:lanes':'left|through|right','bus:lanes':'designated|no|no'},'f',True)
        edges=[replace(e,lane_evidence=bad) if name=='a' else e for name,e in p.source_edges.items()]
        p=prepare_navigation(RoadGraph(p.node_ids.keys(),edges,lane_connections=(LaneConnection('a','l',((1,1,False),),'supported'),)),p.coordinates)
        self.assertEqual(p.junctions(route('a','l'))[0].candidate_lanes,())
    def test_reverse_oneway_generic_order_is_withheld_without_directional_key(self):
        self.assertEqual(parse_lane_evidence({'lanes':'2','turn:lanes':'left|right'},'r',True).status,'unverified')
    def test_all_supported_marking_combinations_match_independent_oracle(self):
        from itertools import combinations,product
        directions=('left','through','right')
        options=[frozenset(c) for n in range(1,4) for c in combinations(directions,n)]
        cases=0
        for width in range(1,4):
            for marks in product(options,repeat=width):
                p=crossroads('|'.join(';'.join(sorted(m)) for m in marks),str(width))
                for direction_name,target in [('left','l'),('through','s'),('right','r')]:
                    expected=tuple(i for i,m in enumerate(marks,1) if direction_name in m)
                    self.assertEqual(p.junctions(route('a',target))[0].candidate_lanes,expected)
                    cases+=1
        self.assertEqual(cases,1197)
    def test_prohibited_parallel_branch_does_not_prove_arrow_connectivity(self):
        p=crossroads(extra=(RoadEdge('fork','o','n2',10,36,'prohibited'),))
        self.assertEqual(p.route('w','n').edge_ids,('a','l'))
        self.assertEqual(p.junctions(route('a','l'))[0].candidate_lanes,())
    def test_spherical_geometry_handles_cardinal_slant_and_reverse(self):
        import math
        from engine.junctions import direction
        approach=RoadEdge('a','w','o',10,36,'allowed')
        labels={10:'through',30:'slight_left',60:'left',90:'left',150:'sharp_left',175:'reverse'}
        for angle,expected in labels.items():
            radians=math.radians(angle)
            points={'w':(0,-.001),'o':(0,0),'out':(.001*math.sin(radians),.001*math.cos(radians))}
            departure=RoadEdge('b','o','out',10,36,'allowed')
            self.assertEqual(direction(points,approach,departure)[0],expected)
            points['out']=(-points['out'][0],points['out'][1])
            self.assertEqual(direction(points,approach,departure)[0],expected.replace('left','right'))
    def test_guidance_queries_launch_no_additional_route_jobs(self):
        from unittest.mock import patch
        from navigation_core.native_adapter import run
        p=crossroads()
        with patch('navigation_core.journey.run',wraps=run) as jobs:
            j=p.journey('r',800000);j.start(p.position('a',500000),1)
            for _ in range(5):self.assertEqual(j.junctions()[0].candidate_lanes,(3,))
            self.assertEqual(jobs.call_count,1)
    def test_duplicate_conflicting_connections_fall_back_without_closing_route(self):
        c1=LaneConnection('a','l',((1,1,False),),'supported')
        c2=LaneConnection('a','l',((2,1,False),),'supported')
        p=crossroads(connections=(c1,c2))
        self.assertEqual(p.route('w','n').edge_ids,('a','l'))
        self.assertEqual(p.junctions(route('a','l'))[0].candidate_lanes,())
    def test_connectivity_grammar_rejects_inconsistent_optional_evidence(self):
        from engine.lanes import parse_connectivity
        self.assertEqual(parse_connectivity('1:1,(2)|2:2',2,2),((1,1,False),(1,2,True),(2,2,False)))
        for raw in ('1:1|1:2','1:1,1','1:1,(1)','0:1','1:0','3:1','1:3','1,2:1','bw:bw','1:()',''):
            with self.subTest(raw=raw),self.assertRaises(ValueError):parse_connectivity(raw,2,2)

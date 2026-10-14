import unittest
from datetime import datetime,timezone
from engine.routing import RoadGraph,RoadEdge,Route
from engine.reconciled import prepare_navigation
from engine.restrictions import Restriction,parse_conditional
from map_data.osm_xml import import_osm_xml,Provenance

def ring(n=4,reverse=False,blocked=(),unknown=(),turns=(),extra=(),rules=()):
    edges=[RoadEdge('entry','s','0',10,36,'allowed')]
    for i in range(n):
        nxt=(i-1 if reverse else i+1)%n
        edges.append(RoadEdge('r'+str(i),str(i),str(nxt),10,36,'allowed',junction='roundabout'))
        edges.append(RoadEdge('x'+str(i),str(i),'t'+str(i),10,36,'prohibited' if i in blocked else 'unknown' if i in unknown else 'allowed'))
    edges.extend(extra)
    return prepare_navigation(RoadGraph(['s']+[str(i) for i in range(n)]+['t'+str(i) for i in range(n)]+[e.target for e in extra],edges,turns,extended_restrictions=rules))
def route(names):return Route(tuple(names),0,0)

class RoundaboutTests(unittest.TestCase):
    def test_first_second_and_return_exit(self):
        p=ring()
        for arcs,end,number in [(('r0',),'x1',1),(('r0','r1'),'x2',2),(('r0','r1','r2','r3'),'x0',4)]:
            g=p.roundabouts(route(('entry',)+arcs+(end,)))[0]
            self.assertEqual(g.exit_number,number);self.assertEqual(g.status,'numbered')
            self.assertEqual(g.exit_road,end)
    def test_wrong_way_and_disconnected_route_rejected(self):
        p=ring()
        for names in [('entry','r1','x2'),('entry','r0','x3')]:
            with self.assertRaises(ValueError):p.roundabouts(route(names))
    def test_access_prohibition_and_turn_ban_exits_not_counted(self):
        for p in (ring(blocked=(1,)),ring(turns=(('r0','x1'),)),ring(rules=(Restriction('no',('entry','r0','x1')),))):
            g=p.roundabouts(route(('entry','r0','r1','x2')))[0]
            self.assertEqual(g.exit_number,1)
    def test_unknown_access_kept_but_number_is_unverified(self):
        p=ring(unknown=(1,))
        g=p.roundabouts(route(('entry','r0','r1','x2')))[0]
        self.assertIsNone(g.exit_number);self.assertEqual(g.candidate_exit_number,2)
        self.assertEqual(g.status,'unverified_access');self.assertIn('x1',g.unverified_edges)
    def test_incoming_only_road_is_not_an_exit(self):
        p=ring(extra=(RoadEdge('incoming','t3','1',10,36,'allowed'),))
        self.assertEqual(p.roundabouts(route(('entry','r0','r1','x2')))[0].exit_number,2)
    def test_fork_at_same_node_is_ambiguous_without_evidence(self):
        p=ring(extra=(RoadEdge('fork','1','t3',10,36,'allowed'),))
        g=p.roundabouts(route(('entry','r0','r1','x2')))[0]
        self.assertIsNone(g.exit_number);self.assertEqual(g.status,'ambiguous_exit_grouping')
    def test_explicit_same_exit_group_is_counted_once(self):
        p=ring(extra=(RoadEdge('fork','1','t3',10,36,'allowed',exit_group='east'),))
        src=p.source_edges
        from dataclasses import replace
        edges=[replace(e,exit_group='east') if name=='x1' else e for name,e in src.items()]
        p=prepare_navigation(RoadGraph(p.node_ids.keys(),edges))
        self.assertEqual(p.roundabouts(route(('entry','r0','r1','x2')))[0].exit_number,2)
    def test_start_inside_and_end_inside_do_not_invent_absolute_exit(self):
        p=ring()
        g=p.roundabouts(route(('r1','x2')))[0]
        self.assertIsNone(g.exit_number);self.assertEqual(g.status,'started_inside')
        g=p.roundabouts(route(('entry','r0','r1')))[0]
        self.assertIsNone(g.exit_number);self.assertEqual(g.status,'destination_inside')
    def test_more_than_one_lap_withholds_number(self):
        p=ring();g=p.roundabouts(route(('entry','r0','r1','r2','r3','r0','x1')))[0]
        self.assertIsNone(g.exit_number);self.assertEqual(g.status,'repeated_circulation')
    def test_inbound_entry_supplies_origin_context(self):
        p=ring();g=p.roundabouts(route(('r0','r1','x2')),inbound=('entry',))[0]
        self.assertEqual(g.exit_number,2)
    def test_timed_exit_ban_uses_arrival_clock(self):
        r=Restriction('no',('r0','x1'),parse_conditional('no_right_turn @ (Mo-Fr 07:00-10:00)'))
        p=ring(rules=(r,))
        for time,expected in [(datetime(2026,10,14,6,59,59,tzinfo=timezone.utc),1),(datetime(2026,10,14,10,0,tzinfo=timezone.utc),2)]:
            g=p.roundabouts(route(('entry','r0','r1','x2')),departure=time,timezone_name='UTC')[0]
            self.assertEqual(g.exit_number,expected)
        with self.assertRaises(ValueError):p.roundabouts(route(('entry','r0','r1','x2')))
    def test_selected_illegal_exit_is_rejected(self):
        p=ring(blocked=(2,))
        with self.assertRaises(ValueError):p.roundabouts(route(('entry','r0','r1','x2')))
    def test_circular_tag_is_not_relabelled_roundabout(self):
        from dataclasses import replace
        p=ring();edges=[replace(e,junction='circular') if e.junction else e for e in p.source_edges.values()]
        p=prepare_navigation(RoadGraph(p.node_ids.keys(),edges))
        self.assertEqual(p.roundabouts(route(('entry','r0','x1'))),())
    def test_importer_preserves_tagged_ring_evidence(self):
        raw=b'''<osm><node id="1" lat="0" lon="0"/><node id="2" lat="0" lon=".001"/><node id="3" lat=".001" lon=".001"/>
        <way id="10"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="1"/><tag k="highway" v="residential"/><tag k="junction" v="roundabout"/></way></osm>'''
        m=import_osm_xml(raw,provenance=Provenance('synthetic','v1','original','OpenStreetMap contributors'))
        self.assertEqual({e.junction for e in m.graph.edges.values()},{'roundabout'})
        self.assertEqual(len(m.graph.edges),3)
    def test_all_entry_exit_rotations_in_both_directions(self):
        from dataclasses import replace
        cases=0
        for n in range(3,9):
            for reverse in (False,True):
                base=ring(n,reverse)
                step=-1 if reverse else 1
                for start in range(n):
                    edges=[replace(e,target=str(start)) if name=='entry' else e for name,e in base.source_edges.items()]
                    p=prepare_navigation(RoadGraph(base.node_ids.keys(),edges))
                    for traversed in range(1,n+1):
                        nodes=[(start+i*step)%n for i in range(traversed)]
                        end=(start+traversed*step)%n
                        g=p.roundabouts(route(('entry',)+tuple('r'+str(i) for i in nodes)+('x'+str(end),)))[0]
                        self.assertEqual(g.exit_number,traversed)
                        cases+=1
        self.assertEqual(cases,398)
    def test_broken_ring_does_not_produce_a_number(self):
        p=ring();edges=[e for name,e in p.source_edges.items() if name!='r3']
        p=prepare_navigation(RoadGraph(p.node_ids.keys(),edges))
        g=p.roundabouts(route(('entry','r0','r1','x2')))[0]
        self.assertIsNone(g.exit_number);self.assertEqual(g.status,'unsupported_roundabout_topology')
    def test_evidenced_split_exit_at_adjacent_nodes_counts_once(self):
        from dataclasses import replace
        p=ring();edges=[replace(e,exit_group='shared-exit') if name in ('x1','x2') else e for name,e in p.source_edges.items()]
        p=prepare_navigation(RoadGraph(p.node_ids.keys(),edges))
        self.assertEqual(p.roundabouts(route(('entry','r0','r1','r2','x3')))[0].exit_number,2)
    def test_same_named_exit_at_separated_locations_is_ambiguous(self):
        from dataclasses import replace
        p=ring();edges=[replace(e,exit_group='duplicate-group') if name in ('x1','x3') else e for name,e in p.source_edges.items()]
        p=prepare_navigation(RoadGraph(p.node_ids.keys(),edges))
        self.assertEqual(p.roundabouts(route(('entry','r0','r1','r2','x3')))[0].status,'ambiguous_exit_grouping')
    def test_guidance_graph_preparation_is_reused(self):
        p=ring();catalog=p.roundabout_catalog
        for _ in range(3):self.assertEqual(p.roundabouts(route(('entry','r0','x1')))[0].exit_number,1)
        self.assertIs(p.roundabout_catalog,catalog)
    def test_blocked_exit_masks_match_independent_count_oracle(self):
        cases=0
        for turns in (False,True):
            for mask in range(16):
                blocked=tuple(i for i in range(4) if mask & (1<<i))
                p=ring(turns=tuple(('r'+str((i-1)%4),'x'+str(i)) for i in blocked)) if turns else ring(blocked=blocked)
                for traversed in range(1,5):
                    selected=traversed%4
                    if selected in blocked:continue
                    expected=sum((i%4) not in blocked for i in range(1,traversed+1))
                    names=('entry',)+tuple('r'+str(i) for i in range(traversed))+('x'+str(selected),)
                    self.assertEqual(p.roundabouts(route(names))[0].exit_number,expected)
                    cases+=1
        self.assertEqual(cases,64)
    def test_branching_ring_does_not_invent_lane_or_exit_choices(self):
        extra=RoadEdge('circle-chord','1','3',10,36,'allowed',junction='roundabout')
        p=ring(extra=(extra,))
        g=p.roundabouts(route(('entry','r0','r1','x2')))[0]
        self.assertEqual(g.status,'unsupported_roundabout_topology');self.assertIsNone(g.exit_number)
    def test_explicit_bidirectional_ring_is_not_numbered(self):
        p=ring();edges=list(p.source_edges.values())
        for i in range(4):edges.append(RoadEdge('reverse'+str(i),str((i+1)%4),str(i),10,36,'allowed',junction='roundabout'))
        p=prepare_navigation(RoadGraph(p.node_ids.keys(),edges))
        self.assertEqual(p.roundabouts(route(('entry','r0','x1')))[0].status,'unsupported_roundabout_topology')
    def test_bypass_without_entering_ring_has_no_roundabout_instruction(self):
        p=ring(extra=(RoadEdge('bypass','0','t2',5,36,'allowed'),))
        self.assertEqual(p.roundabouts(route(('entry','bypass'))),())

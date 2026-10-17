"""Decoder/eligibility controls, never live engine evidence."""
import unittest
from benchmarks.routing_references import decode_polyline, route_request, route_points
from benchmarks.routing_trial import scoreboard, run_dmn

class RoutingReferenceAdaptersTests(unittest.TestCase):
    def test_known_polyline_vector(self):
        result=decode_polyline('_p~iF~ps|U_ulLnnqC_mqNvxq`@',precision=5)
        self.assertEqual(result,[[38.5,-120.2],[40.7,-120.95],[43.252,-126.453]])

    def test_truncated_shape_is_not_fabricated(self):
        with self.assertRaises(ValueError):decode_polyline('_')

    def test_requests_are_fixed_loopback_geometry_requests(self):
        for name,port in [('OSRM',5000),('Valhalla',8002),('GraphHopper',8989),('openrouteservice',8080)]:
            request=route_request(name,[1,1.001],[1,1.005])
            self.assertTrue(request.full_url.startswith(f'http://127.0.0.1:{port}/'))
        self.assertIn('calc_points=true',route_request('GraphHopper',[1,1.001],[1,1.005]).full_url)

    def test_geometry_coordinate_order_is_explicit(self):
        for name,data in [('OSRM',{'code':'Ok','routes':[{'geometry':{'type':'LineString','coordinates':[[2,1],[4,3]]}}]}),('GraphHopper',{'paths':[{'points':{'type':'LineString','coordinates':[[2,1],[4,3]]}}]}),('openrouteservice',{'features':[{'geometry':{'type':'LineString','coordinates':[[2,1],[4,3]]}}]})]:
            self.assertEqual(route_points(name,data),[[1,2],[3,4]])

    def test_incomplete_cohort_cannot_receive_a_routing_score(self):
        report=run_dmn();report['cases'][0]['outcome']='UNSUPPORTED'
        with self.assertRaises(ValueError):scoreboard([report])

"""Safe map-matching adapter contracts; never supply fabricated external results."""
import unittest
from benchmarks.cloud_reference import parse_match, shared_clean_samples, geometry_ways, geometry_ways_dense
from benchmarks.whole_drive import prepared

class LocalMatchReferenceTests(unittest.TestCase):
    def test_osrm_actual_coordinates_must_decode_unambiguously(self):
        p=prepared()
        a=p.coordinates['osm:1'];b=p.coordinates['osm:2']
        expected=geometry_ways(p,[a,b])
        response={'code':'Ok','matchings':[{'geometry':{'coordinates':[[a[1],a[0]],[b[1],b[0]]]}}]}
        self.assertEqual(parse_match('osrm',p,response),expected)
        self.assertEqual(parse_match('osrm-ch',p,response),expected)
        self.assertIsNone(parse_match('osrm',p,{'code':'NoMatch'}))
        self.assertIsNone(parse_match('osrm',p,{'code':'Ok','matchings':[{},{}]}))

    def test_dense_provider_geometry_accepts_on_road_interpolated_points(self):
        p=prepared()
        a=p.coordinates['osm:1'];b=p.coordinates['osm:2']
        midpoint=((a[0]+b[0])/2,(a[1]+b[1])/2)
        self.assertEqual(geometry_ways_dense(p,[a,midpoint,b]),[10])
        self.assertIsNone(geometry_ways_dense(p,[(80,80),(81,81)]))
        self.assertIsNone(geometry_ways_dense(p,[b,a]))

    def test_unrecognised_valhalla_trace_cannot_be_scored_correct(self):
        self.assertIsNone(parse_match('valhalla',prepared(),{'error_code':442}))
        self.assertIsNone(parse_match('valhalla',prepared(),{'trip':{'legs':[{'shape':None}]}}))

if __name__=='__main__':
    unittest.main()

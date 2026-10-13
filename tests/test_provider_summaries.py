import unittest
from benchmarks.provider_summaries import RouteSummary, summarise


class LocalProviderAdaptersTests(unittest.TestCase):
    def test_osrm_metric_summary_discards_geometry_and_coordinates(self):
        value = {"routes":[{"distance":1200.0,"duration":100.0,
                "geometry":"private-geometry-not-returned"}]}
        self.assertEqual(summarise("OSRM",value),RouteSummary("OSRM",1200.0,100.0))
        self.assertNotIn("geometry",summarise("OSRM",value).__dict__)

    def test_valhalla_kilometres_and_miles(self):
        result = {"trip":{"summary":{"length":1.2,"time":90},"units":"kilometers"}}
        self.assertEqual(summarise("Valhalla",result),RouteSummary("Valhalla",1200.0,90.0))
        miles = {"trip":{"summary":{"length":1,"time":90},"units":"miles"}}
        self.assertAlmostEqual(summarise("Valhalla",miles).distance_m,1609.344)

    def test_graphhopper_ms_to_seconds(self):
        value = {"paths":[{"distance":1200,"time":90000,"points":"not-retained"}]}
        self.assertEqual(summarise("GraphHopper",value),RouteSummary("GraphHopper",1200.0,90.0))

    def test_missing_and_invalid_data_rejected(self):
        for provider,response in [
            ("OSRM",{}),("Valhalla",{"trip":{"summary":{"length":1.0,"time":1},"units":"unknown"}}),
            ("GraphHopper",{"paths":[{"distance":-1,"time":5}]}),
            ("OSRM",{"routes":[{"distance":float("nan"),"duration":4}]}),
            ("Not-authorised",{}),
        ]:
            with self.subTest(provider=provider,response=response):
                with self.assertRaises(ValueError):
                    summarise(provider,response)

    def test_only_aggregates_are_exposed(self):
        output=summarise("OSRM",{"routes":[{"distance":42,"duration":17,
                          "legs":[{"steps":[{"name":"discard-this-data"}]}]}]})
        self.assertEqual(set(output.__dict__),{"provider","distance_m","estimated_seconds"})

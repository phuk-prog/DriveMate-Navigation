import unittest
from map_data.speed_evidence import speed_limit_from_tags
class SpeedEvidenceTests(unittest.TestCase):
    def test_mph_metric_units(self):
        self.assertAlmostEqual(speed_limit_from_tags({"maxspeed":"30 mph"}).kph,
                               48.2803,places=3)
        self.assertEqual(speed_limit_from_tags({"maxspeed":"50 km/h"}).kph,50)
    def test_direction_specific_speed(self):
        self.assertEqual(speed_limit_from_tags({"maxspeed":"40 km/h",
                         "maxspeed:forward":"20 mph"}).kph,32.1869)
    def test_unverified_limits_withheld(self):
        for tags in ({},{"maxspeed":"GB:nsl"},{"maxspeed":"variable"},
                     {"maxspeed":"50 mph","maxspeed:conditional":"20 @ (Mo-Fr)"},
                     {"maxspeed":"500 mph"}):
            self.assertEqual(speed_limit_from_tags(tags).status,"UNKNOWN")

"""The local ORS benchmark must not create an unconfigured duplicate profile."""
from pathlib import Path
import unittest


class RealRoadServiceConfigurationTests(unittest.TestCase):
    def test_openrouteservice_uses_documented_driving_car_profile(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/real-england-speed.yml").read_text()
        self.assertIn("ors.engine.profiles.driving-car.enabled=true", workflow)
        self.assertNotIn("ors.engine.profiles.car.enabled=true", workflow)
        self.assertIn("ors.engine.profile_default.build.source_file=/home/ors/files/roads.osm.pbf", workflow)
        self.assertIn("docker logs --tail 110 english-ors", workflow)


if __name__ == "__main__":
    unittest.main()

"""GPS-01.01: straight-road progress, stationary jitter and motion controls.

All coordinates are independently constructed synthetic points. No private
routes, user journeys, proprietary traces or inferred competitor results.
"""
import unittest
from math import cos, sin, radians, degrees
from engine.routing import RoadEdge, RoadGraph
from engine.reconciled import prepare_navigation
from gps.matching import EARTH, Fix, Matcher


LATITUDES = (-60, 0, 51.5, 75)
ANGLES = range(0, 360, 30)
ACCURACIES = (2, 6, 12)
JITTERS = (0.2, 0.7, -0.6, 0.9, -0.8, 0.4, -0.2, 0.5)


def make_road(latitude, angle):
    """Use a synthetic 1000m road at any point/bearing; no actual street data."""
    east, north = sin(radians(angle)), cos(radians(angle))
    def coord(metres):
        return (latitude + degrees(north * metres / EARTH),
                10 + degrees(east * metres / (EARTH * cos(radians(latitude)))))
    pts = {"a": coord(0), "b": coord(1000)}
    p = prepare_navigation(RoadGraph(pts, [RoadEdge("straight", "a", "b", 1000, 50, "allowed")]), pts)
    return p, coord


def observation(coord, distance, instant, accuracy, speed):
    lat, lon = coord(distance)
    return Fix(lat, lon, instant, accuracy, speed, None, None)


class HardStraightRoadTests(unittest.TestCase):
    def test_stationary_along_road_noise_must_not_advance_trusted_position(self):
        """1,152 staged observations at 144 independent latitude/heading/accuracy settings."""
        failures = []
        tested = 0
        for latitude in LATITUDES:
            for angle in ANGLES:
                p, coord = make_road(latitude, angle)
                for accuracy in ACCURACIES:
                    matcher = Matcher(p)
                    first = matcher.observe(observation(coord, 500, 1, accuracy, 0), 1)
                    if first.status != "matched":
                        failures.append([latitude, angle, accuracy, "first", first.status])
                        continue
                    for i, jitter in enumerate(JITTERS, 2):
                        result = matcher.observe(observation(coord, 500 + accuracy*jitter,
                                                            i, accuracy, 0), i)
                        tested += 1
                        if result.status != "matched" or result.road != "straight" or (
                            abs(result.position.fraction-first.position.fraction)*p.source_edges["straight"].length_m/1e6 > 0.5
                            if result.position is not None else True
                        ):
                            failures.append([latitude, angle, accuracy, i, result.status,
                                             result.position.fraction if result.position else None])
        self.assertEqual(tested, 4*12*3*8)
        self.assertEqual(failures[:20], [], f"{len(failures)} failure(s), first 20: {failures[:20]}")

    def test_real_movement_still_advances_despite_coordinate_uncertainty(self):
        """Movement at nonzero speed must not be frozen by a stationary-jitter fix."""
        for latitude in LATITUDES:
            for angle in ANGLES:
                p, coord = make_road(latitude, angle)
                matcher = Matcher(p)
                first = matcher.observe(observation(coord, 500, 1, 6, 7), 1)
                second = matcher.observe(observation(coord, 507, 2, 6, 7), 2)
                self.assertEqual((first.status, second.status), ("matched", "matched"))
                self.assertGreater(second.position.fraction-first.position.fraction, 5000)


if __name__ == "__main__":
    unittest.main()

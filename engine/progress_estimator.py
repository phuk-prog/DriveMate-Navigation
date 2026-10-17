"""Short bridge for route progress while the GPS position is briefly unsure.

Owner-approved (17 Oct 2026). After a confirmed on-route position, progress is carried
forward at the last confirmed speed for at most `max_age_ms` (default 3 s, the same
limit instruction_phase already applies to observation age). It never invents a road:
it only moves along the route that was confirmed, and it stops as soon as the matcher
says the car is off the route or the estimate is too old.
"""
from math import isfinite


class ProgressEstimator:
    def __init__(self, *, max_age_ms=3000):
        if type(max_age_ms) is not int or max_age_ms <= 0:
            raise ValueError("Invalid estimate lifetime")
        self.max_age_ms = max_age_ms
        self.reset()

    def reset(self):
        self._at = None

    def confirm(self, *, timestamp_ms, along_m, speed_mps):
        """A matched on-route position: distance along the route and the car's speed."""
        if (type(timestamp_ms) is not int or any(type(v) not in (int, float) or not isfinite(v) or v < 0
                                                  for v in (along_m, speed_mps))):
            raise ValueError("Invalid confirmed progress")
        self._at = (timestamp_ms, float(along_m), float(speed_mps))

    def estimate(self, *, timestamp_ms):
        """(along_m, age_ms) carried forward, or None when there is no fresh confirmation."""
        if self._at is None or type(timestamp_ms) is not int:
            return None
        then, along, speed = self._at
        age = timestamp_ms - then
        if age < 0 or age > self.max_age_ms:
            return None
        return along + speed * age / 1000.0, age

"""Research instruction triggering; not text-to-speech or real device timing."""
from math import isfinite

def instruction_phase(*, distance_m, speed_mps, reliable_fix,
                      on_correct_route, maneuver_verified, observation_age_ms,
                      spoken_before=False, lead_seconds=5.0):
    values=(distance_m,speed_mps,lead_seconds)
    if any(type(x) not in (int,float) or not isfinite(x) for x in values):
        raise ValueError("Invalid timing input")
    if distance_m<0 or speed_mps<0 or not 2<=lead_seconds<=15:
        raise ValueError("Invalid distance/speed/timing")
    if type(observation_age_ms) is not int or observation_age_ms<0:
        raise ValueError("Invalid observation clock")
    if not all(type(v) is bool for v in
               (reliable_fix,on_correct_route,maneuver_verified,spoken_before)):
        raise ValueError("Invalid confidence fields")
    if (not reliable_fix or not on_correct_route or not maneuver_verified
            or observation_age_ms>3000):
        return "WITHHOLD"
    if distance_m<=8:
        return "NOW" if not spoken_before else "ALREADY_GIVEN"
    if speed_mps<.5:
        return "WAIT"
    if distance_m<=max(25.0,speed_mps*lead_seconds):
        return "APPROACH" if not spoken_before else "ALREADY_GIVEN"
    return "WAIT"

"""Research instruction triggering; not text-to-speech or real device timing."""
from math import isfinite

def lead_seconds_for(speed_mps):
    """Announcement lead by speed (owner-approved, 17 Oct 2026): 5 s up to 30 mph, 8 s up to
    50 mph, 12 s faster (motorways), so fast roads are called earlier in metres and seconds."""
    if type(speed_mps) not in (int,float) or not isfinite(speed_mps) or speed_mps<0:
        raise ValueError("Invalid speed")
    return 5.0 if speed_mps<=13.5 else 8.0 if speed_mps<=22.5 else 12.0


def instruction_phase(*, distance_m, speed_mps, reliable_fix,
                      on_correct_route, maneuver_verified, observation_age_ms,
                      spoken_before=False, lead_seconds=5.0, now_given=None):
    """`now_given` (owner-approved, 17 Oct 2026): pass False/True to also get a separate
    "NOW" call close to the turn after the approach call (None: original single call).
    The confidence gates are unchanged: a stale or unsure position still withholds."""
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
    if now_given is not None and type(now_given) is not bool:
        raise ValueError("Invalid now_given")
    if (not reliable_fix or not on_correct_route or not maneuver_verified
            or observation_age_ms>3000):
        return "WITHHOLD"
    if now_given is not None:
        if distance_m<=max(8.0,speed_mps*1.5):
            return "NOW" if not now_given else "ALREADY_GIVEN"
    elif distance_m<=8:
        return "NOW" if not spoken_before else "ALREADY_GIVEN"
    if speed_mps<.5:
        return "WAIT"
    if distance_m<=max(25.0,speed_mps*lead_seconds):
        return "APPROACH" if not spoken_before else "ALREADY_GIVEN"
    return "WAIT"

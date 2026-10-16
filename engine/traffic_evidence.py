"""Fail-closed traffic evidence screen; not a live traffic feed."""
from math import isfinite

def traffic_decision(*,age_seconds,speed_factor,closure_state,
                     verified_closure,legal_detour_available):
    if type(age_seconds) not in (int,float) or not isfinite(age_seconds) or age_seconds<0:
        raise ValueError("Invalid traffic timestamp")
    if type(speed_factor) not in (int,float) or not isfinite(speed_factor) or not 0<speed_factor<=2:
        raise ValueError("Invalid speed observation")
    if closure_state not in ("OPEN","CLOSED","UNKNOWN"):
        raise ValueError("Invalid closure observation")
    if type(verified_closure) is not bool or type(legal_detour_available) is not bool:
        raise ValueError("Invalid verified route evidence")
    if age_seconds>300:
        return {"status":"STALE","use_traffic_speed":False,"propose_reroute":False}
    if closure_state=="UNKNOWN":
        return {"status":"UNKNOWN","use_traffic_speed":False,"propose_reroute":False}
    if closure_state=="CLOSED":
        if not verified_closure:
            return {"status":"UNVERIFIED_CLOSURE","use_traffic_speed":False,"propose_reroute":False}
        return {"status":"VERIFIED_CLOSURE","use_traffic_speed":False,
                "propose_reroute":legal_detour_available}
    return {"status":"SOURCE_CURRENT","use_traffic_speed":True,
            "propose_reroute":False,"speed_factor":float(speed_factor)}

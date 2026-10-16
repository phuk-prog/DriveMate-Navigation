"""Refuse unfair route calculation time rankings.

Existing measured DMN in-process versus external HTTP are NOT comparable.
These gates are independent of route validity and road/legal accuracy.
"""
from math import isfinite
from statistics import median

KEYS=("worker","interface","boundary","temperature","map_sha","profile_sha","cases")
def compare_timing(runs):
    if not isinstance(runs,(list,tuple)) or len(runs)<2:
        return {"status":"NOT_COMPARABLE","reason":"Two real engines required","ranking":[]}
    seen=set()
    comparability=set()
    values=[]
    for item in runs:
        if not isinstance(item,dict) or any(k not in item for k in KEYS+("engine","milliseconds","valid_routes")):
            return {"status":"NOT_COMPARABLE","reason":"Missing provenance","ranking":[]}
        name=item["engine"]
        if name in seen:return {"status":"NOT_COMPARABLE","reason":"Duplicate engine","ranking":[]}
        seen.add(name)
        scope=tuple(tuple(item[k]) if k=="cases" else item[k] for k in KEYS)
        comparability.add(scope)
        samples=item["milliseconds"]
        if not isinstance(samples,list) or len(samples)<5 or item["valid_routes"]!=len(samples):
            return {"status":"NOT_COMPARABLE","reason":"Missing valid route samples","ranking":[]}
        if any(type(v) not in (int,float) or not isfinite(v) or v<0 for v in samples):
            return {"status":"NOT_COMPARABLE","reason":"Invalid timing","ranking":[]}
        values.append({"engine":name,"median_ms":median(samples),"sample_count":len(samples)})
    if len(comparability)!=1:
        return {"status":"NOT_COMPARABLE","reason":"Different host, API or case/time scope","ranking":[]}
    values.sort(key=lambda x:(x["median_ms"],x["engine"]))
    last=None
    for i,item in enumerate(values,1):
        item["rank"]=i if last is None or item["median_ms"]!=last[0] else last[1]
        last=(item["median_ms"],item["rank"])
    return {"status":"TIMING_ONLY","ranking":values,
            "note":"No route safety or independent road-law conclusion"}

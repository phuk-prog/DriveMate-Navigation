"""Parse public OSM lane movement tags without inventing physical lane truth."""
from dataclasses import dataclass

TOKENS=frozenset(("left","slight_left","sharp_left","through","right",
                  "slight_right","sharp_right","reverse","merge_to_left",
                  "merge_to_right","none"))

@dataclass(frozen=True)
class LaneMovements:
    status: str
    lanes: tuple[frozenset[str],...]
    reason: str
    source: str

def parse_turn_lanes(tags: dict[str,str], *, direction: str="forward") -> LaneMovements:
    if direction not in ("forward","backward"):
        raise ValueError("Invalid travel direction")
    if not isinstance(tags,dict) or not all(isinstance(k,str) and isinstance(v,str)
                                             for k,v in tags.items()):
        raise ValueError("Invalid OSM lane source")
    if any(k.startswith("turn:lanes") and "conditional" in k for k in tags):
        return LaneMovements("UNKNOWN",(),"Time-dependent turn lanes need independent oracle","")
    key="turn:lanes:"+direction
    if key in tags:
        raw=tags[key]
    elif direction=="forward" and tags.get("oneway") in ("yes","1","true") and "turn:lanes" in tags:
        key="turn:lanes"
        raw=tags[key]
    else:
        return LaneMovements("UNKNOWN",(),"Directional turn markings unavailable",key)
    if not raw.strip():
        return LaneMovements("UNKNOWN",(),"Empty turn lane tag",key)
    choices=raw.split("|")
    if not 1<=len(choices)<=20:
        return LaneMovements("UNKNOWN",(),"Invalid lane count",key)
    lanes=[]
    for value in choices:
        tokens=[t.strip().lower() for t in value.split(";")]
        if any(t not in TOKENS for t in tokens) or ("none" in tokens and len(tokens)>1):
            return LaneMovements("UNKNOWN",(),"Unrecognized or contradictory lane turns",key)
        lanes.append(frozenset(t for t in tokens if t!="none"))
    declared=tags.get("lanes:"+direction)
    if declared is None and direction=="forward" and tags.get("oneway") in ("yes","1","true"):
        declared=tags.get("lanes")
    if declared is not None and (not declared.isdigit() or int(declared)!=len(lanes)):
        return LaneMovements("UNKNOWN",(),"Turn and count tags disagree",key)
    return LaneMovements("MAPPED",tuple(lanes),"OSM mapped movements only, not verified paint",key)

def mapped_lanes_for(evidence: LaneMovements,movement: str) -> tuple[int,...]:
    if movement not in TOKENS or movement=="none":
        raise ValueError("Unsupported movement")
    if evidence.status!="MAPPED":
        return ()
    return tuple(i+1 for i,entry in enumerate(evidence.lanes) if movement in entry)

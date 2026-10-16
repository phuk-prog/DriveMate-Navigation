"""Read explicit speed limits without inventing UK law from road type."""
from dataclasses import dataclass
import re

EXACT=re.compile(r"^([0-9]{1,3})(?:\s+(mph|km/h|kph))?$",re.I)

@dataclass(frozen=True)
class SpeedEvidence:
    status: str
    kph: float|None
    reason: str

def speed_limit_from_tags(tags:dict[str,str], *,direction="forward")->SpeedEvidence:
    if direction not in ("forward","backward") or not isinstance(tags,dict):
        raise ValueError("Invalid speed source/direction")
    if not all(isinstance(k,str) and isinstance(v,str) for k,v in tags.items()):
        raise ValueError("Invalid OSM speed tags")
    if any(k.startswith("maxspeed") and "conditional" in k for k in tags):
        return SpeedEvidence("UNKNOWN",None,"Conditional speed regulations unverified")
    tag=tags.get("maxspeed:"+direction,tags.get("maxspeed"))
    if tag is None:
        return SpeedEvidence("UNKNOWN",None,"No mapped speed limit")
    m=EXACT.fullmatch(tag.strip())
    if m is None:
        return SpeedEvidence("UNKNOWN",None,"National, variable or unsupported designation")
    value=int(m.group(1))
    if not 5<=value<=150:
        return SpeedEvidence("UNKNOWN",None,"Unsupported speed value")
    unit=(m.group(2) or "km/h").lower()
    return SpeedEvidence("MAPPED_ONLY",round(value*1.609344 if unit=="mph" else float(value),4),
                         "Raw map source, not independently confirmed legal limit")

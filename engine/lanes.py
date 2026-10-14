"""Original bounded static lane evidence; markings never grant road permissions."""
from dataclasses import dataclass
import re
TURNS=frozenset({'left','slight_left','sharp_left','through','right','slight_right','sharp_right','reverse','merge_to_left','merge_to_right'})
MAX_LANES=32
@dataclass(frozen=True)
class LaneEvidence:
    count: int | None
    indications: tuple
    status: str
    reason: str = ''
@dataclass(frozen=True)
class LaneConnection:
    from_road: str
    to_road: str
    links: tuple
    status: str
    reason: str = ''

def _count(raw):
    if raw is None:return None
    if not re.fullmatch(r'[0-9]{1,2}',raw) or not 1<=int(raw)<=MAX_LANES:raise ValueError('Unsupported lane count')
    return int(raw)

def parse_lane_evidence(tags,direction,oneway):
    suffix='forward' if direction=='f' else 'backward'
    if direction not in ('f','r'):raise ValueError('Unknown lane direction')
    if not any('lanes' in k for k in tags):return LaneEvidence(None,(),'missing')
    if any('lanes' in k and (k.endswith(':conditional') or k.startswith(('bus:','psv:','bicycle:','access:','motorcar:','motor_vehicle:','vehicle:','change:'))) for k in tags):
        return LaneEvidence(None,(),'unverified','Conditional/vehicle/lane-change semantics not evaluated')
    key='turn:lanes:'+suffix
    raw=tags.get(key,tags.get('turn:lanes') if oneway else None)
    count_raw=tags.get('lanes:'+suffix,tags.get('lanes') if oneway else None)
    if direction=='r' and oneway and key not in tags and 'turn:lanes' in tags:
        return LaneEvidence(None,(),'unverified','Reverse oneway needs an explicit backward marking key')
    try:
        count=_count(count_raw)
        if raw is None:
            if not oneway and ('turn:lanes' in tags or 'lanes' in tags) and count is None:
                return LaneEvidence(None,(),'unverified','No directional lane split')
            return LaneEvidence(count,(),'count_only' if count else 'missing')
        if len(raw)>2048:raise ValueError('Lane hint exceeds prototype bound')
        marks=tuple(frozenset(v.strip() for v in cell.split(';')) for cell in raw.split('|'))
        if not 1<=len(marks)<=MAX_LANES or any(not m or not m<=TURNS for m in marks):raise ValueError('Incomplete/unsupported lane marking')
        if count is not None and count!=len(marks):raise ValueError('Lane count/marking mismatch')
        return LaneEvidence(count or len(marks),marks,'supported')
    except ValueError as e:return LaneEvidence(None,(),'unverified',str(e))

def parse_connectivity(raw,from_count,to_count):
    if any(not isinstance(n,int) or isinstance(n,bool) or not 1<=n<=MAX_LANES for n in (from_count,to_count)):raise ValueError('Directional lane bounds unknown')
    if not raw or len(raw)>2048:raise ValueError('Connectivity exceeds prototype bound')
    links=[];seen=set();pairs=set()
    for statement in raw.split('|'):
        parts=statement.split(':')
        if len(parts)!=2 or not parts[0].isdigit():raise ValueError('Unsupported connectivity grammar')
        a=int(parts[0])
        if a in seen or not 1<=a<=from_count:raise ValueError('Invalid/duplicate source lane')
        seen.add(a)
        for token in parts[1].split(','):
            m=re.fullmatch(r'(?:([0-9]+)|\(([0-9]+)\))',token)
            if not m:raise ValueError('Unsupported target lane')
            b=int(m[1] or m[2])
            if not 1<=b<=to_count:raise ValueError('Target lane outside declared bounds')
            link=(a,b,m[2] is not None)
            if (a,b) in pairs:raise ValueError('Duplicate/conflicting lane connection')
            pairs.add((a,b));links.append(link)
    if len(links)>MAX_LANES*MAX_LANES:raise ValueError('Too many connections')
    return tuple(sorted(links))

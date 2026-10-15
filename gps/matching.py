"""Conservative, original local directed-segment GPS matcher.

No route attraction, inferred lane identity, skipped-road reconstruction or trace
logging. Geometry must be complete, within a 20 km radius and below 80 degrees
latitude. Ambiguous/illegal observations withhold position, never close roads.
All thresholds are prototype policy choices, not calibrated device guarantees.
"""
from dataclasses import dataclass,replace
from datetime import datetime, timezone, timedelta
from math import atan2, cos, degrees, floor, hypot, isfinite, radians
from navigation_core.endpoints import Position
from engine.roundabouts import GuidanceRules

EARTH = 6371008.8
CELL = 50.0

def number(x):
    return not isinstance(x, bool) and isinstance(x, (int, float)) and isfinite(x)

@dataclass(frozen=True)
class Fix:
    latitude: float
    longitude: float
    timestamp: float  # UTC epoch seconds, even for static journeys
    accuracy_m: float
    speed_mps: float | None = None
    bearing_degrees: float | None = None
    bearing_accuracy_degrees: float | None = None

    def __post_init__(self):
        if not all(number(x) for x in (self.latitude, self.longitude, self.timestamp, self.accuracy_m)):
            raise ValueError('Finite fix values required')
        if abs(self.latitude)>90 or abs(self.longitude)>180 or self.accuracy_m<=0:
            raise ValueError('Invalid fix coordinates or accuracy')
        for x in (self.speed_mps,self.bearing_degrees,self.bearing_accuracy_degrees):
            if x is not None and not number(x):raise ValueError('Invalid optional fix value')
        if self.speed_mps is not None and self.speed_mps<0:raise ValueError('Negative speed')
        if self.bearing_degrees is not None and not 0<=self.bearing_degrees<360:raise ValueError('Invalid bearing')
        if self.bearing_accuracy_degrees is not None and not 0<=self.bearing_accuracy_degrees<=180:
            raise ValueError('Invalid bearing uncertainty')
        if self.bearing_accuracy_degrees is not None and self.bearing_degrees is None:
            raise ValueError('Bearing uncertainty requires a bearing')

@dataclass(frozen=True)
class Match:
    status: str
    position: Position | None
    road: str | None
    timestamp: float
    accuracy_m: float
    age_s: float
    speed_mps: float | None
    bearing_accuracy_degrees: float | None
    distance_m: float | None = None
    unverified_access: bool = False
    candidates_examined: int = 0
    junction_held: bool = False  # last verified road temporarily retained near its successor

@dataclass(frozen=True)
class Segment:
    name: str
    a: tuple
    b: tuple
    length: float
    bearing: float

class Matcher:
    """Single-session bounded index; only accepted fixes enter road history."""
    def __init__(self, prepared, *, timezone_name=None):
        self.p=prepared;self.rules=GuidanceRules(prepared,timezone_name)
        if prepared.timed_restrictions and not timezone_name:raise ValueError('Road timezone required')
        points=prepared.coordinates
        if not points or any(e.source not in points or e.target not in points for e in prepared.source_edges.values()):
            raise ValueError('Complete verified geographic geometry required for GPS matching')
        self.anchor=points[next(iter(sorted(points)))];self.scale=cos(radians(self.anchor[0]))
        if any(abs(v[0])>80 for v in points.values()):raise ValueError('Polar geometry unsupported')
        projected={n:self._xy(*v) for n,v in points.items()}
        if any(hypot(*v)>20000 for v in projected.values()):raise ValueError('Matcher region exceeds 20 km radius')
        if len(prepared.source_edges)>30000:raise ValueError('Matcher road limit exceeded')
        self.segments={};self.grid={};entries=0
        for name,e in prepared.source_edges.items():
            a,b=projected[e.source],projected[e.target];dx,dy=b[0]-a[0],b[1]-a[1]
            length=hypot(dx,dy)
            if not 0.01<=length<=2000:raise ValueError('Degenerate or overlong matching segment')
            self.segments[name]=Segment(name,a,b,length,degrees(atan2(dx,dy))%360)
            for cell in self._cells(min(a[0],b[0]),max(a[0],b[0]),min(a[1],b[1]),max(a[1],b[1])):
                entries+=1
                if entries>200000:raise ValueError('Matcher geometry index budget exceeded')
                self.grid.setdefault(cell,[]).append(name)
        self.last=None;self.last_fix=None;self.history=()

    def _xy(self,lat,lon):
        delta=(lon-self.anchor[1]+180)%360-180
        return (EARTH*radians(delta)*self.scale,EARTH*radians(lat-self.anchor[0]))

    @staticmethod
    def _cells(x0,x1,y0,y1):
        for x in range(floor(x0/CELL),floor(x1/CELL)+1):
            for y in range(floor(y0/CELL),floor(y1/CELL)+1):yield x,y

    @staticmethod
    def _project(s,point):
        dx,dy=s.b[0]-s.a[0],s.b[1]-s.a[1]
        q=max(0.,min(1.,((point[0]-s.a[0])*dx+(point[1]-s.a[1])*dy)/(s.length*s.length)))
        return q,hypot(point[0]-s.a[0]-q*dx,point[1]-s.a[1]-q*dy)

    def propose(self,fix,now):
        """Pure preview. Rejected fixes do not consume time or change trusted state."""
        if not isinstance(fix,Fix) or not number(now):raise ValueError('Fix and finite UTC receipt time required')
        age=now-fix.timestamp
        def result(status,position=None,road=None,distance=None,count=0,junction_held=False):
            return Match(status,position,road,fix.timestamp,fix.accuracy_m,age,fix.speed_mps,
                         fix.bearing_accuracy_degrees,distance,
                         bool(road and self.p.source_edges[road].access=='unknown'),count,
                         junction_held)
        if age<0:return result('future_fix')
        if age>3:return result('stale_fix')
        if fix.accuracy_m>35:return result('poor_accuracy')
        if fix.speed_mps is not None and fix.speed_mps>80:return result('impossible_speed')
        if self.last and fix.timestamp<=self.last.timestamp:return result('out_of_order')
        try:at=datetime.fromtimestamp(fix.timestamp,timezone.utc)
        except (OverflowError,OSError,ValueError):return result('unsupported_clock')
        if self.p.validity_window and not self.p.validity_window[0]<=at<self.p.validity_window[1]:
            return result('restriction_window_expired')
        point=self._xy(fix.latitude,fix.longitude)
        if abs(fix.latitude)>80 or hypot(*point)>20000:return result('outside_supported_region')
        heading=None
        if (fix.speed_mps is not None and fix.speed_mps>=2 and fix.bearing_degrees is not None
            and fix.bearing_accuracy_degrees is not None and fix.bearing_accuracy_degrees<=30):
            heading=fix.bearing_degrees
        dt=None;stationary=False
        if self.last:
            dt=fix.timestamp-self.last.timestamp
            if dt>10:return result('reacquisition_required')
            old=self._xy(self.last_fix.latitude,self.last_fix.longitude)
            displacement=hypot(point[0]-old[0],point[1]-old[1])
            stationary=fix.speed_mps is not None and fix.speed_mps<2 and displacement<=fix.accuracy_m+self.last.accuracy_m
            if displacement>80*dt+fix.accuracy_m+self.last.accuracy_m+3:return result('impossible_jump')
            if heading is None and displacement>max(6,fix.accuracy_m+self.last.accuracy_m):
                heading=degrees(atan2(point[0]-old[0],point[1]-old[1]))%360
        radius=min(30,max(8,2*fix.accuracy_m));names=set()
        for cell in self._cells(point[0]-radius,point[0]+radius,point[1]-radius,point[1]+radius):
            names.update(self.grid.get(cell,()))
            if len(names)>512:return result('candidate_budget_exceeded',count=len(names))
        candidates=[];near_geometry=False
        for name in sorted(names):
            s=self.segments[name];q,d=self._project(s,point)
            if d>radius:continue
            near_geometry=True
            if heading is not None and abs((s.bearing-heading+180)%360-180)>60:continue
            candidates.append((d,name,q))
        count=len(names)
        if not candidates:return result('direction_mismatch' if near_geometry else 'off_map',count=count)
        candidates.sort();best=candidates[0];margin=max(3,fix.accuracy_m*.5)
        junction_held=False
        # Include inaccessible/disconnected physical roads in ambiguity assessment.
        # Otherwise legality filtering could snap an illegal observation elsewhere.
        if len(candidates)>1 and candidates[1][0]-best[0]<margin:
            if self.last:
                incumbent=next((c for c in candidates if c[1]==self.last.road),None)
                # Hysteresis only at a shared endpoint, not parallel/crossing roads.
                rivals=[c for c in candidates if c[1]!=self.last.road and c[0]-best[0]<margin]
                previous_edge=self.p.source_edges[self.last.road]
                def shared_endpoint_or_stationary_reverse(c):
                    edge=self.p.source_edges[c[1]]
                    if previous_edge.target==edge.source and c[2]*self.segments[c[1]].length<=margin:return True
                    return stationary and previous_edge.source==edge.target and previous_edge.target==edge.source
                if incumbent and incumbent[0]-best[0]<margin and all(shared_endpoint_or_stationary_reverse(c) for c in rivals):
                    # A nearby successor is physically plausible but its
                    # entry is not yet measured with enough separation.
                    # Keep the trusted last road without pretending that an
                    # exact junction crossing or lane position was observed.
                    junction_held=any(c[1]!=self.last.road for c in rivals)
                    best=incumbent
                else:return result('ambiguous',count=count)
            else:return result('ambiguous',count=count)
        d,name,q=best;position=self.p.position(name,round(q*1000000))
        if self.p.source_edges[name].access=='prohibited':return result('prohibited_road',count=count)
        if self.last:
            oldname=self.last.road;oldpos=self.last.position
            if name==oldname:
                backwards=(oldpos.fraction-position.fraction)*self.segments[name].length/1000000
                # With a near-zero measured speed, an apparent small movement
                # entirely inside both fixes' uncertainty must not move the
                # trusted progress marker. Otherwise repeatable along-road
                # GPS jitter can trigger early instructions while stopped.
                # Apply only to the *same* road; this never grants a turn or
                # attaches to a different physical road. Genuine nonzero
                # speed continues through the normal progress path.
                shift=abs(backwards)
                stopped_within_uncertainty=(stationary and fix.speed_mps is not None
                    and fix.speed_mps<=0.5
                    and shift<=fix.accuracy_m+self.last.accuracy_m)
                if stopped_within_uncertainty:
                    position=oldpos
                else:
                    if backwards>max(3,fix.accuracy_m):return result('backwards_progress',count=count)
                    if backwards>0:position=Position(position.edge,oldpos.fraction)
                path=abs(position.fraction-oldpos.fraction)*self.segments[name].length/1000000
            else:
                if self.p.source_edges[oldname].target!=self.p.source_edges[name].source:
                    return result('discontinuous',count=count)
                hist=(self.history+(oldname,))[-self.rules.memory:]
                start=datetime.fromtimestamp(self.last.timestamp,timezone.utc)
                # Actual crossing time is unknown: enforce every minute boundary
                # in this <=10-second interval, plus both endpoints.
                clocks=[start,at];boundary=start.replace(second=0,microsecond=0)+timedelta(minutes=1)
                if boundary<at:clocks.append(boundary)
                if any(not self.rules.legal(hist,name,t) for t in clocks):return result('prohibited_turn',count=count)
                path=((1000000-oldpos.fraction)*self.segments[oldname].length+
                      position.fraction*self.segments[name].length)/1000000
            if path>80*dt+fix.accuracy_m+self.last.accuracy_m+3:return result('impossible_path',count=count)
        return result('matched',position,name,d,count,junction_held)

    def _commit(self,fix,match):
        if match.status!='matched':return
        if self.last and self.last.road!=match.road:
            self.history=(self.history+(self.last.road,))[-self.rules.memory:]
        self.last=match;self.last_fix=fix

    def observe(self,fix,now):
        match=self.propose(fix,now);self._commit(fix,match);return match

@dataclass(frozen=True)
class GpsUpdate:
    match: Match
    trusted_snapshot: object
    guidance_available: bool

class GpsJourney:
    """Atomic adapter. Rejections retain snapshot but suppress current guidance."""
    def __init__(self,prepared,destination_road,fraction,*,timezone_name=None):
        self.matcher=Matcher(prepared,timezone_name=timezone_name)
        self.journey=prepared.journey(destination_road,fraction,timezone_name=timezone_name)
        self.timed=bool(prepared.timed_restrictions or prepared.validity_window)
        self.destination=prepared.position(destination_road,fraction)
        self.update=None

    def observe(self,fix,now):
        m=self.matcher.propose(fix,now)
        # Avoid reporting arrival from an uncertainty interval straddling the
        # target. Keep the previous trusted snapshot until clearer evidence.
        if m.status=='matched' and m.position.edge==self.destination.edge:
            delta=(m.position.fraction-self.destination.fraction)*self.matcher.segments[m.road].length/1000000
            if abs(delta)<=fix.accuracy_m:
                m=replace(m,status='destination_uncertain',position=None,road=None,unverified_access=False)
        if self.journey.snapshot is not None and self.journey.snapshot.status=='arrived':
            m=replace(m,status='journey_complete',position=None,road=None,unverified_access=False)
        if m.status=='matched':
            clock=datetime.fromtimestamp(fix.timestamp,timezone.utc) if self.timed else fix.timestamp
            if self.journey.snapshot is None:s=self.journey.start(m.position,clock)
            else:s=self.journey.observe(m.position,clock)
            self.matcher._commit(fix,m)
        else:s=self.journey.snapshot
        self.update=GpsUpdate(m,s,m.status=='matched' and not m.junction_held
                             and s is not None and s.status=='navigating')
        return self.update

    def guidance_available(self,now):
        if not number(now):raise ValueError('Finite UTC guidance time required')
        return bool(self.update and self.update.guidance_available and 0<=now-self.update.match.timestamp<=3)

    def junctions(self,now):
        return self.journey.junctions() if self.guidance_available(now) else ()

    def roundabouts(self,now):
        return self.journey.roundabouts() if self.guidance_available(now) else ()

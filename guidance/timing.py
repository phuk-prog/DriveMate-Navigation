"""Bounded, original instruction events over consensus GPS navigation.

SI distances internally; one UK formatter for displayed and queued speech text.
No audio/network calls, inferred lane identity, late speech catch-up or persisted
GPS logs. Timing thresholds are uncalibrated research policy, not road readiness.
"""
from dataclasses import dataclass
from math import floor
import json,re
from gps.matching import number

PHASES=('prepare','approach','now')
YARD=.9144
MILE=1609.344

def uk_distance(metres):
    if not number(metres) or not 0<=metres<=1000000:raise ValueError('Bounded nonnegative distance required')
    if metres==0:return '0 yards'
    if metres>=MILE:
        tenths=floor(metres/MILE*10+.5)
        text=f'{tenths//10}' if tenths%10==0 else f'{tenths/10:.1f}'
        return text+(' mile' if tenths==10 else ' miles')
    yards=metres/YARD
    step=5 if yards<100 else 10 if yards<1000 else 50
    rounded=max(5,floor(yards/step+.5)*step)
    return f'{rounded} yards'

def phase_for(distance,speed):
    if not number(distance) or not 0<=distance<=1000000:raise ValueError('Bounded nonnegative distance required')
    if speed is not None and (not number(speed) or not 0<=speed<=80):raise ValueError('Bounded speed required')
    if speed is None or speed<2:return 'prepare' if distance<=100 else None
    if distance<=max(12,min(100,3*speed)):return 'now'
    if distance<=max(35,min(300,8*speed)):return 'approach'
    if distance<=max(100,min(800,20*speed)):return 'prepare'
    return None

VERBS={'left':'Turn left','right':'Turn right','slight_left':'Bear left','slight_right':'Bear right',
       'sharp_left':'Turn sharply left','sharp_right':'Turn sharply right','through':'Continue straight',
       'follow_road_left':'Follow the road to the left','follow_road_right':'Follow the road to the right',
       'follow_road_slight_left':'Follow the road to the left','follow_road_slight_right':'Follow the road to the right',
       'follow_road_sharp_left':'Follow the road sharply to the left','follow_road_sharp_right':'Follow the road sharply to the right'}

@dataclass(frozen=True)
class Target:
    kind: str
    approach: str
    departure: str
    distance_m: float
    action: str | None
    exit_number: int | None = None
    indicated_lanes: tuple = ()

    @property
    def signature(self):
        return (self.kind,self.approach,self.departure,self.action,self.exit_number,self.indicated_lanes)

@dataclass(frozen=True)
class Instruction:
    target: Target
    phase: str | None
    text: str
    next_target: Target | None = None

@dataclass(frozen=True)
class SpeechEvent:
    event_id: str
    phase: str
    text: str
    created_at: float
    expires_at: float
    target_signature: str

@dataclass(frozen=True)
class Frame:
    status: str
    instruction: Instruction | None
    pending: SpeechEvent | None

class Planner:
    def __init__(self,source):
        self.source=source;self.p=source.p;self.cache=None

    def targets(self,now):
        s=self.source.snapshot
        if not self.source.guidance_available(now):
            # Shared-node hysteresis preserves the last confirmed road but
            # must not sound a speculative turn. Keep the explicit junction
            # uncertainty status required by the instruction contract.
            update=self.source.update
            if (update is not None and update.match is not None and
                    update.match.junction_held):
                return 'junction_position_uncertain',()
            return 'guidance_unavailable',()
        if self.cache is not None and self.cache[0] is s:return self.cache[1:]
        sessions=self.source.sessions
        layouts=tuple(x._roundabout_progress.remaining_path(x._session.snapshot)[0] for x in sessions)
        if not layouts or any(x!=layouts[0] for x in layouts[1:]):return 'history_uncertain',()
        roads=layouts[0]
        if len(roads)>512:return 'instruction_route_limit',()
        current=self.p.edge_names[s.position.edge]
        if not roads or roads[0]!=current:return 'route_position_mismatch',()
        distance=0.;endpoints=[]
        for i,name in enumerate(roads):
            if name not in self.source.matcher.segments:return 'geometry_unavailable',()
            length=self.source.matcher.segments[name].length
            fraction=1-s.position.fraction/1000000 if i==0 else 1
            distance+=length*fraction;endpoints.append(distance)
        # Evaluate each variant's guidance directly; an empty consensus return
        # must not be mistaken for no manoeuvre, allowing a later turn to speak.
        junctions=tuple(x.junctions() for x in sessions)
        if any(x!=junctions[0] for x in junctions[1:]):return 'instruction_disagreement',()
        rings=self.p.roundabout_catalog.by_road;targets=[]
        guides=tuple(x.roundabouts() for x in sessions)
        shared=guides[0] if all(x==guides[0] for x in guides[1:]) else ()
        guide_index={(g.entry_road,g.ring_roads,g.exit_road):g for g in shared}
        guide_junction={(g.approach,g.departure):g for g in junctions[0]}
        for i,(a,b) in enumerate(zip(roads,roads[1:])):
            previous,chosen=self.p.source_edges[a],self.p.source_edges[b]
            if a in rings or b in rings:continue
            g=guide_junction.get((a,b))
            if g is None:continue
            outgoing=self.p.roundabout_catalog.outgoing[previous.target]
            branches=[e for e in outgoing if e.target!=previous.source]
            if g.manoeuvre=='through' and len(branches)<=1:continue
            action=VERBS.get(g.manoeuvre)
            if g.manoeuvre=='reverse' and chosen.target==previous.source:action='Make a U-turn'
            targets.append(Target('junction',a,b,endpoints[i],action,None,g.candidate_lanes))
        i=0
        while i<len(roads):
            if roads[i] not in rings:i+=1;continue
            first=i;ring=rings[roads[i]]
            while i<len(roads) and roads[i] in ring.roads:i+=1
            circle=tuple(roads[first:i]);exitroad=roads[i] if i<len(roads) else None
            entry=roads[first-1] if first else None
            g=guide_index.get((entry,circle,exitroad))
            # Live guidance retains the original observed entry while inside;
            # its current partial ring path has no entry in this layout.
            if first==0:
                g=next((x for x in shared if x.ring_roads==circle and x.exit_road==exitroad),None)
            number=g.exit_number if g and g.status=='numbered' else None
            if first:
                action=('At the roundabout, take exit '+str(number)) if number is not None else 'Enter the roundabout'
                targets.append(Target('roundabout_entry',entry,circle[0],endpoints[first-1],action if ring.simple else None,number))
            elif exitroad is not None:
                action=('Take exit '+str(number)+' from the roundabout') if number is not None else 'Leave the roundabout'
                targets.append(Target('roundabout_exit',circle[-1],exitroad,endpoints[i-1],action if ring.simple else None,number))
        targets.sort(key=lambda x:x.distance_m)
        result=('ready',tuple(targets));self.cache=(s,*result)
        return result

class InstructionScheduler:
    """Peek/ack events: stale or changed events cannot be acknowledged as current.

    Bounded delivered-stage state can be checkpointed by the caller. No queued
    event is restored. Checkpoints belong to one trip/session key, not a GPS log.
    """
    def __init__(self,source,session_key,*,checkpoint=None):
        if not isinstance(session_key,str) or re.fullmatch(r'[A-Za-z0-9_-]{1,80}',session_key) is None:
            raise ValueError('Bounded session key required')
        self.source=source;self.planner=Planner(source);self.session_key=session_key
        self.active=None;self.delivered=-1;self.seq=0;self.queue=None;self.last_now=None;self.arrival_delivered=False;self.observed_road=None
        if checkpoint is not None:
            if not isinstance(checkpoint,dict) or set(checkpoint)!={'schema','session_key','active','delivered','seq','arrival_delivered','observed_road'}:
                raise ValueError('Invalid checkpoint fields')
            if type(checkpoint['schema']) is not int or checkpoint['schema']!=1 or checkpoint['session_key']!=session_key:raise ValueError('Checkpoint belongs to another schema/trip')
            active=checkpoint['active'];delivered=checkpoint['delivered'];seq=checkpoint['seq']
            if active is not None and (not isinstance(active,str) or len(active)>4096):raise ValueError('Invalid active target')
            if active is not None:
                try:value=json.loads(active)
                except (ValueError,TypeError):raise ValueError('Invalid active target') from None
                if (not isinstance(value,list) or len(value)!=6 or value[0] not in ('junction','roundabout_entry','roundabout_exit')
                    or not all(isinstance(x,str) and len(x)<=256 for x in value[1:3])
                    or value[3] is not None and (not isinstance(value[3],str) or len(value[3])>256)
                    or value[4] is not None and (type(value[4]) is not int or not 1<=value[4]<=100000)
                    or not isinstance(value[5],list) or len(value[5])>32 or any(type(x) is not int or not 1<=x<=32 for x in value[5])):
                    raise ValueError('Invalid active target')
            if not isinstance(delivered,int) or isinstance(delivered,bool) or not -1<=delivered<=2:raise ValueError('Invalid delivered stage')
            if not isinstance(seq,int) or isinstance(seq,bool) or not 0<=seq<=2**53-1:raise ValueError('Invalid sequence')
            if not isinstance(checkpoint['arrival_delivered'],bool):raise ValueError('Invalid arrival state')
            if checkpoint['observed_road'] is not None and (not isinstance(checkpoint['observed_road'],str) or len(checkpoint['observed_road'])>256):raise ValueError('Invalid observed road')
            self.active=active;self.delivered=delivered;self.seq=seq;self.arrival_delivered=checkpoint['arrival_delivered']
            self.observed_road=checkpoint['observed_road']

    def checkpoint(self):
        return {'schema':1,'session_key':self.session_key,'active':self.active,'delivered':self.delivered,
                'seq':self.seq,'arrival_delivered':self.arrival_delivered,'observed_road':self.observed_road}

    def _new_event(self,phase,text,now,expires,signature):
        if self.seq>=2**53-1:raise ValueError('Instruction sequence exhausted')
        self.seq+=1
        self.queue=SpeechEvent(self.session_key+'_'+str(self.seq),phase,text,now,expires,signature)
        return self.queue

    def poll(self,now):
        if not number(now):raise ValueError('Finite UTC instruction time required')
        if self.last_now is not None and now<self.last_now:
            self.queue=None;return Frame('clock_out_of_order',None,None)
        self.last_now=now
        last=self.source.matcher.last;s=self.source.snapshot
        if s is not None and s.status=='arrived' and last is not None and 0<=now-last.timestamp<=3:
            self.active=None;self.delivered=-1
            road=self.source.p.edge_names[s.position.edge]
            instruction=Instruction(Target('arrival',road,'',0,'You have arrived'),'arrival','You have arrived')
            if self.arrival_delivered:return Frame('arrived',instruction,None)
            if self.queue is None or self.queue.phase!='arrival':self._new_event('arrival','You have arrived',now,last.timestamp+3,'arrival')
            return Frame('arrived',instruction,self.queue)
        status,targets=self.planner.targets(now)
        if status!='ready':
            self.queue=None;return Frame(status,None,None)
        road=self.source.p.edge_names[s.position.edge]
        if self.active is not None and road!=self.observed_road and self.observed_road is not None:
            old_signature=json.loads(self.active)
            if len(old_signature)>1 and old_signature[1]==self.observed_road:
                self.active=None;self.delivered=-1;self.queue=None
        self.observed_road=road
        if not targets:
            self.active=None;self.delivered=-1;self.queue=None;return Frame('cruising',None,None)
        primary=targets[0]
        if primary.action is None:
            self.queue=None;return Frame('manoeuvre_unverified',None,None)
        speed=last.speed_mps;age=now-last.timestamp
        uncertainty=last.accuracy_m+(speed if speed is not None else 80)*age
        if primary.distance_m<=uncertainty:
            self.queue=None;return Frame('junction_position_uncertain',None,None)
        phase=phase_for(primary.distance_m,speed)
        secondary=None
        if len(targets)>1 and targets[1].action is not None and 0<targets[1].distance_m-primary.distance_m<=max(35,(speed or 0)*6):
            secondary=targets[1]
        signature=json.dumps(primary.signature,separators=(',',':'))
        if self.active!=signature:self.active=signature;self.delivered=-1;self.queue=None
        text=primary.action if phase=='now' else 'In '+uk_distance(primary.distance_m)+', '+primary.action[0].lower()+primary.action[1:]
        linked=secondary if phase in ('prepare','approach') else None
        if linked:text+='; then '+linked.action[0].lower()+linked.action[1:]
        instruction=Instruction(primary,phase,text,linked)
        rank=PHASES.index(phase) if phase else -1
        if phase is None or rank<=self.delivered:
            self.queue=None;return Frame('ready',instruction,None)
        # Unknown/stationary speed supports distant preparation only. Moving
        # speech must finish before the lower-bound arrival at this junction.
        duration=2+(1.5 if linked else 0)
        effective_speed=80 if speed is None else speed if speed>=2 else None
        eta=(primary.distance_m-uncertainty)/effective_speed if effective_speed is not None else None
        if eta is not None and eta<duration:
            self.queue=None;return Frame('too_late_for_speech',instruction,None)
        expires=min(last.timestamp+3,now+(eta-duration if eta is not None else 3))
        if self.queue is not None and (self.queue.target_signature!=signature or self.queue.phase!=phase or self.queue.text!=text or now>self.queue.expires_at):
            self.queue=None
        if self.queue is None:self._new_event(phase,text,now,expires,signature)
        return Frame('ready',instruction,self.queue)

    def acknowledge(self,event_id,now):
        if not isinstance(event_id,str):raise ValueError('Event identifier required')
        frame=self.poll(now)
        event=frame.pending
        if event is None or event.event_id!=event_id or now>event.expires_at:return False
        if event.phase=='arrival':self.arrival_delivered=True
        else:self.delivered=max(self.delivered,PHASES.index(event.phase))
        self.queue=None;return True

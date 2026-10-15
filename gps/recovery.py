"""Original bounded GPS loss/recovery with explicit historical uncertainty.

Unobserved paths are possibilities, never an actual-traversal ledger. Recovery
uses directed physical reachability, then retains every bounded inbound suffix.
Future guidance must agree across all suffixes; no assumed legal past can erase a
restriction. Missing GPS does not close any map road. No trace is persisted.
"""
from copy import copy,deepcopy
from dataclasses import dataclass,replace
from datetime import datetime,timezone
from heapq import heappop,heappush
from itertools import count
from math import hypot
from .matching import Matcher,Fix,Match,number
from engine.reconciled import AccessSnapshot
from engine.live_roundabouts import RoundaboutProgress

@dataclass(frozen=True)
class Reachability:
    status: str
    histories: tuple = ()
    expanded: int = 0

def possible_histories(matcher,origin,target,initial_histories,elapsed,*,max_states=4096,max_histories=16):
    """Over-approximate directed physical histories under a motion upper bound.

    Includes paths containing past turn bans. They are NOT permissions or proved
    trips: excluding them as an assumed legal past could clear a future via-road
    restriction. Prohibited-access roads are excluded; one-way topology is used.
    Minimal distance dominates at the same road/history state because this search
    only asks possible physical reachability, not time-dependent route optimality.
    """
    if not number(elapsed) or elapsed<=0 or elapsed>300:return Reachability('recovery_gap_outside_bounds')
    if not isinstance(max_states,int) or isinstance(max_states,bool) or max_states<1:raise ValueError('Positive state budget required')
    if not isinstance(max_histories,int) or isinstance(max_histories,bool) or max_histories<1:raise ValueError('Positive history budget required')
    p=matcher.p;memory=matcher.rules.memory
    oldname=origin.road;name=target.road
    limit=80*elapsed+origin.accuracy_m+target.accuracy_m+3
    q0=origin.position.fraction/1000000;q1=target.position.fraction/1000000
    histories=set();expanded=0
    if oldname==name and q1>=q0 and (q1-q0)*matcher.segments[name].length<=limit:
        histories.update(tuple(h[-memory:]) for h in initial_histories)
    queue=[];best={};serial=count();exhausted=False
    outgoing=p.roundabout_catalog.outgoing
    def offer(road,hist,distance):
        nonlocal exhausted
        if distance>limit:return
        state=(road,tuple(hist[-memory:]))
        if distance<best.get(state,float('inf')):
            if (state not in best and len(best)>=max_states) or len(queue)>=max_states:
                exhausted=True;return
            best[state]=distance;heappush(queue,(distance,next(serial),state))
    for h in initial_histories:
        hist=(tuple(h)+(oldname,))[-memory:]
        for e in outgoing[p.source_edges[oldname].target]:
            if e.access!='prohibited':offer(e.edge_id,hist,(1-q0)*matcher.segments[oldname].length)
            if exhausted:return Reachability('recovery_search_incomplete',expanded=expanded)
    while queue:
        distance,_,state=heappop(queue)
        if best[state]!=distance:continue
        expanded+=1
        if expanded>max_states:return Reachability('recovery_search_incomplete',expanded=expanded)
        road,hist=state
        if road==name and distance+q1*matcher.segments[name].length<=limit:
            histories.add(hist)
            if len(histories)>max_histories:return Reachability('recovery_history_incomplete',expanded=expanded)
        enddistance=distance+matcher.segments[road].length
        after=(hist+(road,))[-memory:]
        for e in outgoing[p.source_edges[road].target]:
            if e.access!='prohibited':offer(e.edge_id,after,enddistance)
            if exhausted:return Reachability('recovery_search_incomplete',expanded=expanded)
    if len(histories)>max_histories:return Reachability('recovery_history_incomplete',expanded=expanded)
    return Reachability('reachable' if histories else 'recovery_unreachable',tuple(sorted(histories)),expanded)

@dataclass(frozen=True)
class RecoveryUpdate:
    status: str
    match: Match | None
    trusted_snapshot: object
    guidance_available: bool
    confirmations: int
    possible_history_count: int
    history_inferred: bool

class RecoveringGpsJourney:
    """Three-fix reacquisition and an all-history consensus journey adapter.

    Shared spatial index, bounded pending fixes and at most 16 journey variants.
    A snapshot with history_uncertain has a fresh location but no safe common plan.
    Call poll(now) during sensor silence; every guidance lookup also checks age.
    """
    def __init__(self,prepared,destination_road,fraction,*,timezone_name=None,max_states=4096,max_histories=16):
        if not isinstance(max_states,int) or isinstance(max_states,bool) or max_states<1:raise ValueError('Positive state budget required')
        if not isinstance(max_histories,int) or isinstance(max_histories,bool) or not 1<=max_histories<=16:raise ValueError('History budget must be 1..16')
        self.p=prepared;self.destination=prepared.position(destination_road,fraction)
        self.destination_road=destination_road;self.fraction=fraction;self.zone=timezone_name
        self.matcher=Matcher(prepared,timezone_name=timezone_name)
        self.max_states=max_states;self.max_histories=max_histories
        self.sessions=();self.histories=((),);self.update=None;self.snapshot=None
        self.mode='acquiring';self.probe=None;self.confirmations=0;self.first_probe_time=None
        self.inferred=False;self.last_receipt=None

    def _reset_probe(self):
        self.probe=None;self.confirmations=0;self.first_probe_time=None

    def _clock(self,t):
        return datetime.fromtimestamp(t,timezone.utc) if self.p.timed_restrictions or self.p.validity_window else t

    def _out(self,status,match=None):
        available=(status in ('tracking','recovered') and self.mode=='tracking'
                   and self.snapshot is not None and self.snapshot.status=='navigating'
                   and not (match is not None and match.junction_held))
        self.update=RecoveryUpdate(status,match,self.snapshot,available,self.confirmations,len(self.sessions),self.inferred)
        return self.update

    def _consensus(self,sessions):
        snaps=tuple(s.snapshot for s in sessions);first=snaps[0]
        if all(s==first for s in snaps[1:]):return first
        # Wrong-turn flags may differ across old possibilities; never publish a
        # guessed violation. Agreement must include actual road plan and status.
        if all((s.position,s.timestamp,s.status,s.roads,s.cost,s.unverified_access_edges)==
               (first.position,first.timestamp,first.status,first.roads,first.cost,first.unverified_access_edges) for s in snaps[1:]):
            return replace(first,wrong_turn=False)
        return AccessSnapshot(first.position,first.timestamp,'history_uncertain',(),None,False,())

    def _destination_uncertain(self,match,fix):
        if match.status=='matched' and match.position.edge==self.destination.edge:
            distance=(match.position.fraction-self.destination.fraction)*self.matcher.segments[match.road].length/1000000
            if abs(distance)<=fix.accuracy_m:
                return replace(match,status='destination_uncertain',position=None,road=None,unverified_access=False)
        return match

    def _new_sessions(self,match,histories):
        sessions=[]
        for history in histories:
            s=self.p.journey(self.destination_road,self.fraction,timezone_name=self.zone)
            inbound=tuple(self.p.edge_ids[n] for n in history)
            snapshot=s.start(match.position,self._clock(match.timestamp),inbound)
            # Restriction histories are possibilities, not observed roundabout
            # entry/exits. Explicitly discard reconstructed historical ordinals.
            s._roundabout_progress=RoundaboutProgress(self.p,s._session)
            s._roundabout_progress.start(s._session.snapshot,())
            sessions.append(s)
        return tuple(sessions)

    def observe(self,fix,now):
        if not isinstance(fix,Fix) or not number(now):raise ValueError('Fix and finite UTC receipt time required')
        if self.last_receipt is not None and now<self.last_receipt:return self._out('receipt_out_of_order')
        self.last_receipt=now
        if self.snapshot is not None and self.snapshot.status=='arrived':return self._out('journey_complete')
        if self.mode=='tracking' and now-self.matcher.last.timestamp>3:
            self.mode='recovering';self._reset_probe()
        if self.mode=='tracking':
            matches=[]
            for hist in self.histories:
                view=copy(self.matcher);view.history=hist
                matches.append(view.propose(fix,now))
            match=self._destination_uncertain(matches[0],fix)
            if any(m.status!='matched' for m in matches):
                match=next(m for m in matches if m.status!='matched')
            if match.status == 'destination_uncertain':
                # A good fix inside the destination accuracy interval is NOT
                # proof of arrival. Keep the previous trusted road/route and
                # matching history intact, withhold guidance for this frame,
                # and allow the next fresh fix to establish a directed
                # crossing. Switching to recovery here used to discard the
                # route and could strand a driver beyond a one-way destination.
                return self._out('destination_uncertain',match)
            if match.status!='matched':
                self.mode='recovering';self._reset_probe();return self._out(match.status,match)
            # Deep-copy only bounded journey state. Prepared immutable graph and
            # indexes remain shared; failures cannot mutate the live session pool.
            sessions=tuple(self._clone_session(s) for s in self.sessions)
            for session in sessions:session.observe(match.position,self._clock(fix.timestamp))
            snapshot=self._consensus(sessions)
            unique={self._variant_key(s):s for s in sessions}
            sessions=tuple(unique.values())
            histories=tuple(tuple(self.p.edge_names[e] for e in s._session._history) for s in sessions)
            self.matcher.history=histories[0];self.matcher._commit(fix,match)
            # _commit advances its own history; replace with the accepted pool's
            # already-advanced suffix to avoid appending the road twice.
            self.matcher.history=histories[0]
            self.sessions=sessions;self.histories=histories;self.snapshot=snapshot
            return self._out('tracking' if snapshot.status!='history_uncertain' else 'history_uncertain',match)
        # A pending streak is disposable evidence, never trusted route progress.
        if self.matcher.last and fix.timestamp<=self.matcher.last.timestamp:
            self._reset_probe();return self._out('out_of_order')
        if self.probe is not None and fix.timestamp-self.probe.last.timestamp>3:self._reset_probe()
        probe=copy(self.matcher) if self.probe is None else copy(self.probe)
        if self.probe is None:probe.last=None;probe.last_fix=None;probe.history=()
        match=self._destination_uncertain(probe.propose(fix,now),fix)
        if match.status=='matched' and fix.accuracy_m>15:
            match=replace(match,status='recovery_accuracy_insufficient',position=None,road=None,unverified_access=False)
        if match.status!='matched':
            self._reset_probe();return self._out(match.status,match)
        probe._commit(fix,match)
        confirmations=self.confirmations+1;first=self.first_probe_time if self.first_probe_time is not None else fix.timestamp
        if confirmations<3 or fix.timestamp-first<2:
            self.probe=probe;self.confirmations=confirmations;self.first_probe_time=first
            return self._out('confirming',replace(match,position=None,road=None,status='confirming'))
        histories=(probe.history,)
        if self.matcher.last:
            old=self.matcher.last;elapsed=fix.timestamp-old.timestamp
            point=self.matcher._xy(fix.latitude,fix.longitude)
            previous=self.matcher._xy(self.matcher.last_fix.latitude,self.matcher.last_fix.longitude)
            if hypot(point[0]-previous[0],point[1]-previous[1])>80*elapsed+old.accuracy_m+fix.accuracy_m+3:
                self._reset_probe();return self._out('recovery_impossible_jump')
            reached=possible_histories(self.matcher,old,match,self.histories,elapsed,
                                       max_states=self.max_states,max_histories=self.max_histories)
            if reached.status!='reachable':
                self._reset_probe();return self._out(reached.status)
            histories=reached.histories
        # Perform all fallible work before replacing any trusted state.
        sessions=self._new_sessions(match,histories);snapshot=self._consensus(sessions)
        recovered=self.matcher.last is not None
        probe.history=histories[0];self.matcher=probe;self.sessions=sessions;self.histories=histories
        self.snapshot=snapshot;self.mode='tracking';self.inferred=recovered
        self._reset_probe()
        return self._out('history_uncertain' if snapshot.status=='history_uncertain' else 'recovered' if recovered else 'tracking',match)

    @staticmethod
    def _variant_key(session):
        context=session._roundabout_progress.context
        ledger=None if context is None else (context.ring,context.entry,tuple(context.opportunities),
                        context.traversed,context.uncertain_time,context.repeated,context.unknown)
        # Equivalent current restriction suffixes can still have different past
        # roundabout exit ledgers. Do not collapse a disputed ordinal into one.
        return tuple(session._session._history),ledger

    @staticmethod
    def _clone_session(session):
        clone=copy(session);clone._session=copy(session._session)
        # Overlay caches and snapshots are immutable query products. Context is
        # the only mutable nested guidance state; keep prepared graph shared.
        tracker=copy(session._roundabout_progress);tracker.session=clone._session
        tracker.context=deepcopy(tracker.context)
        clone._roundabout_progress=tracker
        return clone

    def poll(self,now):
        if not number(now):raise ValueError('Finite UTC receipt time required')
        if self.last_receipt is not None and now<self.last_receipt:return self._out('receipt_out_of_order')
        self.last_receipt=now
        if self.snapshot is not None and self.snapshot.status=='arrived':return self._out('journey_complete')
        if self.matcher.last is None or now-self.matcher.last.timestamp>3:
            self.mode='recovering' if self.matcher.last else 'acquiring'
            if self.probe and now-self.probe.last.timestamp>3:self._reset_probe()
            return self._out('gps_lost')
        return self._out('tracking' if self.mode=='tracking' else 'confirming')

    def guidance_available(self,now):
        if not number(now):raise ValueError('Finite UTC guidance time required')
        return bool(self.update and self.update.guidance_available and self.mode=='tracking' and self.snapshot and self.snapshot.status=='navigating'
                    and self.matcher.last and 0<=now-self.matcher.last.timestamp<=3)

    def junctions(self,now):
        if not self.guidance_available(now):return ()
        variants=tuple(s.junctions() for s in self.sessions)
        return variants[0] if all(v==variants[0] for v in variants[1:]) else ()

    def roundabouts(self,now):
        if not self.guidance_available(now):return ()
        variants=tuple(s.roundabouts() for s in self.sessions)
        return variants[0] if all(v==variants[0] for v in variants[1:]) else ()

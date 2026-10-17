"""Isolated DMN research lifecycle for corroborated rerouting.

Consumes caller-supplied on-route/reliability assessments and monotonic clocks.
It does not assess GPS, compute progress, launch/cancel network work, or emit
active guidance. Cancellation suppresses stale installation; callers still own
physical computation cancellation and Android lifecycle integration.
"""
from dataclasses import dataclass
from math import isfinite
from .routing import Route


@dataclass(frozen=True)
class RerouteRequest:
    request_id: int
    context_revision: int
    observation_timestamp_ms: int
    created_at_ms: int


class ReroutingController:
    def __init__(self, *, minimum_off_route_samples=2, minimum_sample_gap_ms=1000,
                 max_observation_age_ms=10000, cooldown_ms=30000,
                 max_request_age_ms=15000, post_gap_ms=None, post_gap_reliable_samples=3):
        policy={'minimum_off_route_samples':(minimum_off_route_samples,2),
                'minimum_sample_gap_ms':(minimum_sample_gap_ms,1),
                'max_observation_age_ms':(max_observation_age_ms,1),
                'cooldown_ms':(cooldown_ms,0),'max_request_age_ms':(max_request_age_ms,1)}
        for name,(value,minimum) in policy.items():
            if type(value) is not int or value<minimum:raise ValueError('Invalid '+name)
            setattr(self,name,value)
        # After a GPS gap longer than post_gap_ms, that many reliable samples must arrive
        # before off-route evidence counts again (owner-approved, 17 Oct 2026: Run C saw one
        # false reroute right after a blackout). None keeps the original behaviour.
        if post_gap_ms is not None and (type(post_gap_ms) is not int or post_gap_ms<1):
            raise ValueError('Invalid post_gap_ms')
        if type(post_gap_reliable_samples) is not int or post_gap_reliable_samples<1:
            raise ValueError('Invalid post_gap_reliable_samples')
        self.post_gap_ms=post_gap_ms
        self.post_gap_reliable_samples=post_gap_reliable_samples
        self._fresh_needed=0
        self.active=False
        self.installed_route=None
        self.pending_request=None
        self._revision=0
        self._serial=0
        self._last_now=None
        self._last_request_now=None
        self._last_observed_timestamp=None
        self._clear_evidence()

    def _clear_evidence(self):
        self._count=0
        self._last_counted_timestamp=None
        self._latest_off_route_timestamp=None

    def _clock(self,now_ms):
        if type(now_ms) is not int or now_ms<0 or (self._last_now is not None and now_ms<self._last_now):
            raise ValueError('Clock must be nonnegative monotonic milliseconds')
        self._last_now=now_ms

    @staticmethod
    def _validate_route(route):
        if (not isinstance(route,Route) or not isinstance(route.edge_ids,tuple)
                or any(not isinstance(e,str) or not e for e in route.edge_ids)
                or any(type(v) not in (int,float) or not isfinite(v) or v<0
                       for v in (route.length_m,route.estimated_seconds))):
            raise ValueError('Expected a finite nonnegative planner Route')

    def begin(self,route,*,now_ms):
        self._validate_route(route)
        self._clock(now_ms)
        self._revision+=1
        self.active=True
        self.installed_route=route
        self.pending_request=None
        self._last_request_now=None
        self._last_observed_timestamp=None
        self._clear_evidence()

    def stop(self,*,now_ms):
        self._clock(now_ms)
        self._revision+=1
        self.active=False
        self.installed_route=None
        self.pending_request=None
        self._clear_evidence()

    def _expire_request(self,now_ms):
        if self.pending_request is not None and now_ms-self.pending_request.created_at_ms>self.max_request_age_ms:
            self.pending_request=None
            self._clear_evidence()

    def observe(self,*,timestamp_ms,now_ms,reliable,on_route):
        if type(timestamp_ms) is not int or timestamp_ms<0 or type(reliable) is not bool or (on_route is not None and type(on_route) is not bool):
            raise ValueError('Invalid observation assessment')
        self._clock(now_ms)
        self._expire_request(now_ms)
        if not self.active:return None
        if (timestamp_ms>now_ms or now_ms-timestamp_ms>self.max_observation_age_ms
                or (self._last_observed_timestamp is not None and timestamp_ms<=self._last_observed_timestamp)):
            return None
        previous=self._last_observed_timestamp
        self._last_observed_timestamp=timestamp_ms
        if self.post_gap_ms is not None and previous is not None and timestamp_ms-previous>self.post_gap_ms:
            self._fresh_needed=self.post_gap_reliable_samples
            self.pending_request=None
            self._clear_evidence()
        if self._fresh_needed:
            if reliable:
                self._fresh_needed-=1
            return None
        if not reliable or on_route is not False:
            self.pending_request=None
            self._clear_evidence()
            return None
        if self._last_counted_timestamp is not None and now_ms-self._last_counted_timestamp>self.max_observation_age_ms:
            self._count=0
            self._last_counted_timestamp=None
        self._latest_off_route_timestamp=timestamp_ms
        if self.pending_request is not None:return None
        if self._last_counted_timestamp is None or timestamp_ms-self._last_counted_timestamp>=self.minimum_sample_gap_ms:
            self._count=min(self.minimum_off_route_samples,self._count+1)
            self._last_counted_timestamp=timestamp_ms
        if self._count<self.minimum_off_route_samples:return None
        if self._last_request_now is not None and now_ms-self._last_request_now<self.cooldown_ms:return None
        self._serial+=1
        request=RerouteRequest(self._serial,self._revision,timestamp_ms,now_ms)
        self.pending_request=request
        self._last_request_now=now_ms
        return request

    def complete(self,request,route,*,now_ms):
        if route is not None:self._validate_route(route)
        self._clock(now_ms)
        self._expire_request(now_ms)
        if not self.active or self.pending_request is None or request!=self.pending_request:
            return False
        latest=self._latest_off_route_timestamp
        fresh=latest is not None and 0<=now_ms-latest<=self.max_observation_age_ms
        self.pending_request=None
        self._clear_evidence()
        if not fresh or route is None:return False
        self.installed_route=route
        self._revision+=1
        return True

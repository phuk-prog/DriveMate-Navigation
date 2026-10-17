"""Isolated research arrival lifecycle; no GPS/progress or Android integration.

Callers own trustworthy route progress, on-route/reliability assessments and the
route context token. Thresholds are engineering contracts, not GNSS calibration.
"""
from math import asin, cos, isfinite, radians, sin, sqrt


def _number(value):
    return type(value) in (int,float) and isfinite(value)


def _position(value):
    return (isinstance(value,(tuple,list)) and len(value)==2
            and all(_number(v) for v in value)
            and -90<=value[0]<=90 and -180<=value[1]<=180)


def distance_m(a,b):
    """Great-circle distance with longitude wrap and bounded floating error."""
    lat1,lon1=map(radians,a);lat2,lon2=map(radians,b)
    h=sin((lat2-lat1)/2)**2+cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
    return 6371008.8*2*asin(sqrt(max(0,min(1,h))))


class ArrivalController:
    def __init__(self,*,radius_m=20,max_remaining_m=25,max_accuracy_m=15,
                 max_observation_age_ms=10000,minimum_sample_gap_ms=1000):
        for name,value in (('radius_m',radius_m),('max_remaining_m',max_remaining_m),
                           ('max_accuracy_m',max_accuracy_m)):
            if not _number(value) or value<=0:raise ValueError('Invalid '+name)
            setattr(self,name,value)
        for name,value in (('max_observation_age_ms',max_observation_age_ms),
                           ('minimum_sample_gap_ms',minimum_sample_gap_ms)):
            if type(value) is not int or value<=0:raise ValueError('Invalid '+name)
            setattr(self,name,value)
        if minimum_sample_gap_ms>max_observation_age_ms:
            raise ValueError('Corroboration interval exceeds evidence lifetime')
        self._last_now=None
        self._revision=0
        self._active=False
        self._arrived=False
        self._anchor=None
        self._last_timestamp=None

    @property
    def revision(self):return self._revision

    @property
    def arrived(self):return self._arrived

    def _clock(self,now_ms):
        if type(now_ms) is not int or now_ms<0 or (self._last_now is not None and now_ms<self._last_now):
            raise ValueError('Clock must be nonnegative monotonic milliseconds')
        self._last_now=now_ms

    def begin(self,destination,*,route_length_m,now_ms):
        if not _position(destination) or not _number(route_length_m) or route_length_m<0:
            raise ValueError('Invalid destination or route length')
        self._clock(now_ms)
        self._revision+=1
        self._destination=tuple(destination)
        self._route_length_m=route_length_m
        self._began_at=now_ms
        self._active=True
        self._arrived=False
        self._anchor=None
        self._last_timestamp=None
        return self._revision

    def stop(self,*,now_ms):
        self._clock(now_ms)
        self._revision+=1
        self._active=False
        self._arrived=False
        self._anchor=None
        self._last_timestamp=None

    def observe(self,*,context_revision,timestamp_ms,now_ms,position,accuracy_m,
                reliable,on_route,remaining_m):
        self._clock(now_ms)
        if not self._active:return 'INACTIVE'
        if type(context_revision) is not int or context_revision!=self._revision:
            self._anchor=None
            return 'REJECTED'
        if self._arrived:return 'ALREADY_ARRIVED'
        if (type(timestamp_ms) is not int or timestamp_ms<self._began_at
                or timestamp_ms>now_ms or now_ms-timestamp_ms>self.max_observation_age_ms
                or (self._last_timestamp is not None and timestamp_ms<=self._last_timestamp)):
            self._anchor=None
            return 'REJECTED'
        self._last_timestamp=timestamp_ms
        if (not _position(position) or not _number(accuracy_m) or not 0<=accuracy_m<=self.max_accuracy_m
                or reliable is not True or on_route is not True
                or not _number(remaining_m) or not 0<=remaining_m<=min(self.max_remaining_m,self._route_length_m)
                or distance_m(position,self._destination)>self.radius_m):
            self._anchor=None
            return 'WITHHELD'
        if self._anchor is not None and now_ms-self._anchor>self.max_observation_age_ms:
            self._anchor=None
        if self._anchor is None:
            self._anchor=timestamp_ms
            return 'CANDIDATE'
        if timestamp_ms-self._anchor<self.minimum_sample_gap_ms:return 'CANDIDATE'
        self._arrived=True
        self._anchor=None
        return 'ARRIVED'

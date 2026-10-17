"""Actual loopback ROUTE-001 geometry interfaces; no invented responses."""
import json
from math import isfinite
from urllib.parse import urlencode
from urllib.request import Request, ProxyHandler, build_opener
from benchmarks.osrm_live_reference import NoRedirect

OPENER=build_opener(ProxyHandler({}),NoRedirect())


def decode_polyline(shape,precision=6):
    if not isinstance(shape,str) or not 1<=len(shape)<=40000:
        raise ValueError('Invalid encoded shape')
    index=0;lat=lon=0;points=[]
    while index<len(shape):
        values=[]
        for _ in range(2):
            result=shift=0
            while True:
                if index>=len(shape) or shift>35:raise ValueError('Truncated or oversized shape value')
                value=ord(shape[index])-63;index+=1
                if not 0<=value<=63:raise ValueError('Invalid polyline character')
                result|=(value&31)<<shift;shift+=5
                if value<32:break
            values.append(~(result>>1) if result&1 else result>>1)
        lat+=values[0];lon+=values[1]
        points.append([lat/(10**precision),lon/(10**precision)])
        if len(points)>2000:raise ValueError('Too many shape positions')
    return points


def route_request(system,start,end):
    for point in (start,end):
        if len(point)!=2 or any(type(v) not in (int,float) or not isfinite(v) for v in point) or not -90<=point[0]<=90 or not -180<=point[1]<=180:
            raise ValueError('Invalid synthetic endpoint')
    if system=='OSRM':
        a,b=(f'{p[1]:.7f},{p[0]:.7f}' for p in (start,end))
        return Request(f'http://127.0.0.1:5000/route/v1/driving/{a};{b}?overview=full&geometries=geojson&steps=false&alternatives=false')
    if system=='GraphHopper':
        query=urlencode([('point',f'{p[0]:.7f},{p[1]:.7f}') for p in (start,end)]+[('profile','car'),('points_encoded','false'),('calc_points','true'),('instructions','false')])
        return Request('http://127.0.0.1:8989/route?'+query)
    if system=='Valhalla':
        url='http://127.0.0.1:8002/route'
        body={'locations':[{'lat':p[0],'lon':p[1]} for p in (start,end)],'costing':'auto','shape_format':'polyline6','directions_options':{'units':'kilometers'}}
    elif system=='openrouteservice':
        url='http://127.0.0.1:8080/ors/v2/directions/driving-car/geojson'
        body={'coordinates':[[p[1],p[0]] for p in (start,end)],'instructions':False,'preference':'fastest'}
    else:raise ValueError('Unsupported reference')
    return Request(url,json.dumps(body,allow_nan=False).encode(),{'Content-Type':'application/json'},method='POST')


def route_points(system,data):
    if system=='Valhalla':
        legs=data['trip']['legs']
        if len(legs)!=1:raise ValueError('Expected exactly one leg')
        return decode_polyline(legs[0]['shape'])
    if system=='OSRM':
        if data.get('code')!='Ok' or len(data.get('routes',[]))!=1:raise ValueError('No complete OSRM route')
        geometry=data['routes'][0]['geometry']
    elif system=='GraphHopper':
        if len(data.get('paths',[]))!=1:raise ValueError('No single GraphHopper route')
        geometry=data['paths'][0]['points']
    elif system=='openrouteservice':
        if len(data.get('features',[]))!=1:raise ValueError('No single ORS route')
        geometry=data['features'][0]['geometry']
    else:raise ValueError('Unsupported response family')
    if geometry.get('type')!='LineString':raise ValueError('Complete line geometry required')
    return [[p[1],p[0]] for p in geometry['coordinates']]


def run_reference(system):
    if system=='OSRM':
        from benchmarks.osrm_live_reference import wait_for_local_router
        wait_for_local_router()
    elif system=='Valhalla':
        from benchmarks.valhalla_live_reference import wait_for_local_router
        wait_for_local_router()
    elif system=='GraphHopper':
        from benchmarks.graphhopper_live_reference import wait_for_graphhopper
        wait_for_graphhopper()
    elif system=='openrouteservice':
        from benchmarks.ors_snap_reference import wait_for_ors
        wait_for_ors()
    else:raise ValueError('Unknown live reference')
    from benchmarks.routing_trial import load_cases,judge,report
    rows=[]
    for case in load_cases():
        request=route_request(system,case['path'][0],case['path'][-1])
        with OPENER.open(request,timeout=30) as response:raw=response.read(200001)
        if len(raw)>200000:raise ValueError('Oversized live route response')
        rows.append(judge(case,route_points(system,json.loads(raw))))
    return report(system,rows)

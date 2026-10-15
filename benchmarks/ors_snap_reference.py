"""Bounded loopback ORS pointwise snapping; no temporal/direction inference."""
import json
from math import isfinite
from time import monotonic, sleep
from urllib.error import URLError
from urllib.request import Request, ProxyHandler, build_opener

from benchmarks.osrm_live_reference import NoRedirect

URL = 'http://127.0.0.1:8080/ors/v2/snap/driving-car/json'
OPENER = build_opener(ProxyHandler({}), NoRedirect())


def snap_body(fixes):
    if len(fixes) != 4:
        raise ValueError('GPS-001 requires exactly four synthetic observations')
    locations = [[f.longitude, f.latitude] for f in fixes]
    for lon, lat in locations:
        if not (isfinite(lon) and isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError('Invalid observation')
    return json.dumps({'locations': locations, 'radius': 20}, allow_nan=False).encode()


def aligned_points(response):
    locations = response.get('locations')
    if not isinstance(locations, list):
        raise ValueError('Missing ORS locations array')
    if len(locations) != 4:
        return [None] * 4
    points = []
    for entry in locations:
        if entry is None:
            points.append(None)
            continue
        pair = entry.get('location')
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError('Invalid ORS location')
        lon, lat = pair
        if any(type(x) not in (int, float) or not isfinite(x) for x in pair):
            raise ValueError('Invalid ORS coordinates')
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError('ORS coordinates out of bounds')
        points.append((lat, lon))
    return points


def request_snap(body):
    request = Request(URL, body, {'Content-Type': 'application/json'}, method='POST')
    with OPENER.open(request, timeout=20) as response:
        raw = response.read(100001)
    if len(raw) > 100000:
        raise ValueError('ORS response exceeds bound')
    return json.loads(raw)


def wait_for_ors(timeout_s=180):
    deadline = monotonic() + timeout_s
    while monotonic() < deadline:
        try:
            with OPENER.open('http://127.0.0.1:8080/ors/v2/health', timeout=2) as response:
                if json.loads(response.read(4096)).get('status') == 'ready':
                    return
        except (URLError, OSError, ValueError):
            pass
        sleep(1)
    raise TimeoutError('ORS unavailable; not a case failure or pass')

"""openrouteservice 10.1.0 and BRouter 1.7.10 as extra reference engines (owner, 17 Oct 2026).

Both are free, open source and need no registration. Like OSRM, Valhalla and
GraphHopper in TURN-001, each is built from the SAME hashed clip as DMN for every
case, then asked for one car route with its turn instructions. The pinned downloads
and profiles are the ones already used by JUNCTION-001 and ROUTE-001.

Known difference: BRouter takes no start/finish heading, so it may start in the
other direction; the harness then reports OFF_TARGET, never a rule break.

OsmAnd (owner, 17 Oct 2026) is a yardstick only, like every reference engine: its
own map file (OBF) is built from the same clip with OsmAndMapCreator and its Java
router is called through tools/osmand_route/OsmAndRoute.java. It gets the start
direction (its finish-direction option made needless loops in testing, so it is not
used). OsmAnd publishes only nightly builds of the current router; the SHA-256 of
the build used is recorded with every run.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import time
import zipfile
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from benchmarks import turn001_restrictions as t1

NEW = ("openrouteservice", "BRouter", "OsmAnd")
ENGINES = ("OSRM", "GraphHopper", "Valhalla", *NEW)
CACHE = t1.WORK / "engines"
ORS_JAR = ("https://github.com/GIScience/openrouteservice/releases/download/v10.1.0/ors.jar",
           "46b83b353eaf8830a1b53cad91d027e00547cd9a00e86efddd64a45335bfb8e1")
BROUTER_ZIP = ("https://github.com/abrensch/brouter/releases/download/v1.7.10/brouter-1.7.10.zip",
               "023fec3ba997758e8cd7ab9e1bae52e962af3f00b57683e3de86b84ffad01532")
BROUTER_PROFILES = "https://raw.githubusercontent.com/abrensch/brouter/4d2639af77ea5ed9c30d3e400764eb6f9e8522da/misc/profiles2/"
OSMAND_ZIP = "https://download.osmand.net/latest-night-build/OsmAndMapCreator-main.zip"
ORS_PORT, BROUTER_PORT = 8080, 17777
JAVA = os.environ.get("EXTRA_JAVA", "java")  # BRouter: Java 17+
ORS_JAVA = os.environ.get("ORS_JAVA", JAVA)  # openrouteservice 10.1: Java 25


def _download(url: str, sha256: str, path: Path) -> Path:
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != sha256:
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["curl", "-fsSL", "--retry", "2", "--max-time", "300", url, "-o", str(path)], check=True)
    if hashlib.sha256(path.read_bytes()).hexdigest() != sha256:
        raise RuntimeError(f"pinned download changed: {url}")
    return path


def install(engine: str) -> Path:
    """Download and verify the pinned engine once; returns its folder."""
    if engine == "openrouteservice":
        _download(*ORS_JAR, CACHE / "ors" / "ors.jar")
        return CACHE / "ors"
    if engine == "OsmAnd":
        folder = CACHE / "osmand"
        if not (folder / "classes" / "OsmAndRoute.class").exists():
            folder.mkdir(parents=True, exist_ok=True)
            z = folder / "mapcreator.zip"
            subprocess.run(["curl", "-fsSL", "--retry", "2", "--max-time", "900", OSMAND_ZIP, "-o", str(z)], check=True)
            (folder / "build-sha256.txt").write_text(hashlib.sha256(z.read_bytes()).hexdigest() + "\n")
            with zipfile.ZipFile(z) as zf:
                zf.extractall(folder / "mc")
            z.unlink()
            subprocess.run(["javac", "-cp", osmand_classpath(folder, with_helper=False), "-d", str(folder / "classes"),
                            str(t1.ROOT / "tools" / "osmand_route" / "OsmAndRoute.java")], check=True)
        return folder
    folder = CACHE / "brouter"
    if not (folder / "brouter.jar").exists():
        z = _download(*BROUTER_ZIP, CACHE / "brouter.zip")
        with zipfile.ZipFile(z) as zf:
            zf.extractall(CACHE / "brouter-release")
        jar = next((CACHE / "brouter-release").rglob("brouter-*-all.jar"))
        profiles = next((CACHE / "brouter-release").rglob("profiles2"))
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(jar, folder / "brouter.jar")
        shutil.copytree(profiles, folder / "profiles", dirs_exist_ok=True)
        for name in ("all", "softaccess"):  # the map builder needs these two
            subprocess.run(["curl", "-fsSL", "--retry", "2", "--max-time", "60", f"{BROUTER_PROFILES}{name}.brf",
                            "-o", str(folder / "profiles" / f"{name}.brf")], check=True)
    return folder


def osmand_classpath(folder: Path, with_helper: bool = True) -> str:
    mc = folder / "mc"
    parts = [str(mc / "OsmAndMapCreator.jar"), str(mc / "lib" / "*")]
    return ":".join(parts + ([str(folder / "classes")] if with_helper else []))


def osmand_build() -> str | None:
    path = CACHE / "osmand" / "build-sha256.txt"
    return path.read_text().strip() if path.exists() else None


_OSMAND_OBF: Path | None = None


def _port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _wait_answer(url: str, seconds: float) -> None:
    """Wait until the server answers HTTP at all (even 4xx): Docker opens a mapped port
    before the engine inside is listening, so an open port alone is not readiness."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=3):  # noqa: S310 - local engine only
                return
        except HTTPError:
            return
        except Exception:  # noqa: BLE001 - polling a starting local server
            time.sleep(0.5)
    raise RuntimeError(f"Local engine did not answer: {url}")


def _wait_ok(url: str, seconds: float, proc: subprocess.Popen) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"Local engine exited (code {proc.returncode}) before it was ready")
        try:
            with urlopen(url, timeout=3) as r:  # noqa: S310 - local engine only
                if r.status == 200 and b"ready" in r.read(2000).lower():
                    return
        except Exception:  # noqa: BLE001 - polling a starting local server
            pass
        time.sleep(1)
    raise RuntimeError(f"Local engine did not start: {url}")


@contextmanager
def serve(engine: str, pbf: Path, work: Path):
    """Build the engine's graph from this clip only and run it locally."""
    if engine in ("OSRM", "Valhalla", "GraphHopper"):
        with _serve_turn001_engine(engine, pbf, work):
            yield
        return
    home = install(engine)
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    log = (work / "engine.log").open("w")
    proc = None
    try:
        if engine == "OsmAnd":
            global _OSMAND_OBF
            shutil.copyfile(pbf, work / "clip.osm.pbf")
            subprocess.run([JAVA, "-Xmx2g", f"-Djava.util.logging.config.file={home / 'mc' / 'logging.properties'}",
                            "-cp", osmand_classpath(home, with_helper=False), "net.osmand.MainUtilities",
                            "generate-obf", "clip.osm.pbf"], cwd=work, check=True, stdout=log, stderr=subprocess.STDOUT)
            obfs = [p for p in work.glob("*.obf")]
            if len(obfs) != 1:
                raise MapRejected("OsmAndMapCreator built no single OBF from the clip")
            _OSMAND_OBF = obfs[0]
            yield
            return
        if engine == "openrouteservice":
            config = (t1.ROOT / "config" / "ors-gps001.yml").read_text()
            config = config.replace("results/gps001.osm.pbf", str(pbf)).replace("results/ors-graphs",
                                                                                  str(work / "graphs"))
            (work / "ors.yml").write_text(config)
            proc = subprocess.Popen([ORS_JAVA, "-Xms128m", "-Xmx1536m", "-jar", str(home / "ors.jar")], stdout=log,
                                    stderr=subprocess.STDOUT, env={**os.environ,
                                                                   "ORS_CONFIG_LOCATION": str(work / "ors.yml")})
            _wait_ok(f"http://127.0.0.1:{ORS_PORT}/ors/v2/health", 300, proc)
        else:
            for d in ("nodetiles", "waytiles", "nodes55", "waytiles55", "unodes55", "segments", "elevation",
                      "customprofiles"):
                (work / d).mkdir()
            prof, jar = home / "profiles", str(home / "brouter.jar")
            steps = [["btools.mapcreator.OsmFastCutter", str(prof / "lookups.dat"), "nodetiles", "waytiles", "nodes55",
                      "waytiles55", "bordernids.dat", "relations.dat", "restrictions.dat", str(prof / "all.brf"),
                      str(prof / "trekking.brf"), str(prof / "softaccess.brf"), str(pbf)],
                     ["btools.mapcreator.PosUnifier", "nodes55", "unodes55", "bordernids.dat", "bordernodes.dat",
                      "elevation"],
                     ["btools.mapcreator.WayLinker", "unodes55", "waytiles55", "bordernodes.dat", "restrictions.dat",
                      str(prof / "lookups.dat"), str(prof / "all.brf"), "segments", "rd5"]]
            for step in steps:
                subprocess.run([JAVA, "-Xmx512m", "-DavoidMapPolling=true", "-cp", jar, *step], cwd=work, check=True,
                               stdout=log, stderr=subprocess.STDOUT)
            if not list((work / "segments").glob("*.rd5")):
                raise RuntimeError("BRouter built no segments from the clip")
            proc = subprocess.Popen([JAVA, "-Xmx512m", "-DmaxRunningTime=30", "-cp", jar, "btools.server.RouteServer",
                                     str(work / "segments"), str(prof), str(work / "customprofiles"), str(BROUTER_PORT),
                                     "1", "127.0.0.1"], stdout=log, stderr=subprocess.STDOUT)
            deadline = time.time() + 60
            while not _port_open(BROUTER_PORT):
                if time.time() > deadline or proc.poll() is not None:
                    raise RuntimeError("BRouter server did not start")
                time.sleep(0.5)
        yield
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
        log.close()
        shutil.rmtree(work, ignore_errors=True)


@contextmanager
def _serve_turn001_engine(engine: str, pbf: Path, work: Path):
    """OSRM, Valhalla or GraphHopper started on the clip exactly as TURN-001 starts them."""
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    shutil.copyfile(pbf, work / "input.osm.pbf")
    name = f"dmn-ref-{engine.lower()}"
    subprocess.run(["docker", "rm", "-f", name], capture_output=True)
    proc = None
    try:
        if engine == "OSRM":
            image = t1.IMAGES["OSRM"]
            for step in (["osrm-extract", "-p", "/opt/car.lua", "/data/input.osm.pbf"],
                         ["osrm-partition", "/data/input.osrm"], ["osrm-customize", "/data/input.osrm"]):
                r = subprocess.run(["docker", "run", "--rm", "-v", f"{work}:/data", image, *step],
                                   capture_output=True, text=True)
                if r.returncode:
                    raise MapRejected((r.stderr or r.stdout)[-300:])
            subprocess.run(["docker", "run", "-d", "--rm", "--name", name, "-p", "127.0.0.1:5000:5000",
                            "-v", f"{work}:/data", image, "osrm-routed", "--algorithm", "mld", "/data/input.osrm"],
                           check=True, capture_output=True)
            _wait_answer("http://127.0.0.1:5000/route/v1/driving/0,0;0,0", 60)
        elif engine == "Valhalla":
            subprocess.run(["docker", "run", "-d", "--rm", "--name", name, "-p", "127.0.0.1:8002:8002",
                            "-v", f"{work}:/custom_files", "-e", "build_admins=False", "-e", "build_time_zones=False",
                            "-e", "build_elevation=False", "-e", "build_transit=False", "-e", "serve_tiles=True",
                            "-e", "use_tiles_ignore_pbf=False", "-e", "use_default_speeds_config=False",
                            "-e", "build_tar=False", "-e", "server_threads=2", t1.IMAGES["Valhalla"]],
                           check=True, capture_output=True)
            _wait_alive("http://127.0.0.1:8002/status", 900,  # answers once the tiles are built
                        lambda: _container_running(name))
        else:
            (work / "config.yml").write_text(t1.graphhopper_config(work / "input.osm.pbf", work / "cache"))
            log = (work / "startup.log").open("w")
            proc = subprocess.Popen(["/opt/jdk17/bin/java", "-Xmx1g", "-jar", str(t1.WORK / "engines" / "gh.jar"),
                                     "server", str(work / "config.yml")], stdout=log, stderr=subprocess.STDOUT)
            _wait_alive("http://127.0.0.1:8989/health", 90, lambda: proc.poll() is None)
        yield
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
        if proc is not None:
            proc.terminate()
            proc.wait(timeout=30)
        subprocess.run(["sudo", "-n", "rm", "-rf", str(work)], capture_output=True)
        shutil.rmtree(work, ignore_errors=True)


def _container_running(name: str) -> bool:
    r = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", name], capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "true"


def _wait_alive(url: str, seconds: float, alive) -> None:
    """t1._wait, but a server that stops while starting is reported at once (owner-approved,
    17 Oct 2026: run D could only see GraphHopper/Valhalla start failures as time-outs)."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            t1._wait(url, 5)
            return
        except RuntimeError:
            if not alive():
                raise MapRejected(f"engine stopped while starting ({url})") from None
    raise RuntimeError(f"Local engine did not start: {url}")


class MapRejected(RuntimeError):
    """The engine's own map builder refused the clip."""


def _slight(text: str) -> bool:
    text = (text or "").lower()
    return "slight" in text or "keep" in text or "stay" in text


def _kind(text: str) -> str:
    text = (text or "").lower()
    if "uturn" in text or "u-turn" in text or "u turn" in text:
        return "uturn"
    if "left" in text:
        return "left"
    if "right" in text:
        return "right"
    return "straight"


def osrm(geom, headings):
    o, d = geom["origin"], geom["destination"]
    url = (f"http://127.0.0.1:5000/route/v1/driving/{o[1]:.7f},{o[0]:.7f};{d[1]:.7f},{d[0]:.7f}"
           "?overview=full&geometries=geojson&continue_straight=true&steps=true"
           f"&bearings={headings[0]},{t1.HEADING_TOLERANCE};{headings[1]},{t1.HEADING_TOLERANCE}")
    from urllib.error import HTTPError
    began = time.perf_counter()
    try:
        data = t1._http_json(url)
    except HTTPError as exc:
        data = json.loads(exc.read() or b"{}")
    ms = (time.perf_counter() - began) * 1000
    if data.get("code") == "NoRoute":
        return None, [], ms
    if data.get("code") != "Ok":
        raise RuntimeError(f"OSRM {data.get('code')}: {data.get('message', '')[:200]}")
    route = data["routes"][0]
    steps = []
    for leg in route["legs"]:
        for s in leg["steps"]:
            m = s["maneuver"]
            if m["type"] in ("depart", "arrive"):
                continue
            at = (m["location"][1], m["location"][0])
            if m["type"] in ("roundabout", "rotary", "roundabout turn") and "exit" in m:
                steps.append({"at": at, "kind": "roundabout", "exit": m["exit"]})
            elif m["type"] not in ("exit roundabout", "exit rotary"):
                raw = f"{m['type']} {m.get('modifier', '')}"
                steps.append({"at": at, "kind": _kind(m.get("modifier", "")), "slight": _slight(raw), "raw": raw})
    return [(lat, lon) for lon, lat in route["geometry"]["coordinates"]], steps, ms


VALHALLA_KIND = {8: "straight", 22: "straight", 9: "right", 10: "right", 11: "right", 23: "right", 20: "right",
                 16: "left", 15: "left", 14: "left", 24: "left", 21: "left", 12: "uturn", 13: "uturn"}


def valhalla(geom, headings):
    from urllib.error import HTTPError
    o, d = geom["origin"], geom["destination"]
    body = json.dumps({"locations": [
        {"lat": o[0], "lon": o[1], "heading": headings[0], "heading_tolerance": t1.HEADING_TOLERANCE},
        {"lat": d[0], "lon": d[1], "heading": headings[1], "heading_tolerance": t1.HEADING_TOLERANCE}],
        "costing": "auto", "directions_type": "maneuvers"}).encode()
    began = time.perf_counter()
    try:
        data = t1._http_json("http://127.0.0.1:8002/route", body)
    except HTTPError as exc:
        payload = json.loads(exc.read() or b"{}")
        if payload.get("error_code") in (442, 443):
            return None, [], (time.perf_counter() - began) * 1000
        raise RuntimeError(f"Valhalla {payload.get('error_code')}: {payload.get('error', '')[:200]}") from exc
    ms = (time.perf_counter() - began) * 1000
    points, steps = [], []
    for leg in data["trip"]["legs"]:
        shape = t1._decode_polyline(leg["shape"], 6)
        for m in leg["maneuvers"]:
            at = shape[min(m["begin_shape_index"], len(shape) - 1)]
            if m["type"] == 26:
                steps.append({"at": at, "kind": "roundabout", "exit": m.get("roundabout_exit_count")})
            elif m["type"] in VALHALLA_KIND:
                steps.append({"at": at, "kind": VALHALLA_KIND[m["type"]], "slight": m["type"] in (9, 16, 23, 24),
                              "raw": str(m["type"])})
        points.extend(shape)
    return points, steps, ms


GH_KIND = {-3: "left", -2: "left", -1: "left", -7: "left", 1: "right", 2: "right", 3: "right", 7: "right",
           0: "straight", -98: "uturn", -8: "uturn", 8: "uturn"}


def graphhopper(geom, headings):
    from urllib.error import HTTPError
    o, d = geom["origin"], geom["destination"]
    url = (f"http://127.0.0.1:8989/route?point={o[0]:.7f},{o[1]:.7f}&point={d[0]:.7f},{d[1]:.7f}"
           "&profile=car&points_encoded=false&instructions=true&ch.disable=true&way_point_max_distance=0"
           f"&heading={headings[0]}&heading={headings[1]}")
    began = time.perf_counter()
    try:
        data = t1._http_json(url)
    except HTTPError as exc:
        body = json.loads(exc.read() or b"{}")
        if any("ConnectionNotFound" in str(h.get("details", "")) for h in body.get("hints", [])):
            return None, [], (time.perf_counter() - began) * 1000
        raise RuntimeError(f"GraphHopper HTTP {exc.code}: {body.get('message', '')[:200]}") from exc
    ms = (time.perf_counter() - began) * 1000
    path = data["paths"][0]
    points = [(lat, lon) for lon, lat in path["points"]["coordinates"]]
    steps = []
    for ins in path.get("instructions", []):
        at = points[min(ins["interval"][0], len(points) - 1)]
        if ins["sign"] == 6:
            steps.append({"at": at, "kind": "roundabout", "exit": ins.get("exit_number")})
        elif ins["sign"] in GH_KIND:
            steps.append({"at": at, "kind": GH_KIND[ins["sign"]], "slight": ins["sign"] in (-1, 1, -7, 7),
                          "raw": str(ins["sign"])})
    return points, steps, ms


QUERIES = {"OSRM": osrm, "Valhalla": valhalla, "GraphHopper": graphhopper}


ORS_KIND = {0: "left", 2: "left", 4: "left", 12: "left", 1: "right", 3: "right", 5: "right", 13: "right",
            6: "straight", 9: "uturn"}
BROUTER_KIND = {1: "straight", 2: "left", 3: "left", 4: "left", 8: "left", 5: "right", 6: "right", 7: "right",
                9: "right", 10: "uturn", 11: "uturn", 12: "uturn"}


OSMAND_KIND = {1: "straight", 2: "left", 3: "left", 4: "left", 8: "left", 5: "right", 6: "right", 7: "right",
               9: "right", 10: "uturn", 11: "uturn"}


def osmand_raw(geom: dict, headings: tuple[int, int]) -> dict:
    o, d = geom["origin"], geom["destination"]
    began = time.perf_counter()
    r = subprocess.run([JAVA, "-Xmx1g", "-cp", osmand_classpath(CACHE / "osmand"), "OsmAndRoute", str(_OSMAND_OBF),
                        f"{o[0]:.7f}", f"{o[1]:.7f}", f"{d[0]:.7f}", f"{d[1]:.7f}", str(headings[0]),
                        str(headings[1])], capture_output=True, text=True, timeout=120,
                       cwd=_OSMAND_OBF.parent)  # OsmAnd writes regions.ocbf into its working folder
    line = next((ln for ln in r.stdout.splitlines() if ln.startswith("{")), None)
    if line is None:
        raise RuntimeError(f"OsmAnd router gave no answer: {(r.stderr or r.stdout)[-200:]}")
    data = json.loads(line)
    data["wall_ms"] = (time.perf_counter() - began) * 1000
    return data


def osmand(geom: dict, headings: tuple[int, int]):
    data = osmand_raw(geom, headings)
    if data.get("route", "") is None:
        return None, [], data["ms"]
    points = [tuple(p) for p in data["points"]]
    steps = []
    for s in data["steps"]:
        if s["point"] == 0:
            continue  # the departure instruction, skipped for every engine
        if s["roundabout"] or s["value"] in (13, 14):
            steps.append({"at": tuple(s["at"]), "kind": "roundabout", "exit": s["exit"]})
        elif s["value"] in OSMAND_KIND:
            steps.append({"at": tuple(s["at"]), "kind": OSMAND_KIND[s["value"]], "slight": s["value"] in (3, 6, 8, 9),
                          "raw": str(s["value"])})
    return points, steps, data["ms"]


def query(engine: str, geom: dict, headings: tuple[int, int]):
    """(points, steps, ms) or (None, [], ms) when the engine finds no route."""
    if engine in QUERIES:
        return QUERIES[engine](geom, headings)
    if engine == "OsmAnd":
        return osmand(geom, headings)
    o, d = geom["origin"], geom["destination"]
    began = time.perf_counter()
    if engine == "openrouteservice":
        body = json.dumps({"coordinates": [[o[1], o[0]], [d[1], d[0]]], "instructions": True,
                           "bearings": [[headings[0], t1.HEADING_TOLERANCE], [headings[1], t1.HEADING_TOLERANCE]],
                           "continue_straight": True}).encode()
        req = Request(f"http://127.0.0.1:{ORS_PORT}/ors/v2/directions/driving-car/geojson", body,
                      {"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=30) as r:  # noqa: S310 - local engine only
                data = json.load(r)
        except HTTPError as exc:
            err = json.loads(exc.read() or b"{}").get("error", {})
            if isinstance(err, dict) and err.get("code") in (2009, 2010):  # route not found / point not found
                return None, [], (time.perf_counter() - began) * 1000
            raise RuntimeError(f"openrouteservice {exc.code}: {str(err)[:200]}") from exc
        ms = (time.perf_counter() - began) * 1000
        feature = data["features"][0]
        points = [(lat, lon) for lon, lat in feature["geometry"]["coordinates"]]
        steps = []
        for seg in feature["properties"].get("segments", []):
            for s in seg.get("steps", []):
                at = points[min(s["way_points"][0], len(points) - 1)]
                if s["type"] == 7:
                    steps.append({"at": at, "kind": "roundabout", "exit": s.get("exit_number")})
                elif s["type"] in ORS_KIND:
                    steps.append({"at": at, "kind": ORS_KIND[s["type"]], "slight": s["type"] in (4, 5, 12, 13),
                                  "raw": str(s["type"])})
        return points, steps, ms
    url = f"http://127.0.0.1:{BROUTER_PORT}/brouter?" + urlencode(dict(
        lonlats=f"{o[1]:.7f},{o[0]:.7f}|{d[1]:.7f},{d[0]:.7f}", profile="car-vario", alternativeidx=0,
        format="geojson", timode=3))
    try:
        with urlopen(url, timeout=30) as r:  # noqa: S310 - local engine only
            data = json.load(r)
    except HTTPError as exc:
        text = (exc.read() or b"").decode(errors="replace").lower()
        if "no track found" in text or "target island" in text or "not mapped" in text:
            return None, [], (time.perf_counter() - began) * 1000
        raise RuntimeError(f"BRouter {exc.code}: {text[:200]}") from exc
    ms = (time.perf_counter() - began) * 1000
    feature = data["features"][0]
    points = [(p[1], p[0]) for p in feature["geometry"]["coordinates"]]
    steps = []
    for h in feature["properties"].get("voicehints", []):
        at = points[min(h[0], len(points) - 1)]
        if h[1] in (13, 14):
            steps.append({"at": at, "kind": "roundabout", "exit": abs(h[2])})
        elif h[1] in BROUTER_KIND:
            steps.append({"at": at, "kind": BROUTER_KIND[h[1]], "slight": h[1] in (3, 6, 8, 9), "raw": str(h[1])})
    return points, steps, ms


def route(engine: str, folder: Path, clip, geom: dict):
    """Build the engine on this case's clip and ask once: (points, steps, ms), or an error dict."""
    try:
        with serve(engine, folder / "clip.osm.pbf", folder / engine.lower()):
            return query(engine, geom, t1.travel_headings(clip, geom))
    except MapRejected as exc:
        return {"verdict": "ENGINE_REJECTED_MAP", "route": "ENGINE_REJECTED_MAP", "detail": str(exc)[:300]}
    except Exception as exc:  # noqa: BLE001 - recorded, never hidden
        return {"verdict": "ERROR", "route": "ERROR", "detail": f"{type(exc).__name__}: {exc}"[:300]}


def engine_path(clip, geom: dict, points):
    """OSM node path of an engine route (TURN-001 matching plus a start/finish fix).

    TURN-001's matcher only restores simplified-away nodes once it has matched one, so
    when an engine draws its first line from the mid-segment start point straight to a
    node further on, the node(s) in between were lost and a correct start looked off
    target. When the route starts (finishes) within SNAP_TOLERANCE_M of the test point,
    the start (end) node of the test segment is placed before (after) the line, so the
    same restoration fills the gap. A route that really starts elsewhere or in the other
    direction still does not match the test segment. Same rule for every engine.
    """
    pts = [tuple(p) for p in points]
    o_seg, d_seg = list(geom["origin_segment"]), list(geom["destination_segment"])
    start_ok = bool(pts) and t1.metres(pts[0], tuple(geom["origin"])) <= t1.SNAP_TOLERANCE_M
    end_ok = bool(pts) and t1.metres(pts[-1], tuple(geom["destination"])) <= t1.SNAP_TOLERANCE_M
    seeded = ([clip.coords[o_seg[0]]] if start_ok else []) + pts + ([clip.coords[d_seg[1]]] if end_ok else [])
    nodes = clip.match_nodes(seeded)
    if not (nodes[:2] == o_seg and nodes[-2:] == d_seg):
        # owner-approved (17 Oct 2026): run D/C found long engine lines the 1 m reader
        # loses; read them piece by piece instead (same rule for every engine), and keep
        # the second reading only when it is a connected path along the line
        alt = piece_path(clip, seeded)
        if alt and alt[:2] == o_seg and alt[-2:] == d_seg:
            nodes = alt
    return nodes, {"start_snap_m": None if not pts else round(t1.metres(pts[0], tuple(geom["origin"])), 1),
                   "end_snap_m": None if not pts else round(t1.metres(pts[-1], tuple(geom["destination"])), 1)}


PIECE_SNAP_M, PIECE_STEP_M, BRIDGE_PIECES = 3.0, 2.0, 3


def piece_path(clip, points) -> list[str] | None:
    """OSM node path of a drawn line, read road piece by road piece.

    Every PIECE_STEP_M along the line, the nearest piece of a road (within PIECE_SNAP_M)
    whose direction agrees with the line; consecutive pieces must join, or be joined by
    at most BRIDGE_PIECES pieces a car may travel (a simplified bend). Otherwise None:
    a line that cannot be read is never forced onto a road.
    """
    pieces = []
    for a, b in zip(points, points[1:]):
        length = t1.metres(a, b)
        if length < 0.3:
            continue
        heading = t1.bearing(a, b)
        for k in range(max(1, int(length // PIECE_STEP_M))):
            f = (k + 0.5) / max(1, int(length // PIECE_STEP_M))
            p = (a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]))
            piece = _piece_at(clip, p, heading)
            if piece and (not pieces or pieces[-1] != piece):
                pieces.append(piece)
    if not pieces:
        return None
    nodes = list(pieces[0])
    for x, y in pieces[1:]:
        if x == nodes[-1]:
            nodes.append(y)
            continue
        bridge = _bridge(clip, nodes[-1], x)
        if bridge is None:
            return None
        nodes += bridge[1:] + [y]
    return [n for i, n in enumerate(nodes) if i == 0 or nodes[i - 1] != n]


def _piece_grid(clip) -> dict:
    """Road pieces indexed by ~11 m grid cells along their whole length (built once per clip)."""
    grid = getattr(clip, "_rund_piece_grid", None)
    if grid is None:
        grid = {}
        for w, (refs, tags) in clip.ways.items():
            if not clip.drivable(tags):
                continue
            for u, v in zip(refs, refs[1:]):
                if u not in clip.coords or v not in clip.coords:
                    continue
                a, b = clip.coords[u], clip.coords[v]
                steps = max(1, int(t1.metres(a, b) // 5))
                for k in range(steps + 1):
                    f = k / steps
                    cell = (round((a[0] + f * (b[0] - a[0])) * 1e4), round((a[1] + f * (b[1] - a[1])) * 1e4))
                    grid.setdefault(cell, set()).add((u, v))
        clip._rund_piece_grid = grid
    return grid


def _piece_at(clip, point, heading):
    """Nearest road piece within PIECE_SNAP_M whose direction agrees with heading (directed)."""
    from benchmarks.journey001 import _seg_dist
    grid = _piece_grid(clip)
    lat, lon = round(point[0] * 1e4), round(point[1] * 1e4)
    cand = set()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            cand |= grid.get((lat + dy, lon + dx), set())
    best = None
    for u, v in cand:
        d = _seg_dist(point, clip.coords[u], clip.coords[v])
        if d > PIECE_SNAP_M:
            continue
        fwd = abs((t1.bearing(clip.coords[u], clip.coords[v]) - heading + 180) % 360 - 180) <= 45
        back = abs((t1.bearing(clip.coords[v], clip.coords[u]) - heading + 180) % 360 - 180) <= 45
        if fwd or back:
            piece = (u, v) if fwd else (v, u)
            if best is None or d < best[0]:
                best = (d, piece)
    return None if best is None else best[1]


def _bridge(clip, start: str, goal: str) -> list[str] | None:
    """Shortest chain of at most BRIDGE_PIECES travellable pieces from start to goal."""
    frontier, seen = [[start]], {start}
    for _ in range(BRIDGE_PIECES):
        nxt = []
        for path in frontier:
            for w in sorted(w for w in clip.node_ways.get(path[-1], ()) if clip.drivable(clip.ways[w][1])):
                for m in _neighbours(clip, w, path[-1]):
                    if m in seen or not clip.can_travel(w, path[-1], m):
                        continue
                    if m == goal:
                        return path + [m]
                    seen.add(m)
                    nxt.append(path + [m])
        frontier = nxt
    return None


def _neighbours(clip, way: str, node: str) -> list[str]:
    refs = clip.ways[way][0]
    return [refs[k] for i, x in enumerate(refs) if x == node for k in (i - 1, i + 1) if 0 <= k < len(refs)]


# --------------------------------------------------------------------------- run B2 details
class NotAvailable(RuntimeError):
    """The engine has no public output for this detail."""


def query_details(engine: str, geom: dict, headings: tuple[int, int]):
    """(points, details, ms): per-segment speed limits (km/h or None) and lane advice per step.

    Only OSRM (lanes) and GraphHopper (speed limits) expose these in their route
    answers; the others raise NotAvailable.
    """
    o, d = geom["origin"], geom["destination"]
    began = time.perf_counter()
    if engine == "OSRM":
        url = (f"http://127.0.0.1:5000/route/v1/driving/{o[1]:.7f},{o[0]:.7f};{d[1]:.7f},{d[0]:.7f}"
               "?overview=full&geometries=geojson&continue_straight=true&steps=true"
               f"&bearings={headings[0]},{t1.HEADING_TOLERANCE};{headings[1]},{t1.HEADING_TOLERANCE}")
        try:
            data = t1._http_json(url)
        except HTTPError as exc:
            data = json.loads(exc.read() or b"{}")
        ms = (time.perf_counter() - began) * 1000
        if data.get("code") == "NoRoute":
            return None, {}, ms
        if data.get("code") != "Ok":
            raise RuntimeError(f"OSRM {data.get('code')}")
        r = data["routes"][0]
        points = [(lat, lon) for lon, lat in r["geometry"]["coordinates"]]
        lanes = []
        for leg in r["legs"]:
            for s in leg["steps"]:
                for i in s.get("intersections", []):
                    if i.get("lanes"):
                        lanes.append({"at": (i["location"][1], i["location"][0]),
                                      "valid": [k + 1 for k, ln in enumerate(i["lanes"]) if ln.get("valid")],
                                      "count": len(i["lanes"])})
        # OSRM 5.27 has no speed-limit annotation (annotations=maxspeed is an InvalidQuery)
        return points, {"segment_limits_kph": None, "lanes": lanes}, ms
    if engine == "GraphHopper":
        url = (f"http://127.0.0.1:8989/route?point={o[0]:.7f},{o[1]:.7f}&point={d[0]:.7f},{d[1]:.7f}"
               "&profile=car&points_encoded=false&instructions=false&ch.disable=true&way_point_max_distance=0"
               f"&heading={headings[0]}&heading={headings[1]}&details=max_speed")
        try:
            data = t1._http_json(url)
        except HTTPError as exc:
            body = json.loads(exc.read() or b"{}")
            if any("ConnectionNotFound" in str(h.get("details", "")) for h in body.get("hints", [])):
                return None, {}, (time.perf_counter() - began) * 1000
            raise RuntimeError(f"GraphHopper HTTP {exc.code}") from exc
        ms = (time.perf_counter() - began) * 1000
        path = data["paths"][0]
        points = [(lat, lon) for lon, lat in path["points"]["coordinates"]]
        limits = [None] * max(len(points) - 1, 0)
        for start, end, value in path.get("details", {}).get("max_speed", []):
            for k in range(start, min(end, len(limits))):
                limits[k] = float(value) if value not in (None, "Infinity") and float(value) < 1000 else None
        return points, {"segment_limits_kph": limits, "lanes": None}, ms
    if engine == "OsmAnd":
        data = osmand_raw(geom, headings)
        if data.get("route", "") is None:
            return None, {}, data["ms"]
        points = [tuple(p) for p in data["points"]]
        lanes = [{"at": tuple(s["at"]), "valid": s["lanes"], "count": s["lane_count"]}
                 for s in data["steps"] if s["lane_count"]]
        return points, {"segment_limits_kph": data["limits_kph"], "lanes": lanes}, data["ms"]
    raise NotAvailable(engine)


def route_details(engine: str, folder: Path, clip, geom: dict):
    """Like route() but asking for speed limits and lanes; GraphHopper gets max_speed stored."""
    if engine not in ("OSRM", "GraphHopper", "OsmAnd"):
        return {"route": "NOT_AVAILABLE"}
    saved = t1.graphhopper_config
    if engine == "GraphHopper":  # store OSM maxspeed so the route answer can report it
        t1.graphhopper_config = lambda pbf, cache: saved(pbf, cache).replace(
            "graph.encoded_values: car_access,car_average_speed,road_access",
            "graph.encoded_values: car_access,car_average_speed,road_access,max_speed")
    try:
        with serve(engine, folder / "clip.osm.pbf", folder / engine.lower()):
            return query_details(engine, geom, t1.travel_headings(clip, geom))
    except MapRejected as exc:
        return {"route": "ENGINE_REJECTED_MAP", "detail": str(exc)[:300]}
    except Exception as exc:  # noqa: BLE001 - recorded, never hidden
        return {"route": "ERROR", "detail": f"{type(exc).__name__}: {exc}"[:300]}
    finally:
        t1.graphhopper_config = saved

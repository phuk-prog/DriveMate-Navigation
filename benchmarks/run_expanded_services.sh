#!/usr/bin/env bash
# One bounded second dataset per existing isolated engine job; reuse pinned images.
set -euo pipefail
engine="$1"
python -m benchmarks.expanded_fixture
osmium cat results/expanded/map/expanded.osm -o results/expanded/map/expanded.osm.pbf
docker rm -f reference reference-ch >/dev/null 2>&1 || true
if [[ "$engine" == osrm ]]; then
  IMAGE='ghcr.io/project-osrm/osrm-backend:v5.27.1@sha256:855614a38f464b0558a2ad6eaa7cb8c139f39887da9b38b485ce453c6e6e6124'
  docker run --rm -v "$PWD/results/expanded/map:/data" "$IMAGE" osrm-extract -p /opt/car.lua /data/expanded.osm.pbf
  mkdir -p results/expanded/ch-map
  cp results/expanded/map/expanded.osrm* results/expanded/ch-map/
  docker run --rm -v "$PWD/results/expanded/map:/data" "$IMAGE" osrm-partition /data/expanded.osrm
  docker run --rm -v "$PWD/results/expanded/map:/data" "$IMAGE" osrm-customize /data/expanded.osrm
  docker run --rm -v "$PWD/results/expanded/ch-map:/data" "$IMAGE" osrm-contract /data/expanded.osrm
  docker run -d --rm --name reference -p 127.0.0.1:5000:5000 -v "$PWD/results/expanded/map:/data" "$IMAGE" osrm-routed --algorithm mld /data/expanded.osrm
  docker run -d --rm --name reference-ch -p 127.0.0.1:5001:5000 -v "$PWD/results/expanded/ch-map:/data" "$IMAGE" osrm-routed --algorithm ch /data/expanded.osrm
  python -m benchmarks.expanded_comparison --engine osrm --version "5.27.1/pinned-855614a"
  python -m benchmarks.expanded_comparison --engine osrm-ch --version "5.27.1/pinned-855614a"
elif [[ "$engine" == valhalla ]]; then
  IMAGE='ghcr.io/valhalla/valhalla-scripted:3.9.1@sha256:6238809f9dc3057743d70a20efd3911ec38e458bfa13a0601909b58f68dfd956'
  docker run -d --rm --name reference -p 127.0.0.1:8002:8002 -v "$PWD/results/expanded/map:/custom_files" -e build_admins=False -e build_time_zones=False -e build_elevation=False -e use_default_speeds_config=False -e build_tar=False -e server_threads=2 "$IMAGE"
  # Wait for completed HTTP route response, not merely an open socket.
  python -c 'import time; from benchmarks.expanded_fixture import suite; from benchmarks.whole_drive import prepared; from benchmarks.cloud_reference import call; d=suite(); p=prepared(d["osm"]); c=d["cases"][0]; deadline=time.monotonic()+240
while True:
 try:
  r=call("valhalla",p,c["start"],c["end"])
  if r.get("trip",{}).get("legs"): break
 except (OSError,ValueError): pass
 if time.monotonic()>deadline: raise RuntimeError("Expanded Valhalla map unavailable")
 time.sleep(1)'
  python -m benchmarks.expanded_comparison --engine valhalla --version "3.9.1/pinned-6238809"
else
  exit 2
fi

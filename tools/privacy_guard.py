"""Fail-closed privacy guard for the PUBLIC research repository.

Runs on the committed file list; rejects risky filenames, binary blobs, email
addresses and common credentials, without printing matched sensitive text.
This is an extra guard, NOT a substitute for human privacy review. Never
commit personal journeys, GPS traces, private app exports or proprietary maps.
"""
from __future__ import annotations

from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

FORBIDDEN_PARTS = frozenset({
    "private", "personal", "recordings", "recording", "traces", "trace",
    "secrets", "credentials", "home-address", "work-address", "user-data",
})
FORBIDDEN_SUFFIXES = frozenset({
    ".gpx", ".kml", ".kmz", ".fit", ".geojson", ".pbf", ".osm",
    ".mbtiles", ".sqlite", ".db", ".jks", ".keystore", ".pem",
    ".p12", ".pfx", ".pkcs12", ".apk", ".aab", ".jpg", ".jpeg",
    ".png", ".webp", ".heic", ".mp4", ".mov", ".wav", ".pdf", ".zip",
})
SECRET_RE = re.compile(
    r"(?i)(?:github_pat_[a-z0-9_]{20,}|gh[pousr]_[a-z0-9]{20,}|"
    r"sk_(?:live|test)_[a-z0-9]{12,}|AIza[a-z0-9_\-]{30,}|"
    r"-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----)"
)
EMAIL_RE = re.compile(r"(?i)\b[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}\b")
TRACK_RE = re.compile(r"(?i)(?:<gpx\b|<trkpt\b|<wpt\b|<Placemark\b|"
                      r'"(?:latitude|longitude|gps_lat|gps_lon|imei|vin)"\s*:)')
MAX_SOURCE_BYTES = 1_000_000


def inspect_file(relative_path: str, contents: bytes) -> list[str]:
    """Return generic findings, never the contents of a suspect secret."""
    p = PurePosixPath(relative_path)
    reasons = []
    if p.is_absolute() or ".." in p.parts or "\\" in relative_path:
        reasons.append("unsafe path")
    if any(part.lower() in FORBIDDEN_PARTS for part in p.parts):
        reasons.append("privacy-sensitive directory")
    if p.suffix.lower() in FORBIDDEN_SUFFIXES or p.name.lower().startswith(".env"):
        reasons.append("blocked data/binary/credential format")
    if len(contents) > MAX_SOURCE_BYTES or b"\x00" in contents:
        reasons.append("oversized or binary file")
        return reasons
    try:
        text = contents.decode("utf-8")
    except UnicodeDecodeError:
        reasons.append("not UTF-8 text")
        return reasons
    if SECRET_RE.search(text):
        reasons.append("potential credential")
    if EMAIL_RE.search(text):
        reasons.append("possible personal email address")
    if TRACK_RE.search(text):
        reasons.append("possible location/identity recording")
    # Every committed fixture must explicitly say it is synthetic.
    if p.parts[:2] == ("benchmarks", "fixtures"):
        if "synthetic" not in text[:3000].lower():
            reasons.append("fixture lacks explicit synthetic classification")
    return reasons


def scan_repository(root: Path) -> dict[str, list[str]]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=True,
    )
    findings = {}
    for item in result.stdout.split(b"\x00"):
        if not item:
            continue
        try:
            name = item.decode("utf-8")
            contents = (root / name).read_bytes()
            issues = inspect_file(name, contents)
        except (UnicodeDecodeError, OSError):
            name = "<unreadable path>"
            issues = ["unreadable tracked file"]
        if issues:
            findings[name] = issues
    return findings


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    findings = scan_repository(root)
    if findings:
        for path, issues in sorted(findings.items()):
            print(f"PRIVACY CHECK FAILED: {path}: {', '.join(issues)}", file=sys.stderr)
        return 1
    print("Privacy guard passed (heuristic scan of tracked files; manual review still required).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

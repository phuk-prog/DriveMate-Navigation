"""Shared work register for every AI (Claude, Codex, others) working on this repository.

One small JSON file per piece of work in work/items/<ID>.json says what it is, its
state (next / in_progress / done / blocked), which AI and branch hold it, what was
found, where the results are and a fingerprint of the exact inputs it ran on.
`show` reads those files from this checkout AND every fetched remote branch, so an
AI on its own branch still sees what the others are doing.

    python3 -m tools.work_status                      # what is done, running, next
    python3 -m tools.work_status --fetch              # same, after git fetch
    python3 -m tools.work_status seen FINGERPRINT     # exit 1 if already done
    python3 -m tools.work_status start ID --title T --agent NAME
    python3 -m tools.work_status finish ID --summary S [--results F] [--run URL] [--fingerprint X]
    python3 -m tools.work_status plan ID --title T [--why W]
    python3 -m tools.work_status block ID --summary S
    python3 -m tools.work_status where TOPIC          # where is X? (cheapest place first)
    python3 -m tools.work_status source "WHAT" --where PLACE --cost tiny|small|large --topics a,b
    python3 -m tools.work_status import-docs          # register docs/*_RESULTS.md as done

work/index.json is the shared map of WHERE things are (repo files, GitHub job
summaries, data branches, Google Drive, any URL), each with a cost and when to read
it; `show` prints its read-first list, cheapest first. Items can carry their own
--read-first and --source pointers, so an AI opens only what its task needs.

`start` refuses work another AI holds on another branch (updated in the last
STALE_HOURS) and work already done with the same fingerprint, so nothing is
repeated without a reason (use --reason to record a deliberate rerun).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ROOT / "work" / "items"
INDEX = ROOT / "work" / "index.json"
COSTS = ("tiny", "small", "large")
STATES = ("in_progress", "blocked", "next", "done")
STALE_HOURS = 24


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)
    return done.stdout if done.returncode == 0 else ""


def _branch() -> str:
    return _git("rev-parse", "--abbrev-ref", "HEAD").strip() or "unknown"


def _local() -> dict[str, dict]:
    out = {}
    for path in sorted(ITEMS.glob("*.json")):
        item = json.loads(path.read_text())
        out[item["id"]] = {**item, "_seen_on": "this checkout"}
    return out


def _remote() -> list[dict]:
    found = []
    for ref in _git("for-each-ref", "--format=%(refname:short)", "refs/remotes/origin").split():
        if ref.endswith("/HEAD"):
            continue
        for name in _git("ls-tree", "--name-only", f"{ref}:work/items").split():
            if name.endswith(".json"):
                try:
                    found.append({**json.loads(_git("show", f"{ref}:work/items/{name}")), "_seen_on": ref})
                except json.JSONDecodeError:
                    continue
    return found


def collect() -> dict[str, dict]:
    """Newest version of every item across this checkout and all remote branches."""
    items = _local()
    for item in _remote():
        mine = items.get(item["id"])
        if mine is None or item.get("updated", "") > mine.get("updated", ""):
            items[item["id"]] = item
    return items


def _age_hours(item: dict) -> float:
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(item["updated"])).total_seconds() / 3600
    except (KeyError, ValueError):
        return float("inf")


def load_index() -> dict:
    return json.loads(INDEX.read_text()) if INDEX.exists() else {"read_first": [], "sources": []}


def _cost_rank(entry: dict) -> int:
    return COSTS.index(entry.get("cost")) if entry.get("cost") in COSTS else len(COSTS)


def where(index: dict, items: dict[str, dict], topic: str) -> list[str]:
    """Every pointer whose text or topics mention `topic`, cheapest first."""
    t = topic.lower()
    hits = [e for e in index.get("read_first", []) + index.get("sources", [])
            if t in " ".join([e.get("what", ""), e.get("where", ""), *e.get("topics", [])]).lower()]
    out = [f"[{e.get('cost', '?')}] {e['what']}: {e['where']}" + (f" ({e['when']})" if e.get("when") else "")
           for e in sorted(hits, key=_cost_rank)]
    for i in items.values():
        text = " ".join(str(i.get(k, "")) for k in ("id", "title", "summary", "results", "why")).lower()
        if t in text:
            out.append(f"[item {i.get('state')}] {i['id']}: {i.get('results') or i.get('title', '')}")
            out.extend(f"    read first: {x}" for x in i.get("read_first", []))
            out.extend(f"    source: {x}" for x in i.get("sources", []))
    return out


def show(items: dict[str, dict], index: dict | None = None) -> str:
    lines = []
    first = sorted((index or {}).get("read_first", []), key=_cost_rank)
    if first:
        lines.append("READ FIRST (cheapest first; stop once you have what you need)")
        lines.extend(f"- [{e.get('cost', '?')}] {e['what']}: {e['where']}" +
                     (f" ({e['when']})" if e.get("when") else "") for e in first)
    for state in STATES:
        group = sorted((i for i in items.values() if i.get("state") == state),
                       key=lambda i: i.get("updated", ""), reverse=True)
        if not group:
            continue
        lines.append(state.upper().replace("_", " "))
        for i in group[:12] if state == "done" else group:
            who = f" [{i.get('agent', '?')} on {i.get('branch', '?')}, {i.get('updated', '?')[:16]}]"
            stale = " STALE: free to take over" if state == "in_progress" and _age_hours(i) > STALE_HOURS else ""
            lines.append(f"- {i['id']}: {i.get('title', '')}{who}{stale}")
            for key in ("summary", "why", "results"):
                if i.get(key):
                    lines.append(f"    {key}: {i[key]}")
            if state != "done":
                lines.extend(f"    read first: {x}" for x in i.get("read_first", []))
    return "\n".join(lines) or "No work items yet."


def _write(item: dict) -> Path:
    ITEMS.mkdir(parents=True, exist_ok=True)
    path = ITEMS / f"{item['id']}.json"
    clean = {k: v for k, v in item.items() if not k.startswith("_")}
    path.write_text(json.dumps(clean, indent=1, sort_keys=True) + "\n")
    return path


def seen(items: dict[str, dict], fingerprint: str) -> dict | None:
    return next((i for i in items.values() if i.get("state") == "done" and fingerprint in i.get("fingerprints", [])),
                None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fetch", action="store_true", help="git fetch origin first")
    sub = parser.add_subparsers(dest="cmd")
    p = sub.add_parser("seen")
    p.add_argument("fingerprint")
    p = sub.add_parser("where")
    p.add_argument("topic")
    p = sub.add_parser("source")
    p.add_argument("what")
    p.add_argument("--where", required=True, help="repo path, branch, URL, Google Drive link...")
    p.add_argument("--cost", choices=COSTS, default="small")
    p.add_argument("--when", help="when it is worth reading")
    p.add_argument("--topics", default="")
    p.add_argument("--read-first", action="store_true", help="add to the global read-first list")
    sub.add_parser("import-docs")
    for name in ("start", "plan", "finish", "block"):
        p = sub.add_parser(name)
        p.add_argument("id")
        p.add_argument("--title")
        p.add_argument("--agent", default="unknown AI")
        p.add_argument("--summary")
        p.add_argument("--why")
        p.add_argument("--results")
        p.add_argument("--run", action="append", default=[])
        p.add_argument("--fingerprint", action="append", default=[])
        p.add_argument("--reason", help="why repeating work that is already done or held")
        p.add_argument("--read-first", action="append", default=[], help="pointer to read before this item")
        p.add_argument("--source", action="append", default=[], help="where this item's data or evidence lives")
    args = parser.parse_args(argv)
    if args.fetch:
        subprocess.run(["git", "fetch", "-q", "origin"], cwd=ROOT)
    items = collect()
    index = load_index()
    if args.cmd in (None, "show"):
        print(show(items, index))
        return 0
    if args.cmd == "where":
        print("\n".join(where(index, items, args.topic)) or f"Nothing registered for '{args.topic}'.")
        return 0
    if args.cmd == "source":
        entry = {"what": args.what, "where": args.where, "cost": args.cost,
                 "topics": [x.strip() for x in args.topics.split(",") if x.strip()]}
        if args.when:
            entry["when"] = args.when
        key = "read_first" if args.read_first else "sources"
        index[key] = [e for e in index.get(key, []) if e["where"] != args.where] + [entry]
        INDEX.parent.mkdir(parents=True, exist_ok=True)
        INDEX.write_text(json.dumps(index, indent=1) + "\n")
        print(f"Registered in work/index.json ({key}): {args.what} -> {args.where}")
        return 0
    if args.cmd == "import-docs":
        added = 0
        for doc in sorted((ROOT / "docs").glob("*_RESULTS*.md")):
            ident = doc.stem.replace("_RESULTS", "").replace("_", "-")
            if ident in items:
                continue
            heading = next((l.lstrip("# ").strip() for l in doc.read_text().splitlines() if l.startswith("#")), ident)
            heading = heading.removeprefix(f"{ident}:").strip()
            _write({"id": ident, "title": heading[:120], "state": "done", "results": f"docs/{doc.name}",
                    "updated": _now(), "agent": "earlier session", "branch": "history", "runs": [],
                    "fingerprints": [], "history": [f"{_now()} imported from docs/{doc.name}"]})
            added += 1
        print(f"Registered {added} earlier results documents as done.")
        return 0
    if args.cmd == "seen":
        hit = seen(items, args.fingerprint)
        print(f"ALREADY DONE in {hit['id']} ({hit.get('results') or hit.get('summary', '')})" if hit else "not done yet")
        return 1 if hit else 0
    old = items.get(args.id, {})
    item = {k: v for k, v in old.items() if not k.startswith("_")} or {"id": args.id, "created": _now()}
    branch = _branch()
    if args.cmd == "start":
        holder = old.get("state") == "in_progress" and old.get("branch") != branch and _age_hours(old) <= STALE_HOURS
        repeat = old.get("state") == "done" or any(seen(items, f) for f in args.fingerprint)
        if (holder or repeat) and not args.reason:
            why = (f"held by {old.get('agent')} on {old.get('branch')}" if holder else "already done")
            print(f"REFUSED: {args.id} is {why}. Pick other work, or pass --reason to record a deliberate rerun.")
            return 2
    state = {"start": "in_progress", "plan": "next", "finish": "done", "block": "blocked"}[args.cmd]
    item.update(state=state, updated=_now(), branch=branch,
                agent=args.agent if args.agent != "unknown AI" else item.get("agent", args.agent))
    for key in ("title", "summary", "why", "results", "reason"):
        if getattr(args, key):
            item[key] = getattr(args, key)
    item["runs"] = sorted(set(item.get("runs", [])) | set(args.run))
    item["fingerprints"] = sorted(set(item.get("fingerprints", [])) | set(args.fingerprint))
    for key, values in (("read_first", args.read_first), ("sources", args.source)):
        if values:
            item[key] = list(dict.fromkeys(item.get(key, []) + values))
    item.setdefault("history", []).append(f"{item['updated']} {state} by {item['agent']} on {branch}")
    print(f"{args.id} -> {state}: {_write(item).name} (commit and push it so other AIs see it)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Usage: build_ffplan.py spec.json out.ffplan"""
import json, sys, uuid, re
from datetime import date, datetime, timedelta, timezone

MPD = 480  # minutes per working day
CONSTRAINTS = {"ASAP","ALAP","MSO","MFO","SNET","SNLT","FNET","FNLT"}

def iso(d, h=8):
    return datetime(d.year, d.month, d.day, h).strftime("%Y-%m-%dT%H:%M:%S.000Z")

def next_workday(d):
    while d.weekday() >= 5: d += timedelta(days=1)
    return d

def add_workdays(d, n):
    step = 1 if n >= 0 else -1
    for _ in range(abs(n)):
        d += timedelta(days=step)
        while d.weekday() >= 5: d += timedelta(days=step)
    return d

def parse_pred(s):
    m = re.fullmatch(r"\s*(\S+?)\s*(FS|SS|FF|SF)?\s*(?:([+-])\s*(\d+(?:\.\d+)?)\s*d?)?\s*", s)
    if not m: raise SystemExit(f"Bad predecessor '{s}'. Use 'key', 'key SS', 'key FS+2d'.")
    key, typ, sign, n = m.groups()
    lag = (float(n) if n else 0) * (-1 if sign == "-" else 1)
    return key, typ or "FS", int(round(lag * MPD))

def main(spec_path, out_path):
    spec = json.load(open(spec_path))
    start = next_workday(date.fromisoformat(spec["start"]))
    rows = spec["tasks"]
    for i, r in enumerate(rows): r.setdefault("key", str(i + 1))
    keys = {r["key"]: i for i, r in enumerate(rows)}
    if len(keys) != len(rows): raise SystemExit("Duplicate task keys.")

    # outline numbers and levels
    counters, tasks = [], []
    for i, r in enumerate(rows):
        lvl = int(r.get("level", 1))
        if lvl > len(counters) + 1: raise SystemExit(f"Task '{r['name']}' skips an outline level.")
        counters = counters[:lvl]
        if len(counters) < lvl: counters.append(0)
        counters[lvl - 1] += 1
        tasks.append({"id": str(i + 1), "outlineNumber": ".".join(map(str, counters)), "name": r["name"], "outlineLevel": lvl})
    has_child = {i for i in range(len(rows) - 1) if int(rows[i + 1].get("level", 1)) > int(rows[i].get("level", 1))}

    # resources
    res = []
    names = {}
    for r in rows:
        for n in ([r["owner"]] if r.get("owner") else []) + list(r.get("resources", [])):
            if n not in names:
                names[n] = str(len(names) + 1)
                res.append({"id": names[n], "name": n, "type": "work", "maxUnits": 1})

    # dependencies
    deps = []
    for i, r in enumerate(rows):
        for p in r.get("pred", []):
            k, typ, lag = parse_pred(p)
            if k not in keys: raise SystemExit(f"Task '{r['name']}' names unknown predecessor '{k}'.")
            deps.append({"predecessorId": str(keys[k] + 1), "successorId": str(i + 1), "type": typ, "lagMinutes": lag})

    st, fin = {}, {}
    for i, r in enumerate(rows):  # predecessors must be listed before their successors
        if i in has_child: continue
        d = max(0, int(r.get("days", 0 if r.get("milestone") else 1)))
        s, f_min = start, None
        for dep in (x for x in deps if x["successorId"] == str(i + 1)):
            j = int(dep["predecessorId"]) - 1
            if j not in st: raise SystemExit(f"List '{rows[j]['name']}' before '{r['name']}' (it is a predecessor).")
            lag = dep["lagMinutes"] // MPD
            if dep["type"] == "FS":
                c = fin[j] if (r.get("milestone") or d == 0 or rows[j].get("milestone") or not int(rows[j].get("days", 1))) else add_workdays(fin[j], 1)
            elif dep["type"] == "FF":
                f_min = fin[j] if f_min is None else max(f_min, fin[j]); c = start
            else:
                c = st[j]
            s = max(s, next_workday(add_workdays(c, lag) if lag > 0 else c))
        if f_min is not None:
            s = max(s, add_workdays(f_min, -(max(d, 1) - 1)))
        if r.get("constraint") in ("SNET", "MSO") and r.get("constraintDate"):
            s = max(s, next_workday(date.fromisoformat(r["constraintDate"])))
        st[i] = s
        fin[i] = add_workdays(s, d - 1) if d else s

    out = []
    for i, (t, r) in enumerate(zip(tasks, rows)):
        kids = [j for j in range(i + 1, len(rows)) if int(rows[j].get("level", 1)) > t["outlineLevel"] and all(int(rows[k].get("level", 1)) > t["outlineLevel"] for k in range(i + 1, j + 1))]
        if i in has_child:
            s = min(st[j] for j in kids if j in st); f = max(fin[j] for j in kids if j in fin)
            wd = sum(1 for n in range((f - s).days + 1) if (s + timedelta(days=n)).weekday() < 5)
            t.update(isSummary=True, isMilestone=False, start=iso(s), finish=iso(f, 17), durationMinutes=wd * MPD)
        else:
            d = max(0, int(r.get("days", 0 if r.get("milestone") else 1)))
            ms = bool(r.get("milestone")) or d == 0
            t.update(isSummary=False, isMilestone=ms, start=iso(st[i]), finish=iso(fin[i], 8 if ms else 17), durationMinutes=0 if ms else d * MPD)
        t["durationDays"] = round(t["durationMinutes"] / MPD, 2)
        t["percentComplete"] = max(0, min(100, int(r.get("percent", 0))))
        c = r.get("constraint", "ASAP")
        if c not in CONSTRAINTS: raise SystemExit(f"Unknown constraint '{c}'.")
        t["constraintType"] = {"ASAP": "AS_SOON_AS_POSSIBLE", "ALAP": "AS_LATE_AS_POSSIBLE"}.get(c, c)
        t["constraintDate"] = iso(date.fromisoformat(r["constraintDate"])) if c not in ("ASAP", "ALAP") else None
        t["deadline"] = iso(date.fromisoformat(r["deadline"]), 17) if r.get("deadline") else None
        if r.get("notes"): t["notes"] = r["notes"]
        if "optimistic" in r and "pessimistic" in r and not t["isSummary"]:
            t["optimisticDurationMinutes"] = int(r["optimistic"]) * MPD
            t["pessimisticDurationMinutes"] = int(r["pessimistic"]) * MPD
        out.append(t)

    assigns = []
    for i, r in enumerate(rows):
        if i in has_child: continue
        for n in ([r["owner"]] if r.get("owner") else []) + list(r.get("resources", [])):
            assigns.append({"taskId": str(i + 1), "resourceId": names[n], "units": 1, "workMinutes": out[i]["durationMinutes"], "start": out[i]["start"], "finish": out[i]["finish"]})

    risks = []
    for k, x in enumerate(spec.get("risks", [])):
        e = {"id": f"r{k+1}", "kind": x.get("kind", "risk"), "title": x["title"], "status": x.get("status", "open")}
        for f in ("description", "owner", "response", "probability", "impact"):
            if f in x: e[f] = x[f]
        if x.get("tasks"): e["taskIds"] = [str(keys[t] + 1) for t in x["tasks"]]
        risks.append(e)

    ends = [t["finish"] for t in out]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    project = {
        "meta": {"schemaVersion": "1.0", "source": "mspdi", "name": spec["name"], "projectStart": iso(start), "projectFinish": max(ends),
                 "defaultCalendarId": "1", "minutesPerDay": MPD, "minutesPerWeek": MPD * 5, "daysPerMonth": 20, "parsedAt": now,
                 **({"company": spec["company"]} if spec.get("company") else {})},
        "tasks": out, "dependencies": deps, "resources": res, "assignments": assigns, "milestones": [],
        "calendars": [{"id": "1", "name": "Standard", "baseCalendarId": None,
                       "weeklyWorkingMinutes": [[], *[[[480, 720], [780, 1020]]] * 5, []], "exceptions": []}],
        "baselines": [], "risks": risks,
    }
    doc = {"version": 1, "id": str(uuid.uuid4()).upper(), "name": spec["name"], "project": project}
    json.dump(doc, open(out_path, "w"), indent=1)
    print(f"Wrote {out_path}: {sum(1 for t in out if not t['isSummary'])} tasks, {len(deps)} links, {len(res)} resources")

if __name__ == "__main__":
    if len(sys.argv) != 3: raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])

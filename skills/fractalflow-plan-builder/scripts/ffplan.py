#!/usr/bin/env python3
"""ffplan: check, build and read FractalFlow .ffplan schedules.

  ffplan.py check   SPEC_OR_PLAN [--tasks] [--what-if KEY:+N ...] [--finish-by YYYY-MM-DD]
  ffplan.py build   SPEC.json OUT.ffplan
  ffplan.py extract PLAN.ffplan SPEC.json

check    reads a plan spec (JSON) or a .ffplan file and prints dates, the driving path,
         deadlines and schedule-quality findings. It changes nothing.
build    writes a .ffplan from a spec. A spec made by "extract" is merged back onto the
         original file, so anything the spec does not show is carried through untouched.
extract  writes an editable spec from an existing .ffplan.

The tool reads the file it is given and, for a spec made by "extract", the original plan
named in that spec's basedOn field. It writes only the output file it is given; the first
"build" of a new plan also adds one planId line to the spec. It makes no network requests
and starts no other programs. Standard library only; Python 3.8 or later.

Dates are worked out at whole-day precision with the critical path method. FractalFlow
recalculates a plan when it opens the file, and its dates are the ones that count.
"""
import argparse
import bisect
import copy
import difflib
import json
import os
import re
import sys
import uuid
from datetime import date, datetime, timezone

MPD = 480                 # working minutes in one working day
DAY = 1440                # minutes in one calendar day
AM, PM = 0, 1             # the two instants this tool reasons about: start of work, end of work
CLOCK = ("08:00", "17:00")
CLOCK_MIN = (8 * 60, 17 * 60)
STD_HOURS = [[480, 720], [780, 1020]]                             # 08:00-12:00 and 13:00-17:00
FILE_WEEK = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")     # order used in the file
PY_WEEK = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")       # order of date.weekday()
LINK_TYPES = ("FS", "SS", "FF", "SF")
LONG = {"ASAP": "AS_SOON_AS_POSSIBLE", "ALAP": "AS_LATE_AS_POSSIBLE",
        "MSO": "MUST_START_ON", "MFO": "MUST_FINISH_ON",
        "SNET": "START_NO_EARLIER_THAN", "SNLT": "START_NO_LATER_THAN",
        "FNET": "FINISH_NO_EARLIER_THAN", "FNLT": "FINISH_NO_LATER_THAN"}
SHORT = {re.sub("[^A-Z]", "", v): k for k, v in LONG.items()}
SHORT.update({k: k for k in LONG})
START_KIND = ("SNET", "SNLT", "MSO")      # dated at the start of the day; the rest at the end
HARD = ("MSO", "MFO", "SNLT", "FNLT")
RAID_KINDS = ("risk", "assumption", "issue", "dependency", "decision")
RAID_STATUS = ("open", "mitigating", "closed", "realized")

# Thresholds used by the quality checks (common scheduling practice, DCMA 14-point style).
HIGH_FLOAT = 44           # working days
HIGH_DURATION = 44        # working days
SHARE = 5.0               # percent of tasks or links
FS_SHARE = 90.0           # percent of links that should be finish-to-start
PLACEHOLDER = re.compile(r"^(tbd|tba|todo|misc|miscellaneous|other|others|various|stuff|etc|task|new task|untitled)\.?$", re.I)
MARGIN_WORDS = re.compile(r"contingency|buffer|margin|reserve|allowance|float", re.I)


SPEC_KEYS = ("name", "start", "statusDate", "calendar", "tasks", "risks", "company", "planId", "basedOn")
ROW_KEYS = ("id", "key", "name", "level", "days", "minutes", "elapsed", "milestone", "pred", "owner", "resources",
            "percent", "actualStart", "actualFinish", "remaining", "deadline", "constraint", "constraintDate",
            "optimistic", "pessimistic", "notes")
RISK_KEYS = ("id", "kind", "title", "description", "probability", "impact", "owner", "status", "response", "tasks", "impactDays")
PHASE_KEYS = ("id", "key", "name", "level", "notes")      # all a phase row uses


def unknown_keys(obj, allowed, where, err):
    """Misspelt field names would otherwise be dropped without a word, links included."""
    for k in obj:
        if k not in allowed:
            near = difflib.get_close_matches(str(k), allowed, 1)
            err("spec", f"{where}: '{k}' is not a field this tool knows" + (f". Did you mean '{near[0]}'?" if near else "."))


class Fail(Exception):
    """A problem that stops the command, with a message written for the reader."""


class Finding:
    __slots__ = ("sev", "code", "text", "rows", "fix")

    def __init__(self, sev, code, text, rows=(), fix=""):
        self.sev, self.code, self.text, self.rows, self.fix = sev, code, text, list(rows), fix


# ---------------------------------------------------------------- dates and instants

def parse_day(value, what):
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError:
        raise Fail(f"{what}: '{value}' is not a date. Use YYYY-MM-DD.")


def stamp(value, slot, what):
    """A spec date or a file timestamp -> (iso text, instant). The instant is None when the
    time of day is not one of the two this tool reasons about."""
    text = str(value).strip()
    d = parse_day(text, what)
    if len(text) <= 10:
        return (f"{d.isoformat()}T{CLOCK[slot]}:00.000Z", (d.toordinal(), slot))
    clock = text[11:19] if len(text) >= 19 else text[11:16] + ":00"
    inst = None
    if clock == CLOCK[AM] + ":00":
        inst = (d.toordinal(), AM)
    elif clock == CLOCK[PM] + ":00":
        inst = (d.toordinal(), PM)
    return (text, inst)


def short(iso_text, slot):
    """The shortest spec form of a file timestamp: a bare date when the time is the usual one."""
    text = str(iso_text)
    if text[11:19] == CLOCK[slot] + ":00":
        return text[:10]
    return text


def same_stamp(a, b):
    if a is None or b is None:
        return a is None and b is None
    return a[0][:19] == b[0][:19]


def iso(inst):
    return f"{date.fromordinal(inst[0]).isoformat()}T{CLOCK[inst[1]]}:00.000Z"


def to_day(inst):
    return date.fromordinal(inst[0])


def clock_minutes(inst):
    return inst[0] * DAY + CLOCK_MIN[inst[1]]


def show(d):
    return d.strftime("%a %Y-%m-%d") if d else "?"


def days_text(x, unit="d"):
    if x is None:
        return "?"
    if abs(x - round(x)) < 1e-9:
        return f"{int(round(x))}{unit}"
    return f"{x:.1f}{unit}"


# ---------------------------------------------------------------- working calendar

class Calendar:
    """Working days of the week plus whole-day holidays. Days are date ordinals."""

    def __init__(self, workdays=(0, 1, 2, 3, 4), holidays=()):
        self.workdays = frozenset(workdays)            # date.weekday() numbers, Monday = 0
        self.holidays = frozenset(holidays)
        self._hol = sorted(o for o in self.holidays if (o - 1) % 7 in self.workdays)

    def is_work(self, o):
        return (o - 1) % 7 in self.workdays and o not in self.holidays

    def next_work(self, o):
        while not self.is_work(o):
            o += 1
        return o

    def prev_work(self, o):
        while not self.is_work(o):
            o -= 1
        return o

    def count(self, lo, hi):
        """Working days d with lo <= d <= hi."""
        if hi < lo:
            return 0
        full, rem = divmod(hi - lo + 1, 7)
        n = full * len(self.workdays) + sum(1 for o in range(lo, lo + rem) if (o - 1) % 7 in self.workdays)
        return n - (bisect.bisect_right(self._hol, hi) - bisect.bisect_left(self._hol, lo))

    def between(self, a, b):
        """Signed working days between two instants."""
        da = a[0] if a[1] == PM else a[0] - 1
        db = b[0] if b[1] == PM else b[0] - 1
        return self.count(da + 1, db) if db >= da else -self.count(db + 1, da)

    def add(self, inst, n):
        """The end of the n-th working day at or after an instant (n >= 1)."""
        d = self.next_work(inst[0] if inst[1] == AM else inst[0] + 1)
        for _ in range(n - 1):
            d = self.next_work(d + 1)
        return (d, PM)

    def sub(self, inst, n):
        """The start of the n-th working day at or before an instant (n >= 1)."""
        d = self.prev_work(inst[0] if inst[1] == PM else inst[0] - 1)
        for _ in range(n - 1):
            d = self.prev_work(d - 1)
        return (d, AM)

    def shift(self, inst, n):
        return self.add(inst, n) if n > 0 else self.sub(inst, -n) if n < 0 else inst

    def roll(self, inst):
        """The first start of a working day at or after an instant."""
        return (self.next_work(inst[0] if inst[1] == AM else inst[0] + 1), AM)

    def spec(self):
        """The spec form, or None for a plain Monday to Friday week with no holidays."""
        if self.workdays == frozenset((0, 1, 2, 3, 4)) and not self.holidays:
            return None
        out = {"workdays": [PY_WEEK[i] for i in sorted(self.workdays)]}
        hol, run = [], []
        for o in sorted(self.holidays) + [None]:
            if run and (o is None or o != run[-1] + 1):
                a, b = date.fromordinal(run[0]).isoformat(), date.fromordinal(run[-1]).isoformat()
                hol.append(a if a == b else {"from": a, "to": b})
                run = []
            if o is not None:
                run.append(o)
        if hol:
            out["holidays"] = hol
        return out

    def file(self):
        week = [copy.deepcopy(STD_HOURS) if (i - 1) % 7 in self.workdays else [] for i in range(7)]
        exc, run = [], []
        for o in sorted(self.holidays) + [None]:
            if run and (o is None or o != run[-1] + 1):
                exc.append({"start": date.fromordinal(run[0]).isoformat() + "T00:00:00.000Z",
                            "finish": date.fromordinal(run[-1] + 1).isoformat() + "T00:00:00.000Z",
                            "working": False})
                run = []
            if o is not None:
                run.append(o)
        return week, exc


def calendar_from_spec(c, err):
    if c is None:
        return Calendar()
    if not isinstance(c, dict):
        err("calendar", "calendar must be an object with workdays and holidays.")
        return Calendar()
    days = set()
    for name in c.get("workdays", ["Mon", "Tue", "Wed", "Thu", "Fri"]):
        k = str(name).strip()[:3].title()
        if k not in PY_WEEK:
            err("calendar", f"calendar.workdays: '{name}' is not a day of the week.")
        else:
            days.add(PY_WEEK.index(k))
    if not days:
        err("calendar", "calendar.workdays needs at least one working day.")
        days = {0, 1, 2, 3, 4}
    hol = set()
    for h in c.get("holidays", []):
        try:
            if isinstance(h, dict):
                a = parse_day(h.get("from"), "calendar.holidays")
                b = parse_day(h.get("to", h.get("from")), "calendar.holidays")
            else:
                a = b = parse_day(h, "calendar.holidays")
        except Fail as e:
            err("calendar", str(e))
            continue
        if b < a or (b - a).days > 400:
            err("calendar", f"calendar.holidays: the range {a} to {b} is not valid.")
            continue
        hol.update(range(a.toordinal(), b.toordinal() + 1))
    return Calendar(days, hol)


def calendar_from_file(c):
    """A Calendar for a calendar object in a file, or None when it has working hours or
    exceptions this tool does not model."""
    week = c.get("weeklyWorkingMinutes") or []
    if len(week) != 7:
        return None
    days = set()
    for i, windows in enumerate(week):
        if not windows:
            continue
        if [list(w) for w in windows] != STD_HOURS:
            return None
        days.add((i - 1) % 7)
    if not days:
        return None
    hol = set()
    for e in c.get("exceptions") or []:
        s, f = str(e.get("start", "")), str(e.get("finish", ""))
        if e.get("working") or s[11:19] != "00:00:00" or f[11:19] != "00:00:00":
            return None
        try:
            a, b = date.fromisoformat(s[:10]).toordinal(), date.fromisoformat(f[:10]).toordinal()
        except ValueError:
            return None
        if b - a > 4000:
            return None
        hol.update(range(a, b))
    return Calendar(days, hol)


# ---------------------------------------------------------------- the plan model

class Row:
    """One line of the outline: a phase (summary) or a task or milestone (leaf)."""

    def __init__(self):
        self.idx = 0
        self.spec = {}
        self.key = ""
        self.id = None            # task id in the original file, when there is one
        self.base = None          # the task object in the original file
        self.was = None           # the fields of that task as the spec first showed them
        self.was_links = None
        self.level = 1
        self.outline = ""
        self.parent = None
        self.summary = False
        self.links = []           # incoming
        self.outs = []            # outgoing
        self.name = ""
        self.minutes = 0
        self.elapsed = False
        self.milestone = False
        self.n = None             # duration in whole days, when it is whole
        self.people = ()
        self.percent = 0
        self.a_start = None
        self.a_finish = None
        self.deadline = None
        self.ctype = "ASAP"
        self.cdate = None
        self.opt = None
        self.pess = None
        self.notes = ""
        self.fixed = None         # (start, finish) instants of a finished task with no actual dates

    @property
    def label(self):
        return f"{self.outline} {self.name}".strip()

    @property
    def done(self):
        return self.percent >= 100

    @property
    def started(self):
        return self.a_start is not None and not self.done

    @property
    def work_days(self):
        """Duration in working days; a calendar-day task counts five sevenths."""
        if self.summary:
            return 0.0
        return self.minutes / DAY * 5 / 7 if self.elapsed else self.minutes / MPD


class Link:
    __slots__ = ("pred", "succ", "type", "lag", "pct", "base")

    def __init__(self, pred, succ, kind, lag, pct=None, base=None):
        self.pred, self.succ, self.type, self.lag, self.pct, self.base = pred, succ, kind, lag, pct, base

    @property
    def ident(self):
        return (self.type, self.lag, self.pct)


class Plan:
    def __init__(self):
        self.name = "Plan"
        self.spec = {}
        self.start = None             # instant
        self.status = None            # stamp
        self.calendar = Calendar()
        self.cal_known = True         # False when the original calendar is one this tool cannot model
        self.rows = []
        self.links = []
        self.risks = []
        self.findings = []
        self.unsupported = []         # reasons the tool does not work out dates itself
        self.order = []
        self.base = None              # the original document, when the spec came from a file
        self.saved = None             # dates saved in the original file by FractalFlow
        self.plan_id = None

    @property
    def errors(self):
        return [f for f in self.findings if f.sev == "ERROR"]

    @property
    def leaves(self):
        return [r for r in self.rows if not r.summary]

    def skip(self, reason):
        if reason not in self.unsupported:
            self.unsupported.append(reason)


def canon_constraint(value):
    if value in (None, ""):
        return "ASAP"
    return SHORT.get(re.sub("[^A-Z]", "", str(value).upper()))


LAG_RE = re.compile(r"\s*([+-])\s*(\d+)\s*d?\s*$", re.I)
TYPE_RE = re.compile(r"\s+(FS|SS|FF|SF)\s*$", re.I)


def parse_link(item, keys):
    """A predecessor entry -> (key, type, lag minutes, lag percent).

    Text form: a task key, then an optional link type and an optional lag in working days,
    for example "design", "design SS", "design FS+2d" or "design-2d". Keys may themselves
    contain hyphens and digits, so a whole entry that is a key always wins."""
    if isinstance(item, dict):
        key = str(item.get("task", item.get("key", ""))).strip()
        kind = str(item.get("type", "FS")).upper()
        if kind not in LINK_TYPES:
            raise Fail(f"'{kind}' is not a link type. Use FS, SS, FF or SF.")
        try:
            lag = int(item["lagMinutes"]) if "lagMinutes" in item else int(round(float(item.get("lag", 0)) * MPD))
        except (TypeError, ValueError):
            raise Fail("the lag is not a number.")
        return key, kind, lag, item.get("lagPercent")
    text = str(item).strip()

    def keyed(part):
        part = part.strip()
        if part in keys:
            return part, "FS"
        m = TYPE_RE.search(part)
        if m and part[:m.start()].strip() in keys:
            return part[:m.start()].strip(), m.group(1).upper()
        return None

    hit = keyed(text)
    if hit:
        return hit[0], hit[1], 0, None
    m = LAG_RE.search(text)
    if m:
        hit = keyed(text[:m.start()])
        if hit:
            return hit[0], hit[1], int(m.group(2)) * (-1 if m.group(1) == "-" else 1) * MPD, None
    raise Fail(f"'{text}' does not name a task in the plan. Write a task key, then an optional link "
               f"type and lag, for example 'design', 'design SS' or 'design FS+2d'.")


def read_fields(s, summary, err, label):
    """Normalise the fields of one row. Used for spec rows and for rows read from a file."""
    o = {"name": str(s.get("name", "")).strip(), "elapsed": bool(s.get("elapsed")) and not summary}
    unit = DAY if o["elapsed"] else MPD
    minutes = 0
    if not summary:
        try:
            if "minutes" in s:
                minutes = int(s["minutes"])
            elif "days" in s and s["days"] is not None:
                minutes = int(round(float(s["days"]) * unit))
                if s.get("milestone") and minutes:
                    err("duration", f"{label}: a milestone has no duration. Remove days or milestone.")
            elif s.get("milestone"):
                minutes = 0
            else:
                err("duration", f"{label}: give days (working days) or mark it as a milestone.")
                minutes = unit
        except (TypeError, ValueError):
            err("duration", f"{label}: the duration is not a number.")
            minutes = unit
        if minutes < 0:
            err("duration", f"{label}: the duration cannot be negative.")
            minutes = unit
    o["minutes"] = minutes
    o["milestone"] = (not summary) and minutes == 0
    people = []
    if s.get("owner"):
        people.append(str(s["owner"]).strip())
    extra = s.get("resources") or []
    if isinstance(extra, str):
        extra = [extra]
    people += [str(x).strip() for x in extra if str(x).strip()]
    o["people"] = tuple(dict.fromkeys(p for p in people if p))
    try:
        pc = float(s.get("percent", 0) or 0)
    except (TypeError, ValueError):
        err("progress", f"{label}: percent is not a number.")
        pc = 0
    if pc < 0 or pc > 100:
        err("progress", f"{label}: percent must be between 0 and 100.")
        pc = min(100, max(0, pc))
    o["percent"] = int(pc) if pc == int(pc) else pc
    for field, name, slot in (("a_start", "actualStart", AM), ("a_finish", "actualFinish", PM), ("deadline", "deadline", PM)):
        o[field] = None
        if s.get(name):
            try:
                o[field] = stamp(s[name], slot, f"{label} {name}")
            except Fail as e:
                err("date", str(e))
    if o["milestone"] and (o["a_start"] or o["a_finish"]):
        o["a_start"] = o["a_finish"] = o["a_finish"] or o["a_start"]      # a milestone happens at one instant
    c = canon_constraint(s.get("constraint"))
    if c is None:
        err("constraint", f"{label}: '{s.get('constraint')}' is not a constraint. Use SNET, SNLT, FNET, FNLT, MSO or MFO.")
        c = "ASAP"
    o["ctype"], o["cdate"] = c, None
    if s.get("constraintDate") and c not in ("ASAP", "ALAP"):
        try:
            o["cdate"] = stamp(s["constraintDate"], AM if c in START_KIND else PM, f"{label} constraintDate")
        except Fail as e:
            err("date", str(e))
    for field, name in (("opt", "optimistic"), ("pess", "pessimistic")):
        o[field] = None
        if s.get(name) is not None and not summary:
            try:
                o[field] = int(round(float(s[name]) * unit))      # same unit as the duration
            except (TypeError, ValueError):
                err("estimate", f"{label}: {name} is not a number.")
    o["notes"] = str(s.get("notes") or "")
    return o


FIELD_GROUPS = {
    "name": ("name",), "notes": ("notes",), "duration": ("minutes", "elapsed"),
    "people": ("people",), "progress": ("percent", "a_start", "a_finish"),
    "deadline": ("deadline",), "constraint": ("ctype", "cdate"), "estimate": ("opt", "pess"),
}


def changed_groups(row):
    """Which groups of fields differ from the original file (all of them for a new row)."""
    if row.base is None or row.was is None:
        return set(FIELD_GROUPS)
    out = set()
    for group, fields in FIELD_GROUPS.items():
        for f in fields:
            a, b = getattr(row, f), row.was[f]
            same = same_stamp(a, b) if f in ("a_start", "a_finish", "deadline", "cdate") else a == b
            if not same:
                out.add(group)
    return out


def plan_from_spec(spec, base=None, saved=False):
    """Build the model from a spec. Problems are collected as findings, not raised."""
    plan = Plan()
    plan.spec, plan.base = spec, base
    F = plan.findings

    def err(code, text, rows=(), fix=""):
        F.append(Finding("ERROR", code, text, rows, fix))

    unknown_keys(spec, SPEC_KEYS, "The spec", err)
    plan.name = str(spec.get("name") or "").strip()
    if not plan.name:
        err("spec", "The spec needs a name.")
        plan.name = "Plan"
    plan.plan_id = spec.get("planId") or (base or {}).get("id")
    base_meta = ((base or {}).get("project") or {}).get("meta") or {}

    # Calendar. A spec without one keeps the original file's calendar.
    if "calendar" in spec or base is None:
        plan.calendar = calendar_from_spec(spec.get("calendar"), err)
    else:
        cal = base_default_calendar(base)
        known = calendar_from_file(cal) if cal else None
        if known is None:
            plan.cal_known = False
            plan.skip("working hours or calendar exceptions this tool does not model")
        else:
            plan.calendar = known

    try:
        raw = spec.get("start") or base_meta.get("projectStart")
        if not raw:
            raise Fail("The spec needs a start date (YYYY-MM-DD).")
        st = stamp(raw, AM, "start")
        if st[1] is None:
            plan.skip("a project start that is not at the start of a working day")
            plan.start = plan.calendar.roll((parse_day(raw, "start").toordinal(), AM))
        else:
            plan.start = plan.calendar.roll((st[1][0], AM)) if plan.cal_known else st[1]
    except Fail as e:
        err("spec", str(e))
        plan.start = plan.calendar.roll((date.today().toordinal(), AM))
    if spec.get("statusDate"):
        try:
            plan.status = stamp(spec["statusDate"], PM, "statusDate")
        except Fail as e:
            err("date", str(e))

    raw_rows = spec.get("tasks")
    if not isinstance(raw_rows, list) or not raw_rows:
        err("spec", "The spec has no tasks.")
        return plan
    base_tasks = {str(t.get("id")): t for t in ((base or {}).get("project") or {}).get("tasks", [])}
    views = {}
    if base is not None:
        views = {str(v["id"]): v for v in spec_from_doc(base)["tasks"]}

    # Outline.
    rows, keys, ids, counters, prev = [], {}, set(), [], 0
    for i, s in enumerate(raw_rows):
        r = Row()
        r.idx, r.spec = i, s if isinstance(s, dict) else {}
        if not isinstance(s, dict):
            err("spec", f"Task {i + 1} is not an object.")
        r.key = str(r.spec.get("key", i + 1)).strip()
        if r.key in keys:
            err("key", f"The key '{r.key}' is used by more than one task. Keys must be unique.")
        keys.setdefault(r.key, i)
        if r.spec.get("id") is not None and str(r.spec["id"]) in base_tasks:
            r.id = str(r.spec["id"])
            if r.id in ids:
                err("key", f"The id '{r.id}' appears on more than one task.")
                r.id = None
            else:
                ids.add(r.id)
                r.base = base_tasks[r.id]
        try:
            r.level = max(1, int(r.spec.get("level", 1)))
        except (TypeError, ValueError):
            r.level = 1
            err("outline", f"Task '{r.spec.get('name', r.key)}': level must be a whole number.")
        if r.level > prev + 1:
            if r.base is None:
                err("outline", f"Task '{r.spec.get('name', r.key)}' is at level {r.level} right after level {prev}. "
                               f"A task can be at most one level deeper than the row above it.")
            r.level = prev + 1
        prev = r.level
        counters = counters[:r.level] + [0] * (r.level - len(counters))
        counters[r.level - 1] += 1
        r.outline = ".".join(str(c) for c in counters)
        rows.append(r)
    stack = []
    for r in rows:
        while stack and stack[-1].level >= r.level:
            stack.pop()
        r.parent = stack[-1].idx if stack else None
        stack.append(r)
    for i, r in enumerate(rows):
        r.summary = i + 1 < len(rows) and rows[i + 1].level > r.level
    plan.rows = rows

    # Fields.
    for r in rows:
        label = f"Task '{r.spec.get('name') or r.key}'"
        unknown_keys(r.spec, ROW_KEYS, label, err)
        if not str(r.spec.get("name") or "").strip():
            err("spec", f"Row {r.idx + 1} (key '{r.key}') has no name.")
        r.__dict__.update(read_fields(r.spec, r.summary, err, label))
        if r.base is not None:
            v = views[r.id]
            was_summary = "days" not in v and "minutes" not in v and not v.get("milestone")
            r.was = read_fields(v, was_summary, lambda *a, **k: None, label)
            r.was_links = v.get("pred", [])
            if r.done and r.a_start is None and r.a_finish is None and not r.summary:
                try:
                    a, b = stamp(r.base.get("start"), AM, "start"), stamp(r.base.get("finish"), PM, "finish")
                    if a[1] and b[1]:
                        r.fixed = (a[1], b[1])
                    else:
                        plan.skip("finished tasks whose dates are not on whole days")
                except Fail:
                    plan.skip("finished tasks whose dates are not on whole days")
        if r.summary:
            extra = [k for k in r.spec if k not in PHASE_KEYS and k != "pred" and r.spec[k] not in (None, "", [], False)]
            if r.base is None and extra:
                F.append(Finding("WARN", "phase-field", f"{r.label} is a phase, so {', '.join(extra)} on it is ignored. A phase takes its "
                                 "dates from the tasks under it.", [r.idx], "Put these on a task or on the phase's closing milestone."))
            continue
        unit = DAY if r.elapsed else MPD
        r.n = r.minutes // unit
        if r.minutes % unit and r.base is None:
            err("duration", f"{label}: durations are whole days. Round up to the next whole day.")
        pinned = r.done and (r.fixed or (r.a_start and r.a_finish))       # dates are facts; length no longer matters
        if r.minutes % unit and not pinned:
            plan.skip("durations that are not whole days")
        if r.ctype == "ALAP":
            if r.base is None:
                err("constraint", f"{label}: as-late-as-possible is not supported in a spec. Leave the task "
                                  "as soon as possible, or give it a start-no-earlier-than date.")
            plan.skip("as-late-as-possible tasks")
        if r.ctype not in ("ASAP", "ALAP") and r.cdate is None:
            if r.base is None or "constraint" in changed_groups(r):
                err("constraint", f"{label}: constraint {r.ctype} needs a constraintDate.")
            else:
                r.ctype = "ASAP"      # the app treats a dated constraint with no date as none
        for st in (r.a_start, r.a_finish, r.deadline, r.cdate):
            if st is not None and st[1] is None:
                plan.skip("dates that carry a time of day other than 08:00 or 17:00")
        if r.cdate and r.cdate[1] and r.cdate[1][0] < plan.start[0]:
            if r.base is None or "constraint" in changed_groups(r):
                err("constraint", f"{label}: the constraint date {r.cdate[0][:10]} is before the project start. "
                                  "Move the project start, or drop the constraint.")
            plan.skip("constraint dates before the project start")
        if r.spec.get("remaining") is not None:
            # "How many days are left?" is the honest way to update a task that is under way:
            # the duration becomes the time already spent plus the time still needed.
            try:
                left = float(r.spec["remaining"])
            except (TypeError, ValueError):
                left = -1
            if left < 0 or left != int(left):
                err("progress", f"{label}: remaining must be a whole number of days.")
            elif r.done or not r.a_start or not r.a_start[1]:
                err("progress", f"{label}: remaining is for a task that has started and is not finished. Give actualStart.")
            elif not plan.status or not plan.status[1]:
                err("progress", f"{label}: remaining needs a statusDate at the top of the spec, the day progress was measured.")
            elif plan.status[1] < r.a_start[1]:
                err("progress", f"{label}: actualStart is after the status date.")
            elif left == 0:
                err("progress", f"{label}: nothing remaining means it is finished. Set percent to 100 with actualStart and actualFinish.")
            else:
                spent = (plan.status[1][0] - r.a_start[1][0]) if r.elapsed else max(0, plan.calendar.between(r.a_start[1], plan.status[1]))
                r.n = spent + int(left)
                r.minutes = r.n * unit
                r.percent = int(round(100.0 * spent / r.n))
        if r.a_finish and not r.done:
            err("progress", f"{label}: actualFinish is set, so percent must be 100.")
        if r.done and bool(r.a_start) != bool(r.a_finish) and (r.base is None or "progress" in changed_groups(r)):
            err("progress", f"{label}: a finished task needs both actualStart and actualFinish, or neither.")
        if r.milestone and 0 < r.percent < 100:
            err("progress", f"{label}: a milestone is either done (percent 100) or not (0).")
        if r.a_start and r.a_finish and r.a_start[1] and r.a_finish[1] and r.a_finish[1] < r.a_start[1]:
            err("progress", f"{label}: actualFinish is before actualStart.")
        b = r.base or {}
        if b.get("taskMode") == "manual":
            plan.skip("manually scheduled tasks")
        if b.get("active") is False:
            plan.skip("inactive tasks")
        if b.get("splits"):
            plan.skip("split tasks")
        if b.get("levelingDelayMinutes"):
            plan.skip("resource leveling delays")
        if b.get("calendarId") and str(b["calendarId"]) != str(base_meta.get("defaultCalendarId")):
            plan.skip("tasks on their own calendar")
        if r.started and r.base is not None and "progress" not in changed_groups(r) and "duration" not in changed_groups(r):
            eff = (b.get("actualDurationMinutes") or 0) + (b["remainingDurationMinutes"] if b.get("remainingDurationMinutes") is not None else r.minutes)
            if eff % unit:
                plan.skip("in-progress tasks with part-day remaining work")
            else:
                r.n = eff // unit
    if base_meta.get("scheduleFrom") == "finish":
        plan.skip("scheduling backward from the finish date")
    if base is not None:
        default = str(base_meta.get("defaultCalendarId"))
        if any(x.get("calendarId") and str(x["calendarId"]) != default for x in base["project"].get("resources", [])):
            plan.skip("resources on their own calendar")

    # Links.
    seen = set()
    for r in rows:
        items = r.spec.get("pred") or []
        if isinstance(items, (str, dict)):
            items = [items]
        old = {}
        if r.base is not None:
            for d in (base["project"].get("dependencies") or []):
                if str(d.get("successorId")) == r.id:
                    old[(str(d.get("predecessorId")), d.get("type"), d.get("lagMinutes", 0), d.get("lagPercent"))] = d
        for item in items:
            try:
                key, kind, lag, pct = parse_link(item, keys)
            except Fail as e:
                err("link", f"Task '{r.name}': {e}", [r.idx])
                continue
            if key not in keys:
                err("link", f"Task '{r.name}' names a predecessor '{key}' that is not in the plan.", [r.idx])
                continue
            p = rows[keys[key]]
            if p.idx == r.idx:
                err("link", f"Task '{r.name}' is linked to itself.", [r.idx])
                continue
            if (p.idx, r.idx) in seen:
                F.append(Finding("WARN", "duplicate-link", f"{r.label} lists {p.label} as a predecessor more than once. "
                                 "Only the first link is kept.", [r.idx]))
                continue
            seen.add((p.idx, r.idx))
            L = Link(p.idx, r.idx, kind, lag, pct, old.get((p.id, kind, lag, pct)) if p.id else None)
            plan.links.append(L)
            r.links.append(L)
            p.outs.append(L)
            fresh = L.base is None
            if p.summary or r.summary:
                if fresh:
                    err("link", f"The link from '{p.name}' to '{r.name}' involves a phase. Link the tasks "
                                "inside the phase instead, for example its last task or its closing milestone.", [r.idx])
                plan.skip("links on phases")
            if pct is not None:
                plan.skip("percentage lags")
            if lag % MPD:
                plan.skip("lags that are not whole days")
            elif lag and (r.elapsed or p.elapsed):
                if fresh:
                    err("link", f"The link from '{p.name}' to '{r.name}' has a lag next to a calendar-day task. "
                                "Put the extra wait in a task of its own instead of a lag.", [r.idx])
                plan.skip("lags next to calendar-day tasks")

    # Order, and loops.
    indeg = {r.idx: 0 for r in rows}
    for L in plan.links:
        indeg[L.succ] += 1
    ready = [r.idx for r in rows if indeg[r.idx] == 0]
    order, head = [], 0
    while head < len(ready):
        i = ready[head]
        head += 1
        order.append(i)
        for L in rows[i].outs:
            indeg[L.succ] -= 1
            if indeg[L.succ] == 0:
                ready.append(L.succ)
    if len(order) < len(rows):
        left = {i for i in indeg if indeg[i] > 0}
        loop, cur = [], min(left)
        while cur not in loop:
            loop.append(cur)
            cur = next(L.pred for L in rows[cur].links if L.pred in left)
        loop = loop[loop.index(cur):]
        chain = " > ".join(rows[i].name for i in reversed(loop + [cur]))
        err("loop", f"The links form a loop, so nothing can be scheduled: {chain}. Remove one of these links.", loop)
    plan.order = [i for i in order if not rows[i].summary]

    # Risks and other register entries.
    base_risks = {str(x.get("id")): x for x in ((base or {}).get("project") or {}).get("risks", []) or []}
    for k, x in enumerate(spec.get("risks") or []):
        if not isinstance(x, dict) or not str(x.get("title") or "").strip():
            err("risk", f"Risk {k + 1} needs a title.")
            continue
        unknown_keys(x, RISK_KEYS, f"Risk '{x['title']}'", err)
        kind = str(x.get("kind", "risk")).lower()
        status = str(x.get("status", "open")).lower()
        if kind not in RAID_KINDS:
            err("risk", f"Risk '{x['title']}': kind must be one of {', '.join(RAID_KINDS)}.")
            kind = "risk"
        if status not in RAID_STATUS:
            err("risk", f"Risk '{x['title']}': status must be one of {', '.join(RAID_STATUS)}.")
            status = "open"
        tasks = []
        for key in x.get("tasks") or []:
            if str(key) in keys:
                tasks.append(keys[str(key)])
            else:
                err("risk", f"Risk '{x['title']}' names a task '{key}' that is not in the plan.")
        for f in ("probability", "impact"):
            if x.get(f) is not None and x[f] not in (1, 2, 3, 4, 5):
                err("risk", f"Risk '{x['title']}': {f} must be a whole number from 1 to 5.")
        plan.risks.append({"id": str(x["id"]) if x.get("id") is not None and str(x["id"]) in base_risks else None,
                           "kind": kind, "status": status, "tasks": tasks, "spec": x,
                           "base": base_risks.get(str(x.get("id")))})

    if saved and base is not None and isinstance(base.get("cpm"), dict) and base["cpm"].get("tasks"):
        plan.saved = base["cpm"]
    return plan


def base_default_calendar(doc):
    P = doc.get("project") or {}
    default = str((P.get("meta") or {}).get("defaultCalendarId"))
    cals = P.get("calendars") or []
    for c in cals:
        if str(c.get("id")) == default:
            return c
    return cals[0] if cals else None


# ---------------------------------------------------------------- reading a .ffplan as a spec

def outline_sort_key(t):
    return [int(p) if p.isdigit() else 0 for p in str(t.get("outlineNumber", "")).split(".")]


def link_view(d, key_of):
    key = key_of.get(str(d.get("predecessorId")), str(d.get("predecessorId")))
    kind, lag = d.get("type", "FS"), int(d.get("lagMinutes", 0) or 0)
    if d.get("lagPercent") is not None or lag % MPD:
        v = {"task": key, "type": kind, "lagMinutes": lag}
        if d.get("lagPercent") is not None:
            v["lagPercent"] = d["lagPercent"]
        return v
    n = lag // MPD
    if kind == "FS" and n == 0:
        return key
    return f"{key} {kind}" + (f"{n:+d}d" if n else "")


def row_view(t, summary, links_in, people, key_of):
    v = {"id": str(t.get("id")), "key": key_of[str(t.get("id"))], "name": t.get("name", ""),
         "level": int(t.get("outlineLevel", 1) or 1)}
    if not summary:
        m = int(round(t.get("durationMinutes") or 0))
        elapsed = bool(t.get("durationIsElapsed"))
        unit = DAY if elapsed else MPD
        if m == 0:
            v["milestone"] = True
        elif m % unit == 0:
            v["days"] = m // unit
        else:
            v["minutes"] = m
        if elapsed and m:
            v["elapsed"] = True
    if links_in:
        v["pred"] = [link_view(d, key_of) for d in links_in]
    if people:
        v["owner"] = people[0]
        if len(people) > 1:
            v["resources"] = list(people[1:])
    if t.get("percentComplete"):
        v["percent"] = t["percentComplete"]
    if t.get("actualStart"):
        v["actualStart"] = short(t["actualStart"], AM)
    if t.get("actualFinish"):
        v["actualFinish"] = short(t["actualFinish"], PM)
    if t.get("deadline"):
        v["deadline"] = short(t["deadline"], PM)
    c = canon_constraint(t.get("constraintType")) or "ASAP"
    if c != "ASAP":
        v["constraint"] = c
        if t.get("constraintDate") and c != "ALAP":
            v["constraintDate"] = short(t["constraintDate"], AM if c in START_KIND else PM)
    if not summary:
        unit = DAY if t.get("durationIsElapsed") else MPD
        for name, field in (("optimistic", "optimisticDurationMinutes"), ("pessimistic", "pessimisticDurationMinutes")):
            if t.get(field) is not None:
                x = t[field] / unit
                v[name] = int(x) if x == int(x) else x
    if t.get("notes"):
        v["notes"] = t["notes"]
    return v


def risk_view(x, key_of):
    v = {"id": str(x.get("id")), "kind": x.get("kind", "risk"), "title": x.get("title", "")}
    for f in ("description", "probability", "impact", "owner"):
        if x.get(f) not in (None, ""):
            v[f] = x[f]
    v["status"] = x.get("status", "open")
    if x.get("response"):
        v["response"] = x["response"]
    if x.get("taskIds"):
        v["tasks"] = [key_of[str(i)] for i in x["taskIds"] if str(i) in key_of]
    if x.get("scheduleImpactMinutes"):
        d = x["scheduleImpactMinutes"] / MPD
        v["impactDays"] = int(d) if d == int(d) else d
    return v


def spec_from_doc(doc):
    """The editable view of a plan file. Anything not shown here stays in the file."""
    P = doc.get("project") or {}
    meta = P.get("meta") or {}
    tasks = sorted(P.get("tasks") or [], key=outline_sort_key)
    key_of = {str(t.get("id")): "t" + str(t.get("id")) for t in tasks}
    names = {str(r.get("id")): str(r.get("name") or "") for r in P.get("resources") or []}
    people, links_in = {}, {}
    for a in P.get("assignments") or []:
        n = names.get(str(a.get("resourceId")))
        if n and n not in people.setdefault(str(a.get("taskId")), []):
            people[str(a.get("taskId"))].append(n)
    for d in P.get("dependencies") or []:
        links_in.setdefault(str(d.get("successorId")), []).append(d)
    spec = {"name": doc.get("name") or meta.get("name") or "Plan"}
    if meta.get("projectStart"):
        spec["start"] = short(meta["projectStart"], AM)
    if meta.get("statusDate"):
        spec["statusDate"] = short(meta["statusDate"], PM)
    cal = base_default_calendar(doc)
    known = calendar_from_file(cal) if cal else None
    if known is not None and known.spec() is not None:
        spec["calendar"] = known.spec()
    rows = []
    for i, t in enumerate(tasks):
        level = int(t.get("outlineLevel", 1) or 1)
        summary = i + 1 < len(tasks) and int(tasks[i + 1].get("outlineLevel", 1) or 1) > level
        tid = str(t.get("id"))
        rows.append(row_view(t, summary, links_in.get(tid, []), people.get(tid, []), key_of))
    spec["tasks"] = rows
    if P.get("risks"):
        spec["risks"] = [risk_view(x, key_of) for x in P["risks"]]
    return spec


# ---------------------------------------------------------------- critical path dates

class Result:
    def __init__(self, source):
        self.source = source              # "tool" or "saved"
        self.start, self.finish = {}, {}  # row -> date
        self.es, self.ef = {}, {}         # row -> instant (tool only)
        self.tf = {}                      # row -> float in days (calendar days for calendar-day tasks)
        self.crit = {}
        self.why = {}                     # row -> ("start" | "pred" | "constraint" | "actual", link)
        self.feed = {}                    # row -> (latest bound set by a predecessor, that link), whatever won
        self.path = []                    # the chain of tasks that sets the finish date
        self.p_start = self.p_finish = None
        self.pf = None
        self.length = None                # working days from start to finish


def schedule(plan, days=None, start=None):
    """Forward and backward pass over the tasks. Returns None when the plan uses something
    this tool does not model; FractalFlow then works the dates out when it opens the file."""
    if plan.unsupported or plan.errors or not plan.order:
        return None
    cal, rows = plan.calendar, plan.rows
    t0 = start or plan.start
    res = Result("tool")
    ES, EF = res.es, res.ef

    def dur(r):
        return days[r.idx] if days and r.idx in days else r.n

    def fin(r, s, n):                     # finish of a task that starts at s
        if n == 0:
            return s
        return (s[0] + n, s[1]) if r.elapsed else cal.add(s, n)

    def beg(r, f, n):                     # start of a task that finishes at f
        if n == 0:
            return f
        return (f[0] - n, f[1]) if r.elapsed else cal.sub(f, n)

    for i in plan.order:
        r, n = rows[i], dur(rows[i])
        best, why = t0, ("start", None)
        for L in r.links:
            if rows[L.pred].summary:
                continue
            b = cal.shift(EF[L.pred] if L.type in ("FS", "FF") else ES[L.pred], L.lag // MPD)
            if L.type in ("FF", "SF"):
                b = beg(r, b, n)
            if i not in res.feed or b > res.feed[i][0]:
                res.feed[i] = (b, L)
            if b > best:
                best, why = b, ("pred", L)
        if r.cdate:
            b = None
            if r.ctype in ("SNET", "MSO"):
                b = r.cdate[1]
            elif r.ctype in ("FNET", "MFO"):
                b = beg(r, r.cdate[1], n)
            if b is not None and b > best:
                best, why = b, ("constraint", None)
        if r.a_start:
            best, why = r.a_start[1], ("actual", None)
        elif r.fixed:
            best, why = r.fixed[0], ("actual", None)
        elif not r.elapsed and n > 0:
            best = cal.roll(best)
        ES[i] = best
        if r.done and r.a_finish:
            EF[i] = r.a_finish[1]
        elif r.fixed:
            EF[i] = r.fixed[1]
        else:
            EF[i] = fin(r, best, n)
        res.why[i] = why

    res.pf = max(EF.values())
    LS, LF = {}, {}
    for i in reversed(plan.order):
        r, n = rows[i], dur(rows[i])
        if r.done or r.started:
            LS[i], LF[i] = ES[i], EF[i]
            res.tf[i], res.crit[i] = 0.0, r.started
            continue
        lf = res.pf
        for L in r.outs:
            if rows[L.succ].summary:
                continue
            b = cal.shift(LS[L.succ] if L.type in ("FS", "SS") else LF[L.succ], -(L.lag // MPD))
            if L.type in ("SS", "SF"):
                b = fin(r, b, n)
            if b < lf:
                lf = b
        if r.cdate and r.ctype in ("SNLT", "MSO"):
            lf = min(lf, fin(r, r.cdate[1], n))
        if r.cdate and r.ctype in ("FNLT", "MFO"):
            lf = min(lf, r.cdate[1])
        if r.deadline:
            lf = min(lf, r.deadline[1])
        LF[i], LS[i] = lf, beg(r, lf, n)
        if r.elapsed and n > 0:
            res.tf[i] = (clock_minutes(lf) - clock_minutes(EF[i])) / DAY
        else:
            res.tf[i] = float(cal.between(EF[i], lf))
        res.crit[i] = res.tf[i] <= 0

    for i in plan.order:
        res.start[i], res.finish[i] = to_day(ES[i]), to_day(EF[i])
    for r in reversed(rows):              # phases take the span of what is under them
        if r.summary:
            kids = [k.idx for k in rows if k.parent == r.idx and k.idx in ES]
            if kids:
                ES[r.idx], EF[r.idx] = min(ES[k] for k in kids), max(EF[k] for k in kids)
                res.start[r.idx], res.finish[r.idx] = to_day(ES[r.idx]), to_day(EF[r.idx])
    res.p_start, res.p_finish = to_day(t0), to_day(res.pf)
    res.length = cal.between(t0, res.pf)
    # The driving path: walk back from the last task through whatever set each start.
    ends = [i for i in plan.order if EF[i] == res.pf]
    cur = sorted(ends, key=lambda i: (not rows[i].done, len(rows[i].outs) == 0, i))[-1]
    while cur is not None:
        res.path.append(cur)
        w = res.why[cur]
        cur = w[1].pred if w[0] == "pred" else None
    res.path.reverse()
    return res


def saved_result(plan):
    """Dates FractalFlow saved in the file, in the same shape as the tool's own result."""
    cpm, rows = plan.saved, plan.rows
    res = Result("saved")
    by_id = {r.id: r for r in rows if r.id}
    for r in rows:
        b = r.base or {}
        c = (cpm.get("tasks") or {}).get(r.id) or {}
        try:
            res.start[r.idx] = date.fromisoformat(str(b.get("start"))[:10])
            res.finish[r.idx] = date.fromisoformat(str(b.get("finish"))[:10])
        except ValueError:
            continue
        if r.summary:
            continue
        tf = c.get("totalFloatMinutes")
        if tf is not None:
            res.tf[r.idx] = tf / (DAY if r.elapsed else MPD)
        res.crit[r.idx] = bool(c.get("isCritical"))
        drivers = [by_id[str(x)].idx for x in c.get("drivingPredecessorIds") or [] if str(x) in by_id]
        kind = {"predecessors": "pred", "constraint": "constraint", "actuals": "actual"}.get(c.get("esDeterminedBy"), "start")
        res.why[r.idx] = (kind, drivers)
    try:
        res.p_start = date.fromisoformat(str(cpm.get("projectStart"))[:10])
        res.p_finish = date.fromisoformat(str(cpm.get("projectFinish"))[:10])
    except ValueError:
        res.p_start = min(res.start.values(), default=None)
        res.p_finish = max(res.finish.values(), default=None)
    res.length = cpm.get("durationWorkingDays")
    res.path = [by_id[str(x)].idx for x in cpm.get("criticalPath") or [] if str(x) in by_id]
    return res


# ---------------------------------------------------------------- writing a .ffplan

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def progress_fields(t, r):
    """Progress is written so that actual plus remaining work equals the duration."""
    for k in ("actualStart", "actualFinish", "actualDurationMinutes", "remainingDurationMinutes"):
        t.pop(k, None)
    t["percentComplete"] = r.percent
    if r.a_start:
        t["actualStart"] = r.a_start[0]
    if r.done:
        if r.a_finish:
            t["actualFinish"] = r.a_finish[0]
        if r.a_start:
            t["actualDurationMinutes"], t["remainingDurationMinutes"] = t["durationMinutes"], 0
    elif r.a_start:
        done = int(round(t["durationMinutes"] * r.percent / 100.0))
        t["actualDurationMinutes"], t["remainingDurationMinutes"] = done, t["durationMinutes"] - done


def apply_fields(t, r, groups, plan):
    if "name" in groups:
        t["name"] = r.name
    if "notes" in groups:
        if r.notes:
            t["notes"] = r.notes
        else:
            t.pop("notes", None)
    if r.summary:
        return
    if "duration" in groups:
        t["durationMinutes"] = r.minutes
        t["isMilestone"] = r.milestone
        if r.elapsed:
            t["durationIsElapsed"] = True
        else:
            t.pop("durationIsElapsed", None)
        t.pop("mpxj", None)
    if "constraint" in groups:
        t["constraintType"] = LONG[r.ctype]
        t["constraintDate"] = r.cdate[0] if r.cdate else None
    if "deadline" in groups:
        t["deadline"] = r.deadline[0] if r.deadline else None
    if "estimate" in groups:
        for field, value in (("optimisticDurationMinutes", r.opt), ("pessimisticDurationMinutes", r.pess)):
            if value is None:
                t.pop(field, None)
            else:
                t[field] = value
    if "progress" in groups or ("duration" in groups and (r.a_start or r.percent)):
        if r.done and r.a_start and r.a_finish and r.a_start[1] and r.a_finish[1]:
            # A finished task takes the length it actually had.
            if r.elapsed:
                t["durationMinutes"] = max(0, clock_minutes(r.a_finish[1]) - clock_minutes(r.a_start[1]))
            elif not r.milestone and plan.cal_known:
                t["durationMinutes"] = max(1, plan.calendar.between(r.a_start[1], r.a_finish[1])) * MPD
        progress_fields(t, r)
    t["durationDays"] = round(t["durationMinutes"] / MPD, 2)


def build_doc(plan, res):
    """The plan as a .ffplan document. With an original file, only what changed is rewritten."""
    base, rows, cal = plan.base, plan.rows, plan.calendar
    doc = copy.deepcopy(base) if base else {"version": 1, "id": None, "name": plan.name, "project": {}}
    doc.pop("cpm", None)                  # the app recalculates when this is absent
    P = doc["project"]
    meta = P.setdefault("meta", {})
    old_tasks = {str(t.get("id")): t for t in P.get("tasks") or []}
    kept = {r.id for r in rows if r.id}
    used = set(old_tasks)
    nums = [int(x) for x in used if x.isdigit()]
    counter = [max(nums) + 1 if nums else 1]

    def fresh_id(taken, counter):
        while str(counter[0]) in taken:
            counter[0] += 1
        taken.add(str(counter[0]))
        return str(counter[0])

    ids = {}
    for r in rows:
        ids[r.idx] = r.id if r.id else fresh_id(used, counter)

    start_text = iso(plan.start)
    tasks = []
    for r in rows:
        if r.base is not None:
            t = old_tasks[r.id]
            groups = changed_groups(r)
            old_outline = str(t.get("outlineNumber"))
            if t.get("wbs") is not None and str(t["wbs"]) == old_outline:
                t["wbs"] = r.outline
        else:
            t = {"id": ids[r.idx], "outlineNumber": r.outline, "name": r.name, "outlineLevel": r.level,
                 "parentId": None, "isSummary": r.summary, "isMilestone": r.milestone,
                 "start": start_text, "finish": start_text if (r.milestone or r.summary) else iso((plan.start[0], PM)),
                 "durationMinutes": r.minutes, "durationDays": round(r.minutes / MPD, 2), "percentComplete": 0,
                 "constraintType": LONG["ASAP"], "constraintDate": None, "deadline": None}
            groups = set(FIELD_GROUPS)
        t["outlineNumber"], t["outlineLevel"] = r.outline, r.level
        t["parentId"] = ids[r.parent] if r.parent is not None else None
        t["isSummary"] = r.summary
        if r.summary:
            t["isMilestone"] = False
        apply_fields(t, r, groups, plan)
        if res is not None and res.source == "tool" and r.idx in res.es:
            t["start"], t["finish"] = iso(res.es[r.idx]), iso(res.ef[r.idx])
            if r.summary:
                t["durationMinutes"] = max(0, cal.between(res.es[r.idx], res.ef[r.idx])) * MPD
                t["durationDays"] = round(t["durationMinutes"] / MPD, 2)
        tasks.append(t)
    P["tasks"] = tasks

    # Links: an unchanged link keeps its original object and position.
    old_deps = P.get("dependencies") or []
    position = {id(d): k for k, d in enumerate(((base or {}).get("project") or {}).get("dependencies") or [])}
    deps = []
    for L in plan.links:
        if L.base is not None:
            deps.append((position.get(id(L.base), 0), 0, copy.deepcopy(L.base)))
        else:
            d = {"predecessorId": ids[L.pred], "successorId": ids[L.succ], "type": L.type, "lagMinutes": L.lag}
            if L.pct is not None:
                d["lagPercent"] = L.pct
            deps.append((len(old_deps), len(deps), d))
    P["dependencies"] = [d for _, _, d in sorted(deps, key=lambda x: (x[0], x[1]))]

    # People.
    resources = P.get("resources") or []
    by_name = {str(x.get("name")): str(x.get("id")) for x in resources}
    taken = {str(x.get("id")) for x in resources}
    rnums = [int(x) for x in taken if x.isdigit()]
    rcounter = [max(rnums) + 1 if rnums else 1]
    assignments = []
    rewrite = {r.id for r in rows if r.base is not None and "people" in changed_groups(r)}
    for a in P.get("assignments") or []:
        tid = str(a.get("taskId"))
        if tid in kept and tid not in rewrite:
            assignments.append(a)
    for r in rows:
        if r.summary or not r.people or (r.base is not None and r.id not in rewrite):
            continue
        t = tasks[r.idx]
        for name in r.people:
            if name not in by_name:
                by_name[name] = fresh_id(taken, rcounter)
                resources.append({"id": by_name[name], "name": name, "type": "work", "maxUnits": 1})
            assignments.append({"taskId": ids[r.idx], "resourceId": by_name[name], "units": 1,
                                "workMinutes": 0 if r.elapsed else t["durationMinutes"],
                                "start": t["start"], "finish": t["finish"]})
    P["resources"], P["assignments"] = resources, assignments

    # Register entries.
    if "risks" in plan.spec or base is None:
        taken_r = {str(x.get("id")) for x in P.get("risks") or []}
        k, out = 0, []
        for x in plan.risks:
            s = x["spec"]
            if x["base"] and s == risk_view(x["base"], {i: "t" + i for i in old_tasks}):
                out.append(copy.deepcopy(x["base"]))          # untouched entry: keep it exactly as it was
                continue
            e = copy.deepcopy(x["base"]) if x["base"] else {}
            if not x["base"]:
                k += 1
                while f"r{k}" in taken_r:
                    k += 1
                taken_r.add(f"r{k}")
                e["id"] = f"r{k}"
            e["kind"], e["title"], e["status"] = x["kind"], str(s["title"]).strip(), x["status"]
            for f in ("description", "probability", "impact", "owner", "response"):
                if s.get(f) not in (None, ""):
                    e[f] = s[f]
                else:
                    e.pop(f, None)
            if x["tasks"]:
                e["taskIds"] = [ids[i] for i in x["tasks"]]
            else:
                e.pop("taskIds", None)
            if s.get("impactDays"):
                e["scheduleImpactMinutes"] = int(round(float(s["impactDays"]) * MPD))
            else:
                e.pop("scheduleImpactMinutes", None)
            out.append(e)
        P["risks"] = out
    elif P.get("risks"):
        for e in P["risks"]:
            if e.get("taskIds"):
                e["taskIds"] = [i for i in e["taskIds"] if str(i) in kept]

    # Everything else that points at tasks loses the tasks that were removed.
    for b in P.get("baselines") or []:
        if isinstance(b.get("tasks"), dict):
            b["tasks"] = {k: v for k, v in b["tasks"].items() if str(k) in kept}
    if P.get("timeEntries"):
        P["timeEntries"] = [e for e in P["timeEntries"] if str(e.get("taskId")) in kept]
    P["milestones"] = []                  # rebuilt by the app from the tasks

    # Header and calendar.
    doc["name"] = meta["name"] = plan.name
    if base is None:
        week, exc = cal.file()
        meta.update({"schemaVersion": "1.0", "source": "mspdi", "projectStart": start_text,
                     "projectFinish": start_text, "defaultCalendarId": "1", "minutesPerDay": MPD,
                     "minutesPerWeek": MPD * len(cal.workdays),
                     "daysPerMonth": 20 if len(cal.workdays) == 5 else round(len(cal.workdays) * 52 / 12),
                     "parsedAt": now_iso()})
        P["calendars"] = [{"id": "1", "name": "Standard", "baseCalendarId": None,
                           "weeklyWorkingMinutes": week, "exceptions": exc}]
        P.setdefault("baselines", [])
        P.setdefault("risks", [])
        if plan.spec.get("company"):
            meta["company"] = str(plan.spec["company"])
        doc["id"] = plan.plan_id or str(uuid.uuid4()).upper()
    else:
        if "start" in plan.spec and not same_stamp(stamp(plan.spec["start"], AM, "start"), stamp(meta.get("projectStart"), AM, "start")):
            meta["projectStart"] = start_text
        if "calendar" in plan.spec and plan.cal_known:
            target = base_default_calendar(doc)
            known = calendar_from_file(target) if target else None
            if target is not None and (known is None or known.workdays != cal.workdays or known.holidays != cal.holidays):
                target["weeklyWorkingMinutes"], target["exceptions"] = cal.file()
                meta["minutesPerWeek"] = MPD * len(cal.workdays)
        if doc.pop("starterVersion", None) is not None:
            doc["id"] = str(uuid.uuid4()).upper()      # a plan made from a starter is a plan of its own
    if plan.status is not None:
        if not meta.get("statusDate") or not same_stamp(plan.status, stamp(meta["statusDate"], PM, "statusDate")):
            meta["statusDate"] = plan.status[0]
    elif "statusDate" not in plan.spec:
        if base is None:
            meta.pop("statusDate", None)
    if res is not None and res.source == "tool":
        meta["projectFinish"] = iso(res.pf)
    return doc


# ---------------------------------------------------------------- quality checks

def labels(plan, idxs, limit=8):
    idxs = list(dict.fromkeys(idxs))
    text = "; ".join(plan.rows[i].label for i in idxs[:limit])
    return text + (f"; and {len(idxs) - limit} more" if len(idxs) > limit else "")


def link_text(plan, L):
    n = L.lag // MPD if L.lag % MPD == 0 else None
    lag = "" if not L.lag else (f"{n:+d}d" if n is not None else f"{L.lag:+d}min")
    return f"{plan.rows[L.pred].label} > {plan.rows[L.succ].label} ({L.type}{lag})"


def latest_baseline(plan):
    bl = ((plan.base or {}).get("project") or {}).get("baselines") or []
    bl = [b for b in bl if isinstance(b.get("tasks"), dict) and b["tasks"]]
    return max(bl, key=lambda b: str(b.get("savedAt") or "")) if bl else None


def margin_days(plan, finish, due):
    """Working days from a finish date to a due date; negative when late. Calendar days when
    the plan's calendar is one this tool does not model."""
    a, b = finish.toordinal(), due.toordinal()
    if not plan.cal_known:
        return b - a
    return plan.calendar.count(a + 1, b) if b >= a else -plan.calendar.count(b + 1, a)


def run_checks(plan, res):
    """Findings (things to fix or to know) and measures (DCMA 14-point style)."""
    F, M = [], []
    rows, cal = plan.rows, plan.calendar
    leaves = plan.leaves
    todo = [r for r in leaves if not r.done]                  # still to do
    work = [r for r in todo if not r.milestone]               # still to do, with a duration
    links = [L for L in plan.links if not rows[L.succ].done]
    has = res is not None

    def warn(code, text, rs=(), fix=""):
        F.append(Finding("WARN", code, text, rs, fix))

    def note(code, text, rs=(), fix=""):
        F.append(Finding("NOTE", code, text, rs, fix))

    def measure(name, value, target, ok):
        M.append((name, value, target, "n/a" if ok is None else "ok" if ok else "review"))

    def share(part, whole):
        return 100.0 * len(part) / len(whole) if whole else 0.0

    # 1. Logic: every task should have something before it and something after it.
    no_pred = [r for r in todo if not r.links]
    no_succ = [r for r in todo if not r.outs]
    first = next((r for r in no_pred if r.milestone), no_pred[0] if no_pred else None)
    if has and no_succ:
        last = max(no_succ, key=lambda r: (res.finish.get(r.idx, date.min), r.milestone, r.idx))
    else:
        last = next((r for r in reversed(no_succ) if r.milestone), no_succ[-1] if no_succ else None)
    open_start = [r for r in no_pred if r is not first]
    open_end = [r for r in no_succ if r is not last]
    if open_start:
        warn("open-start", f"{len(open_start)} task(s) have no predecessor: {labels(plan, [r.idx for r in open_start])}.",
             [r.idx for r in open_start],
             "Link each one to the work or decision that lets it start. If it can start on day one, link it to the start milestone.")
    if open_end:
        warn("open-end", f"{len(open_end)} task(s) have no successor: {labels(plan, [r.idx for r in open_end])}.",
             [r.idx for r in open_end],
             "Link each one to what it enables, or to the finish milestone. A task nothing depends on can slip without the plan noticing.")
    loose = [r for r in work if r in open_start or r in open_end]
    measure("Missing logic", f"{len(loose)} of {len(work)} tasks ({share(loose, work):.0f}%)", f"at most {SHARE:.0f}%",
            share(loose, work) <= SHARE if work else None)
    if last is not None and not last.milestone:
        note("finish-milestone", f"The plan ends on a task ({last.label}), not a milestone.", [last.idx],
             "Add a finish milestone that the last tasks lead to, so the completion date has a name.")

    # 2 to 4. Leads, lags and link types.
    phase_links = [L for L in plan.links if rows[L.pred].summary or rows[L.succ].summary]
    if phase_links:
        warn("phase-link", f"{len(phase_links)} link(s) are on phases: " + "; ".join(link_text(plan, L) for L in phase_links[:5]) + ".",
             [L.succ for L in phase_links], "Link the tasks inside the phase instead. Links on phases hide what really drives the dates.")
    leads = [L for L in links if L.lag < 0]
    lags = [L for L in links if L.lag > 0]
    if leads:
        warn("lead", f"{len(leads)} link(s) use a negative lag: " + "; ".join(link_text(plan, L) for L in leads[:5]) + ".",
             [L.succ for L in leads],
             "Model the overlap directly: split the earlier task where the next one can begin, or use a start-to-start link with a positive lag.")
    measure("Leads (negative lags)", str(len(leads)), "0", len(leads) == 0 if links else None)
    lag_share = share(lags, links)
    if lags:
        text = f"{len(lags)} link(s) carry a lag: " + "; ".join(link_text(plan, L) for L in lags[:5]) + ("; and more" if len(lags) > 5 else "") + "."
        fix = "Turn each wait into a task with a name and an owner, using calendar days when the wait runs on the calendar, so the plan shows what it is waiting for."
        many = lag_share > SHARE and (len(links) >= 20 or lag_share > 30)
        (warn if many else note)("lag", text, [L.succ for L in lags], fix)
    measure("Lags", f"{len(lags)} of {len(links)} links ({lag_share:.0f}%)", f"at most {SHARE:.0f}%", lag_share <= SHARE if links else None)
    fs = [L for L in links if L.type == "FS"]
    fs_share = share(fs, links)
    if links and (fs_share < FS_SHARE and len(links) >= 20 or fs_share < 60):
        warn("link-mix", f"Only {fs_share:.0f}% of links are finish-to-start.", [],
             "Start-to-start and finish-to-finish links are harder to follow and to update. Keep them for work that truly runs in step.")
    sf = [L for L in links if L.type == "SF"]
    if sf:
        warn("start-to-finish", f"{len(sf)} start-to-finish link(s): " + "; ".join(link_text(plan, L) for L in sf[:5]) + ".",
             [L.succ for L in sf], "Start-to-finish is almost never what is meant. Check the direction of the link.")
    measure("Finish-to-start links", f"{fs_share:.0f}%" if links else "no links", f"at least {FS_SHARE:.0f}%", fs_share >= FS_SHARE if links else None)

    # 5. Constraints.
    hard = [r for r in todo if r.ctype in HARD]
    soft = [r for r in todo if r.ctype in ("SNET", "FNET")]
    hard_share = share(hard, todo)
    if hard:
        text = f"{len(hard)} task(s) are pinned by a hard constraint: " + "; ".join(f"{r.label} ({r.ctype})" for r in hard[:6]) + "."
        fix = "Use a deadline for a date you are aiming at. Keep hard constraints for dates the outside world truly fixes."
        (warn if hard_share > SHARE and len(hard) >= 3 else note)("hard-constraint", text, [r.idx for r in hard], fix)
    measure("Hard constraints", f"{len(hard)} of {len(todo)} ({hard_share:.0f}%)", f"at most {SHARE:.0f}%", hard_share <= SHARE if todo else None)
    silent = [r for r in hard + soft if not r.notes.strip()]
    if silent:
        note("constraint-reason", f"{len(silent)} constrained task(s) do not say why: {labels(plan, [r.idx for r in silent])}.",
             [r.idx for r in silent], "Put the reason and its source in the task notes.")
    if plan.cal_known:
        off = [r for r in todo if not r.elapsed and any(st and st[1] and not cal.is_work(st[1][0]) for st in (r.deadline, r.cdate))]
        if off:
            note("off-day-date", f"{len(off)} task(s) have a deadline or constraint on a non-working day: {labels(plan, [r.idx for r in off])}.",
                 [r.idx for r in off], "Check the date, or the calendar.")

    # 6 to 8. Float and long tasks.
    long_tasks = [r for r in work if r.work_days > HIGH_DURATION]
    long_share = share(long_tasks, work)
    if long_tasks:
        waits = [r for r in long_tasks if r.elapsed]
        text = f"{len(long_tasks)} task(s) run longer than {HIGH_DURATION} working days: {labels(plan, [r.idx for r in long_tasks])}."
        fix = ("Split long work into steps that can be checked off, each ending in something visible."
               + (" A long wait on someone else's clock is fine if the clock is real." if waits else ""))
        (warn if long_share > SHARE else note)("long-task", text, [r.idx for r in long_tasks], fix)
    high = neg = None
    if has:
        floats = [r for r in todo if r.idx in res.tf]
        high = [r for r in floats if not r.milestone and res.tf[r.idx] > HIGH_FLOAT]
        neg = [r for r in floats if res.tf[r.idx] < 0]
        high_share = share(high, work)
        if high:
            note("high-float", f"{len(high)} task(s) have more than {HIGH_FLOAT} days of float: {labels(plan, [r.idx for r in high])}.",
                 [r.idx for r in high],
                 "Either this is real freedom, as in a side workstream that only has to be ready by the end, or a successor is missing. Check what each task feeds.")
        measure("High float", f"{len(high)} of {len(work)} tasks ({high_share:.0f}%)", f"at most {SHARE:.0f}%", high_share <= SHARE if work else None)
        if neg:
            worst = min(res.tf[r.idx] for r in neg)
            warn("negative-float", f"{len(neg)} task(s) cannot meet a date they are held to (worst: {days_text(-worst)} late): "
                                   f"{labels(plan, [r.idx for r in sorted(neg, key=lambda r: res.tf[r.idx])])}.",
                 [r.idx for r in neg],
                 "Find the deadline or constraint behind it (see DEADLINES), then shorten or overlap work on that path, move the date, or cut scope.")
        measure("Negative float", f"{len(neg)} tasks", "0", len(neg) == 0)
    else:
        measure("High float", "not worked out", f"at most {SHARE:.0f}%", None)
        measure("Negative float", "not worked out", "0", None)
    measure("Long tasks", f"{len(long_tasks)} of {len(work)} tasks ({long_share:.0f}%)", f"at most {SHARE:.0f}%", long_share <= SHARE if work else None)

    # Deadlines.
    if has:
        missed = [(r, margin_days(plan, res.finish[r.idx], date.fromisoformat(r.deadline[0][:10])))
                  for r in todo if r.deadline and r.idx in res.finish]
        late = [(r, m) for r, m in missed if m < 0]
        tight = [(r, m) for r, m in missed if 0 <= m <= 2]
        if late:
            warn("deadline-missed", "Deadline(s) missed: " + "; ".join(f"{r.label} by {days_text(-m)}" for r, m in late[:8]) + ".",
                 [r.idx for r, _ in late], "Decide what gives: the date, the scope, or the way the work is done. Do not shorten estimates to make it fit.")
        if tight:
            note("deadline-tight", "Deadline(s) with two days of margin or less: " + "; ".join(f"{r.label} ({days_text(m)})" for r, m in tight[:8]) + ".",
                 [r.idx for r, _ in tight], "One slip on the path to it and the date is gone. Consider margin.")

    # 9 and 11, 14. Progress.
    status = plan.status[1] if plan.status else None
    any_progress = any(r.percent or r.a_start for r in leaves)
    invalid = []
    if status is None and any_progress:
        note("no-status-date", "The plan records progress but has no status date.", [],
             "Set statusDate to the day the progress was measured.")
    if status is not None:
        sday = to_day(status)
        future = [r for r in leaves for st in (r.a_start, r.a_finish) if st and st[1] and st[1] > status]
        if future:
            warn("actual-in-future", f"{len(set(r.idx for r in future))} task(s) have actual dates after the status date: {labels(plan, [r.idx for r in future])}.",
                 [r.idx for r in future], "An actual date is a fact. Check the dates or the status date.")
        invalid += future
        if has:
            due_by = sday if status[1] == PM else date.fromordinal(status[0] - 1)      # a morning status date has not had its day yet
            overdue = [r for r in todo if r.idx in res.finish and res.finish[r.idx] <= due_by and not r.milestone]
            running = [r for r in overdue if r.a_start]
            ready = lambda r: all(rows[L.pred].done for L in r.links)       # nothing upstream is holding it
            waiting = [r for r in todo if r.idx in res.start and res.start[r.idx] < sday and not r.a_start and not r.percent
                       and not r.milestone and ready(r)]
            if running:
                warn("overdue", f"{len(running)} task(s) under way were due to finish by the status date: {labels(plan, [r.idx for r in running])}.",
                     [r.idx for r in running],
                     "Ask how many working days each still needs and set remaining to that. Its finish, and everything after it, then moves to where it really is.")
            if waiting:
                warn("not-started", f"{len(waiting)} task(s) could have started by the status date and show no progress: {labels(plan, [r.idx for r in waiting])}.",
                     [r.idx for r in waiting],
                     "Record the start if it happened. If not, find out what is holding it and give it a start-no-earlier-than date for the day it can really begin.")
            invalid += overdue + [r for r in todo if r.idx in res.start and res.start[r.idx] < sday and not r.a_start and not r.percent and r not in overdue]
        measure("Invalid dates", f"{len(set(r.idx for r in invalid))} tasks", "0", not invalid)
        seq = [r for r in leaves if (r.a_start or r.done) and any(L.type == "FS" and not rows[L.pred].done for L in r.links) and r.percent]
        if seq:
            note("out-of-sequence", f"{len(seq)} task(s) started before a predecessor finished: {labels(plan, [r.idx for r in seq])}.",
                 [r.idx for r in seq], "The link may be softer than drawn. Decide whether it is a real dependency.")
        base_line = latest_baseline(plan)
        if base_line:
            due, done_n, missed_n = 0, 0, 0
            for r in leaves:
                b = base_line["tasks"].get(r.id) if r.id else None
                if not b or r.milestone:
                    continue
                try:
                    bf = date.fromisoformat(str(b.get("finish"))[:10])
                except ValueError:
                    continue
                if bf <= sday:
                    due += 1
                    late_done = r.done and r.a_finish and date.fromisoformat(r.a_finish[0][:10]) > bf
                    if not r.done or late_done:
                        missed_n += 1
                if r.done:
                    done_n += 1
            if due:
                measure("Missed tasks", f"{missed_n} of {due} due by the status date ({100.0 * missed_n / due:.0f}%)", f"at most {SHARE:.0f}%", 100.0 * missed_n / due <= SHARE)
                measure("Baseline execution index", f"{done_n / due:.2f}", "at least 0.95", done_n / due >= 0.95)
    else:
        measure("Invalid dates", "no status date", "0", None)
    half = [r for r in todo if 0 < r.percent < 100 and not r.a_start]
    if half:
        note("progress-no-start", f"{len(half)} task(s) show progress but no actual start: {labels(plan, [r.idx for r in half])}.",
             [r.idx for r in half], "Add actualStart so the plan holds the task where it really began.")

    # 10. Owners.
    unowned = [r for r in work if not r.people]
    owners = sorted({p for r in leaves for p in r.people})
    if work and not owners:
        note("no-owners", "No task has an owner.", [], "Name who is answerable for each task, even if it is the same person or team throughout.")
    elif unowned:
        warn("no-owner", f"{len(unowned)} task(s) have no owner: {labels(plan, [r.idx for r in unowned])}.", [r.idx for r in unowned],
             "Give every task one answerable owner.")
    measure("Tasks without an owner", f"{len(unowned)} of {len(work)}", "0", (not unowned) if work else None)

    # 12 and 13. Does the finish respond to the path, and how tight is it against its date.
    if has and res.source == "tool" and res.path:
        probe = next((i for i in res.path if not rows[i].done and not rows[i].started and rows[i].n), None)
        if probe is not None:
            moved = schedule(plan, days={probe: rows[probe].n + 600})
            ok = moved is not None and moved.pf > res.pf
            measure("Critical path test", "finish moves when the path slips" if ok else "finish does not move when the path slips", "moves", ok)
            if not ok:
                warn("path-broken", "Delaying work on the driving path does not move the finish date.", [probe],
                     "Something other than the work holds the end date, usually a constraint on the last task. Replace it with a deadline.")
        end = rows[res.path[-1]]
        target = end.deadline or (end.cdate if end.ctype in ("FNLT", "MFO") else None)
        if target and target[1]:
            origin = status if status and status > plan.start else plan.start
            length = cal.between(origin, res.pf)
            if length > 0:
                cpli = (length + cal.between(res.pf, target[1])) / length
                measure("Critical path length index", f"{cpli:.2f}", "at least 0.95", cpli >= 0.95)
    elif has and res.source == "saved":
        ok = bool(res.path) and res.finish.get(res.path[-1]) == res.p_finish
        measure("Critical path test", "path reaches the finish date" if ok else "path does not reach the finish date", "reaches", ok if res.path else None)

    # Names and shape.
    seen, dup_sib, dup_any = {}, [], []
    for r in rows:
        k = r.name.strip().lower()
        if (r.parent, k) in seen:
            dup_sib.append(r.idx)
        seen[(r.parent, k)] = r.idx
    names = {}
    for r in leaves:
        names.setdefault(r.name.strip().lower(), []).append(r.idx)
    dup_any = [i for v in names.values() if len(v) > 1 for i in v if i not in dup_sib]
    if dup_sib:
        warn("duplicate-name", f"Tasks with the same name in the same phase: {labels(plan, dup_sib)}.", dup_sib,
             "Make each name say what is different about it.")
    elif dup_any:
        note("repeated-name", f"{len(dup_any)} task(s) share a name with a task elsewhere in the plan: {labels(plan, dup_any)}.", dup_any,
             "In a list or a filter these will look identical. Add the thing they act on to the name.")
    vague = [r.idx for r in rows if PLACEHOLDER.match(r.name.strip())]
    if vague:
        warn("vague-name", f"Placeholder names: {labels(plan, vague)}.", vague, "Name the work: a verb and the thing it acts on.")
    single = [r.idx for r in rows if r.summary and sum(1 for k in rows if k.parent == r.idx) == 1]
    if single:
        note("single-child", f"Phase(s) with only one row under them: {labels(plan, single)}.", single, "Either add the other tasks or drop the phase level.")
    if max((r.level for r in rows), default=1) > 4:
        note("deep-outline", "The outline goes deeper than four levels.", [], "Three levels are enough for most plans: phase, work package, task.")
    milestones = [r for r in leaves if r.milestone]
    if len(work) > 15 and not any(r.summary for r in rows):
        note("flat-plan", "The plan has no phases.", [], "Group the tasks into phases so people can read it at a glance.")
    if len(work) > 15 and len(milestones) < 2:
        note("few-milestones", "The plan has fewer than two milestones.", [], "Add milestones for decisions, approvals, deliveries and the end of each phase.")

    # Estimates and risk.
    fresh = [r for r in work if not r.started]             # once a task is under way its range is history
    bad_range = [r.idx for r in fresh if (r.opt is not None and r.opt > r.minutes) or (r.pess is not None and r.pess < r.minutes)]
    if bad_range:
        warn("estimate-range", f"The optimistic to pessimistic range does not contain the duration: {labels(plan, bad_range)}.", bad_range,
             "Optimistic should be at or below the duration and pessimistic at or above it.")
    if has:
        blind = [r for r in fresh if res.crit.get(r.idx) and r.work_days >= 10 and r.opt is None and r.pess is None and not r.elapsed]
        if blind:
            note("no-range", f"{len(blind)} long task(s) on the critical path have no optimistic or pessimistic estimate: {labels(plan, [r.idx for r in blind], 5)}.",
                 [r.idx for r in blind], "Ask how short and how long each could run. The spread is what a risk simulation works from.")
        if len(work) >= 10 and all(res.crit.get(r.idx) for r in work):
            note("single-chain", "Every task is critical: the plan is one chain.", [],
                 "Check which tasks really wait on each other. Work that can run side by side shortens the plan and adds float.")
    merges = [r.idx for r in todo if len(r.links) >= 4]
    if merges:
        note("merge-point", f"Several paths meet at: {labels(plan, merges, 5)}.", merges,
             "Where many paths join, the chance that at least one is late is high. Consider margin before these points.")
    register = [x for x in plan.risks if x["kind"] == "risk" and x["status"] in ("open", "mitigating")]
    if len(work) >= 10 and not plan.risks:
        note("no-risks", "The plan lists no risks, assumptions or open decisions.", [], "Record the few things most likely to move the dates, each with an owner and a response.")
    gaps = [x["spec"].get("title") for x in register if not x["spec"].get("owner") or not x["spec"].get("response")]
    if gaps:
        note("risk-gaps", f"{len(gaps)} open risk(s) have no owner or no response: " + "; ".join(str(g) for g in gaps[:5]) + ".", [],
             "A risk nobody owns is only a worry. Name the owner and what they will do.")
    held = [r for r in todo if r.deadline or r.ctype in ("FNLT", "MFO")]
    if held and not any(MARGIN_WORDS.search(r.name) for r in rows):
        note("no-margin", "The plan is held to a date but shows no schedule margin.", [r.idx for r in held[:3]],
             "Add a contingency task just before the committed milestone, sized to the risks, and guard it.")
    if has and plan.cal_known and res.length and res.length >= 60 and not cal.holidays:
        note("no-holidays", "The calendar has no holidays, and the plan runs for months.", [], "Add public holidays and shutdowns to calendar.holidays.")

    # Redundant links: A > C when A > B > C already says so.
    if len(leaves) <= 1500:
        up = {}
        for i in plan.order:
            s = set()
            for L in rows[i].links:
                if L.type == "FS" and L.lag >= 0 and L.pred in up:
                    s.add(L.pred)
                    s |= up[L.pred]
            up[i] = s
        redundant = []
        for i in plan.order:
            direct = [L for L in rows[i].links if L.type == "FS" and L.lag == 0 and L.pred in up]
            for L in direct:
                if any(L.pred in up[o.pred] for o in rows[i].links if o is not L and o.type == "FS" and o.lag >= 0 and o.pred in up):
                    redundant.append(L)
        if redundant:
            note("redundant-link", f"{len(redundant)} link(s) repeat what a longer chain already says: "
                 + "; ".join(link_text(plan, L) for L in redundant[:4]) + ("; and more" if len(redundant) > 4 else "") + ".",
                 [L.succ for L in redundant], "Remove them. Fewer links are easier to read and to maintain.")

    # People carrying several tasks at once.
    if has and owners:
        busy = []
        for person in owners:
            events = []
            for r in work:
                if person in r.people and not r.elapsed and r.idx in res.start:
                    events.append((res.start[r.idx].toordinal(), 1))
                    events.append((res.finish[r.idx].toordinal() + 1, -1))
            level = peak = 0
            when = None
            for at, step in sorted(events):
                level += step
                if level > peak:
                    peak, when = level, at
            if peak >= 3:
                busy.append((person, peak, date.fromordinal(when)))
        if busy:
            note("workload", "Owners carrying three or more tasks at once: "
                 + "; ".join(f"{p} ({n} around {w.isoformat()})" for p, n, w in busy[:6]) + ".",
                 [], "Fine for a team, a problem for one person. Check that each can carry the load, or stagger the work.")

    if plan.unsupported:
        note("dates-by-app", "This tool did not work out dates for this plan because it uses: " + "; ".join(plan.unsupported) + ".", [],
             "FractalFlow calculates the dates when it opens the file." if not has else "The dates shown are the ones FractalFlow saved in the file.")
    if plan.base is not None and (plan.base.get("starterVersion") is not None or "(sample)" in plan.name.lower()):
        note("starter-plan", "This is a starter plan.", [], "Give your version its own name before you build it.")
    return F, M


# ---------------------------------------------------------------- report

def why_text(plan, res, i):
    """What sets the start of a task, in words."""
    kind, extra = res.why.get(i, ("start", None))
    if kind == "pred":
        if isinstance(extra, Link):
            lag = f"{extra.lag // MPD:+d}d" if extra.lag else ""
            tail = "" if extra.type == "FS" and not extra.lag else f" ({extra.type}{lag})"
            return plan.rows[extra.pred].label + tail
        if extra:
            return "; ".join(plan.rows[x].label for x in extra[:2])
        return "its predecessors"
    return {"start": "the project start", "constraint": "its constraint date", "actual": "its actual start"}[kind]


def duration_text(r):
    if r.summary:
        return ""
    if r.milestone:
        return "milestone"
    unit = DAY if r.elapsed else MPD
    x = r.minutes / unit
    return days_text(x, " cal days" if r.elapsed else "d")


def float_text(r, tf):
    if tf is None:
        return ""
    if r.elapsed and not r.milestone:
        return "under 1 cal day" if 0 < tf < 1 else days_text(int(tf) if tf > 0 else tf, " cal days")
    return days_text(tf, "d")


def levers(plan, res, limit=5):
    """How far the finish moves if a task on the driving path took no time at all."""
    out = []
    todo = [i for i in res.path if not plan.rows[i].done and not plan.rows[i].started and plan.rows[i].n
            and plan.rows[i].ctype not in ("MSO", "MFO")]          # a task fixed to a date is not a lever
    for i in sorted(todo, key=lambda i: -plan.rows[i].work_days)[:40]:
        alt = schedule(plan, days={i: 0})
        if alt is not None:
            gain = plan.calendar.between(alt.pf, res.pf)
            if gain > 0:
                out.append((gain, i))
    return sorted(out, key=lambda x: (-x[0], x[1]))[:limit]


def print_report(plan, res, findings, measures, show_tasks=False, own=None):
    rows, cal = plan.rows, plan.calendar
    leaves = plan.leaves
    out = []
    w = out.append
    tasks = [r for r in leaves if not r.milestone]
    w(f"PLAN  {plan.name}")
    w(f"  {len(tasks)} tasks, {len(leaves) - len(tasks)} milestones, {sum(1 for r in rows if r.summary)} phases, "
      f"{len(plan.links)} links, {len({p for r in leaves for p in r.people})} owners")
    if res is not None:
        basis = "dates worked out by this tool" if res.source == "tool" else "dates saved in the file by FractalFlow"
        length = f"   {res.length} working days" if res.length is not None else ""
        w(f"  Start {show(res.p_start)}   Finish {show(res.p_finish)}{length}   ({basis})")
    elif plan.errors:
        w("  Dates are not worked out until the errors below are fixed.")
    else:
        w(f"  Start {show(to_day(plan.start))}   Finish: not worked out here; FractalFlow calculates it when it opens the file")
    if plan.cal_known:
        week = " ".join(PY_WEEK[i] for i in sorted(cal.workdays))
        w(f"  Working week: {week}; {len(cal.holidays)} holiday day(s)")
    else:
        w("  Calendar: custom working hours (kept as they are in the file)")
    done = [r for r in leaves if r.done]
    going = [r for r in leaves if r.started or (0 < r.percent < 100)]
    if not plan.errors and (done or going or (plan.status and plan.status[1] and plan.status[1][0] > plan.start[0])):
        w(f"  Status date {show(to_day(plan.status[1])) if plan.status and plan.status[1] else 'not set'}: "
          f"{len(done)} done, {len(going)} in progress, {len(leaves) - len(done) - len(going)} not started")

    errors = [f for f in findings if f.sev == "ERROR"]
    if errors:
        w("")
        w(f"ERRORS ({len(errors)}): fix these first. Nothing can be built until they are gone.")
        for f in errors:
            w(f"  {f.code}: {f.text}")
            if f.fix:
                w(f"      Fix: {f.fix}")

    if res is not None and res.path:
        w("")
        total = "" if res.length is None else f", {res.length} working days end to end"
        w(f"DRIVING PATH  the chain of work that sets the finish date ({len(res.path)} steps{total})")
        path = res.path if len(res.path) <= 24 else res.path[:11] + [None] + res.path[-11:]
        for i in path:
            if i is None:
                w(f"  ... {len(res.path) - 22} more steps ...")
                continue
            r = rows[i]
            fl = res.tf.get(i)
            extra = f"   float {float_text(r, fl)}" if fl and fl >= 1 else ""
            state = "   done" if r.done else "   in progress" if r.started else ""
            w(f"  {show(res.start.get(i))} to {show(res.finish.get(i))}  {r.label}  ({duration_text(r)}){extra}{state}")

    if own is not None and own.path and own.why[own.path[0]][0] == "constraint" and own.path[0] in own.feed:
        # The finish hangs on a fixed date. Show the work that has to be ready for it, and its slack.
        head = rows[own.path[0]]
        chain, cur = [], own.feed[own.path[0]][1]
        while cur is not None and len(chain) < 500:
            chain.append(cur.pred)
            cur = own.feed[cur.pred][1] if cur.pred in own.feed else None
        chain.reverse()
        w("")
        w(f"LEADING IN  {head.label} is held by its constraint date. The chain of work into it "
          f"({len(chain)} steps), with the float each step has before it delays anything:")
        shown = chain if len(chain) <= 16 else chain[:7] + [None] + chain[-8:]
        for i in shown:
            if i is None:
                w(f"  ... {len(chain) - 15} more steps ...")
                continue
            r = rows[i]
            state = "done" if r.done else "in progress" if r.started else "float " + float_text(r, own.tf.get(i))
            w(f"  {show(own.start.get(i))} to {show(own.finish.get(i))}  {r.label}  ({duration_text(r)})   {state}")

    if res is not None:
        marks = [r for r in leaves if r.milestone and r.idx in res.finish]
        if marks:
            w("")
            w("KEY DATES")
            for r in sorted(marks, key=lambda r: (res.finish[r.idx], r.idx)):
                tag = "  done" if r.done else "  critical" if res.crit.get(r.idx) else ""
                w(f"  {show(res.finish[r.idx])}  {r.label}{tag}")
        due = [r for r in leaves if r.deadline and r.idx in res.finish]
        if due:
            w("")
            w("DEADLINES")
            for r in due:
                d = date.fromisoformat(r.deadline[0][:10])
                m = margin_days(plan, res.finish[r.idx], d)
                unit = "working days" if plan.cal_known else "days"
                verdict = "done" if r.done else f"{m} {unit} of margin" if m > 0 else "on the day, no margin" if m == 0 else f"LATE by {-m} {unit}"
                w(f"  {r.label}: due {show(d)}, forecast {show(res.finish[r.idx])}: {verdict}")
        near = sorted([r for r in leaves if not r.done and not r.started and r.idx in res.tf and not r.milestone
                       and (1 if r.elapsed else 0) <= res.tf[r.idx] <= 5 and res.tf[r.idx] > 0],
                      key=lambda r: (res.tf[r.idx], r.idx))
        if near:
            w("")
            w("LEAST FLOAT  not critical, but close (float of 5 days or less)")
            for r in near[:10]:
                w(f"  {float_text(r, res.tf[r.idx]):>10}  {r.label}  ({show(res.start[r.idx])} to {show(res.finish[r.idx])})")
            if len(near) > 10:
                w(f"  ... and {len(near) - 10} more")
        if own is not None:
            lv = levers(plan, own)
            if lv:
                w("")
                w("BIGGEST LEVERS  how many working days the finish pulls in if the step took no time")
                for gain, i in lv:
                    r = rows[i]
                    kind = "a wait: can it be expedited or started sooner?" if r.elapsed else "work: can it be split, overlapped or better staffed?"
                    w(f"  {gain:>4}d  {r.label}  ({duration_text(r)}; {kind})")

    rest = [f for f in findings if f.sev != "ERROR"]
    warns = [f for f in rest if f.sev == "WARN"]
    notes = [f for f in rest if f.sev == "NOTE"]
    w("")
    w(f"CHECKS  {len(errors)} errors, {len(warns)} warnings, {len(notes)} notes")
    for f in warns + notes:
        w(f"  {f.sev:<4} {f.code}: {f.text}")
        if f.fix:
            w(f"       Fix: {f.fix}")
    if not errors and not rest:
        w("  Nothing to report.")
    if measures:
        w("")
        w("MEASURES  (the DCMA 14-point style measures that apply; a guide, not a verdict)")
        width = max(len(m[0]) for m in measures)
        for name, value, target, verdict in measures:
            w(f"  {name:<{width}}  {value}   target {target}   {verdict}")

    if show_tasks:
        w("")
        w("TASKS")
        w("  start       finish      length        float     row")
        for r in rows:
            i = r.idx
            a = res.start.get(i).isoformat() if res is not None and res.start.get(i) else "          "
            b = res.finish.get(i).isoformat() if res is not None and res.finish.get(i) else "          "
            fl = "" if res is None or r.summary else "done" if r.done else float_text(r, res.tf.get(i))
            flags = []
            if res is not None and res.crit.get(i) and not r.done:
                flags.append("critical")
            if r.started:
                flags.append(f"{r.percent}% done")
            if r.people:
                flags.append("owner " + ", ".join(r.people))
            if res is not None and not r.summary and not r.done and i in res.why:
                flags.append("start set by " + why_text(plan, res, i))
            indent = "  " * (r.level - 1)
            w(f"  {a}  {b}  {duration_text(r):<12}  {fl:<8}  {indent}{r.key} | {r.label}" + (f"  [{'; '.join(flags)}]" if flags else ""))
    print("\n".join(out))


def print_what_if(plan, res, changes):
    days, lines = {}, []
    keys = {r.key: r for r in plan.rows}
    for item in changes:
        for part in str(item).split(","):
            part = part.strip()
            if not part:
                continue
            m = re.fullmatch(r"(.+?)\s*:\s*([+\-=])\s*(\d+)\s*d?", part)
            if not m or m.group(1).strip() not in keys:
                raise Fail(f"--what-if '{part}': write KEY:+N, KEY:-N or KEY:=N with a task key from the plan (see --tasks).")
            r = keys[m.group(1).strip()]
            if r.summary or r.done or r.n is None:
                raise Fail(f"--what-if: '{r.name}' is a phase or is already finished, so its length cannot be changed.")
            n = int(m.group(3))
            new = n if m.group(2) == "=" else max(0, days.get(r.idx, r.n) + (n if m.group(2) == "+" else -n))
            days[r.idx] = new
            lines.append(f"  {r.label}: {r.n} to {new} {'calendar ' if r.elapsed else ''}days")
    alt = schedule(plan, days=days)
    if alt is None:
        raise Fail("The what-if could not be worked out for this plan.")
    move = plan.calendar.between(res.pf, alt.pf)
    print("")
    print("WHAT IF")
    print("\n".join(lines))
    verdict = "does not move" if move == 0 else f"moves {abs(move)} working day(s) {'later' if move > 0 else 'earlier'}"
    print(f"  Finish {verdict}: {show(to_day(res.pf))} becomes {show(to_day(alt.pf))}")
    for r in plan.leaves:
        if r.deadline and not r.done:
            d = date.fromisoformat(r.deadline[0][:10])
            a, b = margin_days(plan, res.finish[r.idx], d), margin_days(plan, alt.finish[r.idx], d)
            if a != b:
                print(f"  Deadline {r.label}: margin goes from {a} to {b} working days")
    if alt.path != res.path:
        print("  The driving path changes to: " + " > ".join(plan.rows[i].name for i in alt.path[-8:]))
    else:
        print("  The driving path stays the same.")


def print_finish_by(plan, res, target_text):
    target = parse_day(target_text, "--finish-by")
    goal = (target.toordinal(), PM)
    cal = plan.calendar
    span = max(30, res.pf[0] - plan.start[0])
    lo, hi = target.toordinal() - 3 * span - 400, target.toordinal()

    def finish_for(o):
        r = schedule(plan, start=cal.roll((o, AM)))
        return r.pf if r else None

    print("")
    print(f"FINISH BY {show(target)}")
    now = cal.between(res.pf, goal)
    print(f"  Starting {show(to_day(plan.start))} as planned, the plan finishes {show(to_day(res.pf))}: "
          + (f"{now} working day(s) to spare." if now > 0 else "exactly on the day." if now == 0 else f"{-now} working day(s) too late."))
    first = finish_for(lo)
    if first is None or first > goal:
        print("  No start date makes this work. Dates inside the plan (constraints or recorded progress) hold the finish past the target. "
              "The work itself has to change.")
        return
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = finish_for(mid)
        if f is not None and f <= goal:
            lo = mid
        else:
            hi = mid - 1
    best = cal.prev_work(lo)
    print(f"  Latest start that still makes it: {show(date.fromordinal(best))}.")


# ---------------------------------------------------------------- files and commands

def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise Fail(f"There is no file at {path}.")
    except json.JSONDecodeError as e:
        raise Fail(f"{path} is not valid JSON (line {e.lineno}: {e.msg}).")


def kind_of(data, path):
    if isinstance(data, dict) and isinstance(data.get("project"), dict) and isinstance(data["project"].get("tasks"), list):
        return "plan"
    if isinstance(data, dict) and isinstance(data.get("tasks"), list):
        return "spec"
    raise Fail(f"{path} is neither a plan spec (a JSON object with a tasks list) nor a FractalFlow plan.")


def open_plan(path, want_saved=True):
    """Load a spec or a .ffplan and return (plan, base path)."""
    data = read_json(path)
    if kind_of(data, path) == "plan":
        return plan_from_spec(spec_from_doc(data), base=data, saved=want_saved), path
    base, base_path = None, None
    if data.get("basedOn"):
        base_path = os.path.join(os.path.dirname(os.path.abspath(path)), str(data["basedOn"]))
        if not os.path.exists(base_path):
            raise Fail(f"This spec was made from {data['basedOn']}, which is not next to it any more. Put the original "
                       f"plan file back in the same folder, or run extract again on the plan.")
        base = read_json(base_path)
        if kind_of(base, base_path) != "plan":
            raise Fail(f"{base_path} is not a FractalFlow plan.")
    return plan_from_spec(data, base=base), base_path


def dump_spec(spec):
    head = [(k, v) for k, v in spec.items() if k not in ("tasks", "risks")]
    lines = ["{"]
    for k, v in head:
        lines.append(f"  {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)},")
    for name in ("tasks", "risks"):
        if name not in spec:
            continue
        lines.append(f"  {json.dumps(name)}: [")
        items = spec[name]
        for i, item in enumerate(items):
            lines.append("    " + json.dumps(item, ensure_ascii=False) + ("," if i < len(items) - 1 else ""))
        lines.append("  ],")
    lines[-1] = lines[-1].rstrip(",")
    lines.append("}")
    return "\n".join(lines) + "\n"


def cmd_check(args):
    plan, _ = open_plan(args.file)
    res = saved_result(plan) if plan.saved else schedule(plan)
    own = res if (res is not None and res.source == "tool") else schedule(plan)
    if args.what_if or args.finish_by:
        # A question about one scenario gets a short answer, not the whole report again.
        if plan.errors:
            raise Fail("The plan has errors. Run check without options and fix them first.")
        if own is None:
            raise Fail("What-if and finish-by need dates this tool can work out itself, and this plan uses: "
                       + ("; ".join(plan.unsupported) or "something it could not read") + ".")
        print(f"PLAN  {plan.name}")
        print(f"  Start {show(own.p_start)}   Finish {show(own.p_finish)}   {own.length} working days")
        if args.what_if:
            print_what_if(plan, own, args.what_if)
        if args.finish_by:
            print_finish_by(plan, own, args.finish_by)
        return 0
    findings, measures = (list(plan.findings), [])
    if not plan.errors:
        more, measures = run_checks(plan, res)
        findings += more
    print_report(plan, res, findings, measures, args.tasks, own)
    return 1 if plan.errors else 0


def cmd_build(args):
    data = read_json(args.spec)
    if kind_of(data, args.spec) != "spec":
        raise Fail("build takes a spec. To change an existing plan, run extract on it first, edit the spec, then build.")
    plan, base_path = open_plan(args.spec)
    if base_path and os.path.abspath(base_path) == os.path.abspath(args.out):
        raise Fail("Write the new plan to a new file name, so the original stays as it was.")
    if plan.errors:
        print(f"Not built: {len(plan.errors)} error(s).")
        for f in plan.errors:
            print(f"  {f.code}: {f.text}")
        return 1
    res = schedule(plan)
    if plan.base is None and not plan.spec.get("planId"):
        # Remember the plan's identity so a later revision is recognised as the same plan.
        plan.plan_id = str(uuid.uuid4()).upper()
        try:
            with open(args.spec, encoding="utf-8") as f:
                text = f.read()
            at = text.index("{") + 1
            with open(args.spec, "w", encoding="utf-8") as f:
                f.write(text[:at] + f'\n  "planId": "{plan.plan_id}",' + text[at:])
        except (OSError, ValueError):
            pass
    doc = build_doc(plan, res)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    more, _ = run_checks(plan, res)
    warns = sum(1 for f in more if f.sev == "WARN")
    leaves = plan.leaves
    print(f"Wrote {args.out}")
    print(f"  {sum(1 for r in leaves if not r.milestone)} tasks, {sum(1 for r in leaves if r.milestone)} milestones, {len(plan.links)} links")
    if res is not None:
        print(f"  Start {show(res.p_start)}, finish {show(res.p_finish)}, {res.length} working days")
    else:
        print("  Dates are left for FractalFlow to calculate when it opens the file (" + "; ".join(plan.unsupported) + ").")
    print(f"  Checks: {warns} warning(s). Run check for the details." if warns else "  Checks: no warnings.")
    if not args.out.lower().endswith(".ffplan"):
        print("  Note: FractalFlow opens files that end in .ffplan.")
    return 0


def cmd_extract(args):
    doc = read_json(args.plan)
    if kind_of(doc, args.plan) != "plan":
        raise Fail("extract takes a FractalFlow plan (.ffplan).")
    spec = spec_from_doc(doc)
    rel = os.path.relpath(os.path.abspath(args.plan), os.path.dirname(os.path.abspath(args.spec)))
    spec = dict([("name", spec["name"]), ("basedOn", rel)] + [(k, v) for k, v in spec.items() if k != "name"])
    with open(args.spec, "w", encoding="utf-8") as f:
        f.write(dump_spec(spec))
    plan = plan_from_spec(spec, base=doc)
    P = doc.get("project") or {}
    shown = {"id", "outlineNumber", "name", "outlineLevel", "parentId", "isSummary", "isMilestone", "start", "finish",
             "durationMinutes", "durationDays", "durationIsElapsed", "percentComplete", "constraintType", "constraintDate",
             "deadline", "notes", "actualStart", "actualFinish", "actualDurationMinutes", "remainingDurationMinutes",
             "optimisticDurationMinutes", "pessimisticDurationMinutes"}
    hidden = sorted({k for t in P.get("tasks") or [] for k in t if k not in shown})
    kept = []
    for name, label in (("baselines", "baseline(s)"), ("customFieldDefs", "custom column(s)"), ("timeEntries", "time entries"),
                        ("resources", "resource(s)"), ("assignments", "assignment(s)"), ("calendars", "calendar(s)")):
        if P.get(name):
            kept.append(f"{len(P[name])} {label}")
    print(f"Wrote {args.spec}: {len(spec['tasks'])} rows, {len(plan.links)} links, {len(spec.get('risks', []))} register entries")
    print(f"  Based on {rel}. Keep that file next to the spec: build needs it.")
    print("  Carried through from the original without appearing in the spec: " + (", ".join(kept) or "nothing extra")
          + (f"; task fields {', '.join(hidden)}" if hidden else "") + ".")
    print("  Rows keep their id. Add new rows without an id; delete a row to remove the task.")
    if plan.unsupported:
        print("  This tool will not work out dates for this plan (" + "; ".join(plan.unsupported) + "). FractalFlow recalculates when it opens the file.")
    for f in plan.errors:
        print(f"  ERROR {f.code}: {f.text}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ffplan.py", description="Check, build and read FractalFlow .ffplan schedules.")
    sub = ap.add_subparsers(dest="command", required=True)
    c = sub.add_parser("check", help="report dates, the driving path and quality findings for a spec or a .ffplan")
    c.add_argument("file")
    c.add_argument("--tasks", action="store_true", help="also list every row with its dates, float and what sets its start")
    c.add_argument("--what-if", nargs="+", metavar="KEY:+N", help="try longer or shorter tasks, for example permit:+10 frame:-2 test:=8")
    c.add_argument("--finish-by", metavar="YYYY-MM-DD", help="find the latest start date that still finishes by this date")
    c.set_defaults(run=cmd_check)
    b = sub.add_parser("build", help="write a .ffplan from a spec")
    b.add_argument("spec")
    b.add_argument("out")
    b.set_defaults(run=cmd_build)
    e = sub.add_parser("extract", help="write an editable spec from a .ffplan")
    e.add_argument("plan")
    e.add_argument("spec")
    e.set_defaults(run=cmd_extract)
    args = ap.parse_args(argv)
    try:
        return args.run(args)
    except Fail as e:
        print(f"Stopped: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

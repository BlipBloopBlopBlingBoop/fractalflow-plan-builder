"""Tests for the plan tool. Run with:  python3 -m unittest discover -s tests

The expected dates, float and critical flags in EXPECTED were confirmed against FractalFlow
when these cases were written, so a change that moves any of them needs a fresh look.
"""
import copy
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(HERE, "..", "skills", "fractalflow-plan-builder")
sys.path.insert(0, os.path.join(SKILL, "scripts"))
import ffplan as F  # noqa: E402

CASES = {'links': {'name': 'Links',
           'start': '2027-01-04',
           'tasks': [{'key': 'a', 'name': 'A', 'days': 3},
                     {'key': 'fs2', 'name': 'After A plus two days', 'days': 2, 'pred': ['a FS+2d']},
                     {'key': 'ss1', 'name': 'Starts a day after A starts', 'days': 2, 'pred': ['a SS+1d']},
                     {'key': 'ff', 'name': 'Finishes with A', 'days': 2, 'pred': ['a FF']},
                     {'key': 'ff1', 'name': 'Finishes a day after A', 'days': 2, 'pred': ['a FF+1d']},
                     {'key': 'sf3', 'name': 'Finishes three days after A starts', 'days': 2, 'pred': ['a SF+3d']},
                     {'key': 'lead', 'name': 'Overlaps A by a day', 'days': 2, 'pred': ['a FS-1d']},
                     {'key': 'gate', 'name': 'A done', 'milestone': True, 'pred': ['a']},
                     {'key': 'next', 'name': 'After the gate', 'days': 1, 'pred': ['gate']},
                     {'key': 'end', 'name': 'End', 'milestone': True, 'pred': ['fs2', 'ss1', 'ff', 'ff1', 'sf3', 'lead', 'next']}]},
 'calendar': {'name': 'Calendar',
              'start': '2027-01-03',
              'calendar': {'workdays': ['Sun', 'Mon', 'Tue', 'Wed', 'Thu'], 'holidays': ['2027-01-06', {'from': '2027-01-12', 'to': '2027-01-13'}]},
              'tasks': [{'key': 'a', 'name': 'A', 'days': 2},
                        {'key': 'b', 'name': 'B', 'days': 3, 'pred': ['a']},
                        {'key': 'c', 'name': 'C', 'days': 2, 'pred': ['b FS+1d']},
                        {'key': 'end', 'name': 'End', 'milestone': True, 'pred': ['c']}]},
 'constraints': {'name': 'Constraints',
                 'start': '2027-01-04',
                 'tasks': [{'key': 'a', 'name': 'A', 'days': 2},
                           {'key': 'snet',
                            'name': 'Not before Friday',
                            'days': 2,
                            'pred': ['a'],
                            'constraint': 'SNET',
                            'constraintDate': '2027-01-08'},
                           {'key': 'fnet',
                            'name': 'Finish no earlier than Tuesday',
                            'days': 2,
                            'pred': ['a'],
                            'constraint': 'FNET',
                            'constraintDate': '2027-01-12'},
                           {'key': 'fnlt',
                            'name': 'Finish no later than Wednesday',
                            'days': 2,
                            'pred': ['a'],
                            'constraint': 'FNLT',
                            'constraintDate': '2027-01-06'},
                           {'key': 'mso', 'name': 'Must start Monday', 'days': 2, 'pred': ['a'], 'constraint': 'MSO', 'constraintDate': '2027-01-11'},
                           {'key': 'due', 'name': 'Has a deadline', 'days': 3, 'pred': ['a'], 'deadline': '2027-01-07'},
                           {'key': 'free', 'name': 'Plain', 'days': 2, 'pred': ['a']},
                           {'key': 'end', 'name': 'End', 'milestone': True, 'pred': ['snet', 'fnet', 'fnlt', 'mso', 'due', 'free']}]},
 'waits': {'name': 'Waits',
           'start': '2027-01-04',
           'tasks': [{'key': 'a', 'name': 'A ends Friday', 'days': 5},
                     {'key': 'cure', 'name': 'Three calendar days', 'days': 3, 'elapsed': True, 'pred': ['a']},
                     {'key': 'b', 'name': 'After the wait', 'days': 1, 'pred': ['cure']},
                     {'key': 'week', 'name': 'Seven calendar days', 'days': 7, 'elapsed': True, 'pred': ['a']},
                     {'key': 'c', 'name': 'After the week', 'days': 1, 'pred': ['week']},
                     {'key': 'end', 'name': 'End', 'milestone': True, 'pred': ['b', 'c']}]},
 'progress': {'name': 'Progress',
              'start': '2027-01-04',
              'statusDate': '2027-01-13',
              'tasks': [{'key': 'a', 'name': 'Done late', 'days': 2, 'percent': 100, 'actualStart': '2027-01-04', 'actualFinish': '2027-01-06'},
                        {'key': 'b', 'name': 'Half done', 'days': 4, 'pred': ['a'], 'percent': 50, 'actualStart': '2027-01-07'},
                        {'key': 'c', 'name': 'Not started', 'days': 2, 'pred': ['b']},
                        {'key': 'd', 'name': 'Side task', 'days': 1, 'pred': ['a']},
                        {'key': 'end', 'name': 'End', 'milestone': True, 'pred': ['c', 'd']}]}}

# key -> [start, finish, total float in days (calendar days for calendar-day tasks), critical]
EXPECTED = {'links': {'a': ['2027-01-04T08:00', '2027-01-06T17:00', 0.0, True],
           'fs2': ['2027-01-11T08:00', '2027-01-12T17:00', 0.0, True],
           'ss1': ['2027-01-05T08:00', '2027-01-06T17:00', 4.0, False],
           'ff': ['2027-01-05T08:00', '2027-01-06T17:00', 4.0, False],
           'ff1': ['2027-01-06T08:00', '2027-01-07T17:00', 3.0, False],
           'sf3': ['2027-01-05T08:00', '2027-01-06T17:00', 4.0, False],
           'lead': ['2027-01-06T08:00', '2027-01-07T17:00', 3.0, False],
           'gate': ['2027-01-06T17:00', '2027-01-06T17:00', 3.0, False],
           'next': ['2027-01-07T08:00', '2027-01-07T17:00', 3.0, False],
           'end': ['2027-01-12T17:00', '2027-01-12T17:00', 0.0, True]},
 'calendar': {'a': ['2027-01-03T08:00', '2027-01-04T17:00', 0.0, True],
              'b': ['2027-01-05T08:00', '2027-01-10T17:00', 0.0, True],
              'c': ['2027-01-14T08:00', '2027-01-17T17:00', 0.0, True],
              'end': ['2027-01-17T17:00', '2027-01-17T17:00', 0.0, True]},
 'constraints': {'a': ['2027-01-04T08:00', '2027-01-05T17:00', -1.0, True],
                 'snet': ['2027-01-08T08:00', '2027-01-11T17:00', 1.0, False],
                 'fnet': ['2027-01-11T08:00', '2027-01-12T17:00', 0.0, True],
                 'fnlt': ['2027-01-06T08:00', '2027-01-07T17:00', -1.0, True],
                 'mso': ['2027-01-11T08:00', '2027-01-12T17:00', 0.0, True],
                 'due': ['2027-01-06T08:00', '2027-01-08T17:00', -1.0, True],
                 'free': ['2027-01-06T08:00', '2027-01-07T17:00', 3.0, False],
                 'end': ['2027-01-12T17:00', '2027-01-12T17:00', 0.0, True]},
 'waits': {'a': ['2027-01-04T08:00', '2027-01-08T17:00', 0.0, True],
           'cure': ['2027-01-08T17:00', '2027-01-11T17:00', 6.625, False],
           'b': ['2027-01-12T08:00', '2027-01-12T17:00', 4.0, False],
           'week': ['2027-01-08T17:00', '2027-01-15T17:00', 2.625, False],
           'c': ['2027-01-18T08:00', '2027-01-18T17:00', 0.0, True],
           'end': ['2027-01-18T17:00', '2027-01-18T17:00', 0.0, True]},
 'progress': {'a': ['2027-01-04T08:00', '2027-01-06T17:00', 0.0, False],
              'b': ['2027-01-07T08:00', '2027-01-12T17:00', 0.0, True],
              'c': ['2027-01-13T08:00', '2027-01-14T17:00', 0.0, True],
              'd': ['2027-01-07T08:00', '2027-01-07T17:00', 5.0, False],
              'end': ['2027-01-14T17:00', '2027-01-14T17:00', 0.0, True]}}


def solve(spec):
    plan = F.plan_from_spec(copy.deepcopy(spec))
    return plan, F.schedule(plan)


def run(*argv):
    out = io.StringIO()
    with redirect_stdout(out):
        code = F.main(list(argv))
    return code, out.getvalue()


class Dates(unittest.TestCase):
    def test_cases_match_the_confirmed_dates(self):
        for name, spec in CASES.items():
            plan, res = solve(spec)
            self.assertEqual([f.text for f in plan.errors], [], name)
            self.assertIsNotNone(res, name)
            for r in plan.leaves:
                got = [F.iso(res.es[r.idx])[:16], F.iso(res.ef[r.idx])[:16], round(res.tf[r.idx], 3), bool(res.crit[r.idx])]
                self.assertEqual(got, EXPECTED[name][r.key], f"{name}: {r.key}")

    def test_a_built_file_reads_back_to_the_same_dates(self):
        for name, spec in CASES.items():
            plan, res = solve(spec)
            doc = F.build_doc(plan, res)
            again = F.plan_from_spec(F.spec_from_doc(doc), base=doc)
            res2 = F.schedule(again)
            self.assertEqual(again.unsupported, [], name)
            self.assertEqual({k: v for k, v in res.ef.items()}, {k: v for k, v in res2.ef.items()}, name)
            self.assertEqual(res.pf, res2.pf, name)

    def test_milestones_are_written_at_one_instant(self):
        # A milestone whose start and finish differ would be read by the app as a one-day task.
        plan, res = solve(CASES["links"])
        for t in F.build_doc(plan, res)["project"]["tasks"]:
            if t["isMilestone"]:
                self.assertEqual(t["start"], t["finish"], t["name"])

    def test_no_saved_calculation_is_written(self):
        plan, res = solve(CASES["links"])
        self.assertNotIn("cpm", F.build_doc(plan, res))

    def test_later_start_never_finishes_earlier(self):
        plan, res = solve(CASES["constraints"])
        last = None
        for step in range(0, 40, 3):
            alt = F.schedule(plan, start=plan.calendar.roll((plan.start[0] + step, F.AM)))
            self.assertTrue(last is None or alt.pf >= last)
            last = alt.pf


class Calendars(unittest.TestCase):
    def test_holidays_survive_the_file_format(self):
        cal = F.calendar_from_spec({"workdays": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                                    "holidays": ["2027-05-31", {"from": "2027-12-24", "to": "2027-12-31"}]}, self.fail)
        week, exceptions = cal.file()
        back = F.calendar_from_file({"weeklyWorkingMinutes": week, "exceptions": exceptions})
        self.assertEqual((back.workdays, back.holidays), (cal.workdays, cal.holidays))
        self.assertEqual(back.spec(), cal.spec())

    def test_unusual_hours_are_left_alone(self):
        week = [[], [[540, 1080]], [[540, 1080]], [[540, 1080]], [[540, 1080]], [[540, 1080]], []]
        self.assertIsNone(F.calendar_from_file({"weeklyWorkingMinutes": week, "exceptions": []}))

    def test_working_day_arithmetic(self):
        cal = F.Calendar()
        mon = F.date(2027, 1, 4).toordinal()
        self.assertEqual(cal.add((mon, F.AM), 5), (mon + 4, F.PM))
        self.assertEqual(cal.add((mon + 4, F.PM), 1), (mon + 7, F.PM))
        self.assertEqual(cal.sub((mon + 7, F.AM), 1), (mon + 4, F.AM))
        self.assertEqual(cal.between((mon, F.AM), (mon + 7, F.PM)), 6)
        self.assertEqual(cal.between((mon + 7, F.PM), (mon, F.AM)), -6)


class Links(unittest.TestCase):
    KEYS = {"a": 0, "phase-2": 1, "pour-concrete": 2}

    def test_forms(self):
        for text, want in {"a": ("a", "FS", 0), "a SS": ("a", "SS", 0), "a FS+2d": ("a", "FS", 960), "a-2": ("a", "FS", -960),
                           "phase-2": ("phase-2", "FS", 0), "phase-2 FS+1d": ("phase-2", "FS", 480),
                           "pour-concrete ff": ("pour-concrete", "FF", 0)}.items():
            self.assertEqual(F.parse_link(text, self.KEYS)[:3], want, text)
        self.assertEqual(F.parse_link({"task": "a", "type": "ss", "lag": 2}, self.KEYS)[:3], ("a", "SS", 960))

    def test_unknown_key(self):
        with self.assertRaises(F.Fail):
            F.parse_link("nobody FS", self.KEYS)


class Problems(unittest.TestCase):
    def errors(self, spec):
        return " | ".join(f.text for f in F.plan_from_spec(spec).errors)

    def test_loop(self):
        text = self.errors({"name": "x", "start": "2027-01-04", "tasks": [
            {"key": "a", "name": "A", "days": 1, "pred": ["b"]}, {"key": "b", "name": "B", "days": 1, "pred": ["a"]}]})
        self.assertIn("loop", text)

    def test_misspelt_field_is_caught(self):
        text = self.errors({"name": "x", "start": "2027-01-04", "tasks": [
            {"key": "a", "name": "A", "days": 1}, {"key": "b", "name": "B", "days": 1, "preds": ["a"]}]})
        self.assertIn("Did you mean 'pred'", text)

    def test_links_on_phases_and_part_days_are_refused(self):
        text = self.errors({"name": "x", "start": "2027-01-04", "tasks": [
            {"key": "p", "name": "Phase", "level": 1}, {"key": "a", "name": "A", "level": 2, "days": 1.5},
            {"key": "b", "name": "B", "level": 1, "days": 1, "pred": ["p"]}]})
        self.assertIn("involves a phase", text)
        self.assertIn("whole days", text)

    def test_lag_next_to_a_calendar_day_task_is_refused(self):
        text = self.errors({"name": "x", "start": "2027-01-04", "tasks": [
            {"key": "a", "name": "A", "days": 1}, {"key": "w", "name": "Wait", "days": 3, "elapsed": True, "pred": ["a FS+1d"]}]})
        self.assertIn("calendar-day task", text)


class Checks(unittest.TestCase):
    def codes(self, spec):
        plan, res = solve(spec)
        findings, measures = F.run_checks(plan, res)
        return {f.code for f in findings}, {m[0]: m[3] for m in measures}

    def test_example_plan_is_clean(self):
        with open(os.path.join(SKILL, "examples", "office-move.json"), encoding="utf-8") as f:
            plan, res = solve(json.load(f))
        findings, _ = F.run_checks(plan, res)
        self.assertEqual(plan.errors, [])
        self.assertEqual([f.code for f in findings if f.sev == "WARN"], [])

    def test_loose_ends_and_late_dates_are_found(self):
        codes, measures = self.codes({"name": "x", "start": "2027-01-04", "tasks": [
            {"key": "a", "name": "A", "days": 3, "owner": "Ann"},
            {"key": "b", "name": "B", "days": 3, "pred": ["a FS-1d"], "owner": "Ann", "deadline": "2027-01-06"},
            {"key": "c", "name": "TBD", "days": 2},
            {"key": "end", "name": "End", "milestone": True, "pred": ["b"]}]})
        for code in ("open-start", "open-end", "lead", "deadline-missed", "negative-float", "vague-name", "no-owner"):
            self.assertIn(code, codes)
        self.assertEqual(measures["Leads (negative lags)"], "review")
        self.assertEqual(measures["Negative float"], "review")

    def test_progress_checks(self):
        codes, _ = self.codes({"name": "x", "start": "2027-01-04", "statusDate": "2027-01-15", "tasks": [
            {"key": "a", "name": "A", "days": 2, "percent": 100, "actualStart": "2027-01-04", "actualFinish": "2027-01-05"},
            {"key": "b", "name": "B", "days": 2, "pred": ["a"]},
            {"key": "c", "name": "C", "days": 2, "pred": ["b"], "percent": 30},
            {"key": "end", "name": "End", "milestone": True, "pred": ["c"]}]})
        for code in ("not-started", "progress-no-start"):
            self.assertIn(code, codes)

    def test_remaining_days_move_a_running_task_past_the_status_date(self):
        spec = {"name": "x", "start": "2027-01-04", "statusDate": "2027-01-15", "tasks": [
            {"key": "a", "name": "A", "days": 3, "percent": 50, "actualStart": "2027-01-04"},
            {"key": "b", "name": "B", "days": 2, "pred": ["a"]},
            {"key": "end", "name": "End", "milestone": True, "pred": ["b"]}]}
        codes, _ = self.codes(spec)
        self.assertIn("overdue", codes)
        spec["tasks"][0].pop("percent")
        spec["tasks"][0]["remaining"] = 2
        plan, res = solve(spec)
        self.assertEqual(plan.errors, [])
        a = plan.rows[0]
        self.assertEqual((a.n, a.percent), (12, 83))            # ten working days spent, two to go
        self.assertEqual(res.finish[0].isoformat(), "2027-01-19")
        self.assertEqual(res.start[1].isoformat(), "2027-01-20")
        findings, _ = F.run_checks(plan, res)
        self.assertNotIn("overdue", {f.code for f in findings})
        task = F.build_doc(plan, res)["project"]["tasks"][0]
        self.assertEqual(task["actualDurationMinutes"] + task["remainingDurationMinutes"], task["durationMinutes"])


class Files(unittest.TestCase):
    def test_build_extract_edit_build(self):
        with tempfile.TemporaryDirectory() as d:
            spec_path, first = os.path.join(d, "plan.json"), os.path.join(d, "Plan.ffplan")
            with open(spec_path, "w", encoding="utf-8") as f:
                json.dump(CASES["links"], f)
            self.assertEqual(run("build", spec_path, first)[0], 0)
            with open(first, encoding="utf-8") as f:
                doc = json.load(f)
            # Something this tool does not show in a spec must come through a rebuild untouched.
            doc["project"]["tasks"][0]["customFields"] = {"text1": "Keep me"}
            doc["project"]["customFieldDefs"] = [{"key": "text1", "name": "Stage"}]
            doc["cpm"] = {"tasks": {}}
            with open(first, "w", encoding="utf-8") as f:
                json.dump(doc, f)
            edit_path, second = os.path.join(d, "edit.json"), os.path.join(d, "Plan 2.ffplan")
            self.assertEqual(run("extract", first, edit_path)[0], 0)
            with open(edit_path, encoding="utf-8") as f:
                spec = json.load(f)
            self.assertEqual(spec["basedOn"], "Plan.ffplan")
            victim = next(r for r in spec["tasks"] if r["name"] == "Overlaps A by a day")
            spec["tasks"].remove(victim)
            for r in spec["tasks"]:
                r["pred"] = [p for p in r.get("pred", []) if not str(p).startswith(victim["key"])] or None
                if r["pred"] is None:
                    del r["pred"]
            spec["tasks"].insert(1, {"key": "new", "name": "Brand new task", "days": 4, "pred": ["t1"], "owner": "Sam"})
            next(r for r in spec["tasks"] if r["name"] == "End")["pred"].append("new")
            with open(edit_path, "w", encoding="utf-8") as f:
                json.dump(spec, f)
            self.assertEqual(run("build", edit_path, second)[0], 0)
            with open(second, encoding="utf-8") as f:
                out = json.load(f)
            tasks = {t["name"]: t for t in out["project"]["tasks"]}
            self.assertEqual(tasks["A"]["customFields"], {"text1": "Keep me"})
            self.assertEqual(tasks["A"]["id"], "1")
            self.assertNotIn("Overlaps A by a day", tasks)
            self.assertIn("Brand new task", tasks)
            self.assertEqual(out["project"]["customFieldDefs"], [{"key": "text1", "name": "Stage"}])
            self.assertEqual(out["id"], doc["id"])
            self.assertNotIn("cpm", out)
            ids = {t["id"] for t in out["project"]["tasks"]}
            self.assertEqual(len(ids), len(out["project"]["tasks"]))
            for dep in out["project"]["dependencies"]:
                self.assertIn(dep["predecessorId"], ids)
                self.assertIn(dep["successorId"], ids)
            self.assertEqual([r["name"] for r in out["project"]["resources"]], ["Sam"])

    def test_untouched_round_trip_changes_nothing(self):
        plan, res = solve(CASES["progress"])
        doc = F.build_doc(plan, res)
        again = F.plan_from_spec(F.spec_from_doc(doc), base=doc)
        out = F.build_doc(again, F.schedule(again))
        a, b = copy.deepcopy(doc["project"]), copy.deepcopy(out["project"])
        self.assertEqual(a, b)

    def test_check_reports_and_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            good, bad = os.path.join(d, "good.json"), os.path.join(d, "bad.json")
            with open(good, "w", encoding="utf-8") as f:
                json.dump(CASES["constraints"], f)
            with open(bad, "w", encoding="utf-8") as f:
                json.dump({"name": "x", "start": "2027-01-04", "tasks": [{"key": "a", "name": "A", "days": 1, "pred": ["zz"]}]}, f)
            code, text = run("check", good, "--tasks")
            self.assertEqual(code, 0)
            for section in ("DRIVING PATH", "DEADLINES", "CHECKS", "MEASURES", "TASKS"):
                self.assertIn(section, text)
            self.assertEqual(run("check", bad)[0], 1)
            self.assertEqual(run("build", bad, os.path.join(d, "x.ffplan"))[0], 1)
            code, text = run("check", good, "--what-if", "free:+10", "--finish-by", "2027-02-26")
            self.assertEqual(code, 0)
            self.assertIn("WHAT IF", text)
            self.assertIn("Latest start", text)


if __name__ == "__main__":
    unittest.main()

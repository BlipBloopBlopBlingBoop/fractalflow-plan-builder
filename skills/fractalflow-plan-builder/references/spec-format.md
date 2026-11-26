# The spec and the tool

Everything the plan spec can hold and everything `scripts/ffplan.py` does.

## Commands

```
ffplan.py check   SPEC_OR_PLAN [--tasks] [--what-if KEY:+N ...] [--finish-by YYYY-MM-DD]
ffplan.py build   SPEC.json OUT.ffplan
ffplan.py extract PLAN.ffplan SPEC.json
```

| Command | Reads | Writes | Exit code |
|---|---|---|---|
| `check` | A spec, or a `.ffplan` | Nothing | 0 clean or warnings only, 1 errors, 2 could not run |
| `build` | A spec (and the original plan, for a spec made by `extract`) | The `.ffplan`. On a new plan it also adds a `planId` line to the spec. | 0 built, 1 errors |
| `extract` | A `.ffplan` | A spec | 0 |

The tool uses the Python standard library only (Python 3.8 or later). It reads the file it is given and, for a spec made by `extract`, the original plan named in `basedOn`. It writes only the output file it is given. It makes no network requests and starts no other programs.

## The spec

A JSON object. Field names are checked, so a misspelt field is reported as an error.

### Top level

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | The plan's name. |
| `start` | yes | Project start, `YYYY-MM-DD`. Moved to the next working day if it is not one. |
| `tasks` | yes | The rows, in outline order. |
| `calendar` | no | Working week and holidays. Default: Monday to Friday, no holidays. |
| `statusDate` | no | The day progress was measured. |
| `risks` | no | The register: risks, assumptions, issues, dependencies, decisions. |
| `company` | no | Stored with the plan. |
| `planId` | no | Written by `build` so later versions are recognised as the same plan. Leave it alone. |
| `basedOn` | no | Written by `extract`: the original plan file, which must stay next to the spec. |

### calendar

```json
"calendar": {
  "workdays": ["Sun", "Mon", "Tue", "Wed", "Thu"],
  "holidays": ["2027-05-31", {"from": "2027-12-24", "to": "2028-01-01"}]
}
```

Working days are eight hours. A holiday is a whole day or an inclusive range of days.

### tasks

One object per row.

| Field | Meaning |
|---|---|
| `key` | A short unique name for the row, used in `pred`, in risks and in `--what-if`. Letters, digits, hyphens. |
| `name` | What the row is called in the plan. |
| `level` | Outline level, 1 for the top. A row can be at most one level deeper than the row above. Default 1. |
| `days` | Duration in whole working days. |
| `elapsed` | `true` to count `days` as calendar days: the task runs through weekends and holidays. |
| `milestone` | `true` for a point in time. No `days`. |
| `pred` | What must come first: a list of links. |
| `owner` | Who answers for the task. |
| `resources` | Other people or crews on the task, as a list of names. |
| `optimistic`, `pessimistic` | The range for the duration, in the same days as `days`. |
| `deadline` | A date to be measured against. Does not move the task. |
| `constraint`, `constraintDate` | Pins the task: `SNET`, `SNLT`, `FNET`, `FNLT`, `MSO`, `MFO`, with a date. |
| `notes` | Free text: the basis of the estimate, the source of a date, acceptance criteria. |
| `percent` | Percent complete, 0 to 100. |
| `actualStart`, `actualFinish` | Real dates. A finished task (`percent` 100) has both or neither. A finished milestone has one. |
| `remaining` | For a task under way: the working days still needed as of `statusDate` (calendar days for a calendar-day task). Needs `actualStart`. The tool sets the duration to the time already spent plus this, and works out the percent. |
| `id` | Only in a spec made by `extract`: the task's identity in the original file. Keep it on existing rows; leave it off new ones. |
| `minutes` | Only in a spec made by `extract`, for a task whose duration is not whole days. |

**Phases.** A row followed by deeper rows is a phase. It takes its dates from the rows under it, so it uses only `key`, `name`, `level` and `notes`. Anything else on a phase is ignored with a warning, and a link to or from a phase is an error.

**Links.** Each entry in `pred` is a task key, then an optional link type and an optional lag in working days:

| Entry | Meaning |
|---|---|
| `"design"` | Finish-to-start: starts after `design` finishes. |
| `"design SS"` | Start-to-start: starts when `design` starts. |
| `"design FF"` | Finish-to-finish: finishes when `design` finishes, or later. |
| `"design SF"` | Start-to-finish. Rarely right. |
| `"design FS+2d"` | Two working days after `design` finishes. |
| `"design SS+3d"` | Three working days after `design` starts. |
| `"design FS-1d"` | A lead: one working day before `design` finishes. Avoid. |

A lag next to a calendar-day task is not allowed: put the extra wait in a task of its own. Order in the list does not matter, and rows can refer to rows above or below them.

**Dates.** Dates are whole days. A start-type date (`start`, `actualStart`, `SNET`, `SNLT`, `MSO`) means the start of that working day. A finish-type date (`deadline`, `actualFinish`, `FNET`, `FNLT`, `MFO`) means the end of it.

### risks

```json
{"kind": "risk", "title": "Permit review runs long", "description": "...", "probability": 3, "impact": 4,
 "owner": "Project lead", "status": "open", "response": "Submit early; ask about an expedited review.",
 "tasks": ["permit"], "impactDays": 15}
```

| Field | Meaning |
|---|---|
| `kind` | `risk`, `assumption`, `issue`, `dependency` or `decision`. Default `risk`. |
| `title` | Required. |
| `probability`, `impact` | 1 to 5. Mainly for risks. |
| `owner`, `response`, `description` | Who and what. |
| `status` | `open`, `mitigating`, `closed` or `realized`. Default `open`. |
| `tasks` | Keys of the tasks it touches. |
| `impactDays` | The delay, in working days, if the risk happens. |

## Reading the report

| Section | What it tells you |
|---|---|
| Header | Counts, start, finish, length in working days, and where the dates came from. |
| ERRORS | Problems that stop the plan being scheduled or built. |
| DRIVING PATH | The chain of work that sets the finish date, in order, with dates. A calendar-day step may show a little float where a weekend absorbs it. |
| LEADING IN | Shown when the driving path starts at a task held by a constraint date, such as a booked event: the chain of work into that task, with the float each step has. The smallest float in the chain is how far the preparation can slip. |
| KEY DATES | Every milestone with its date. |
| DEADLINES | Each deadline, the forecast, and the margin or the miss in working days. |
| LEAST FLOAT | Tasks that are not critical but have five days of float or less. |
| BIGGEST LEVERS | For steps on the driving path, how many working days the finish would pull in if the step took no time. It shows where shortening is worth the effort. A step can be worth less than its length when another chain is close behind. |
| CHECKS | Findings, most serious first, each with a fix. See `schedule-checks.md`. |
| MEASURES | Standard schedule-quality measures with targets. |
| TASKS (`--tasks`) | Every row: dates, length, float, and what sets its start. The key is shown before each name. |

`--what-if` and `--finish-by` print only their own short answer.

## What the tool works out, and what it leaves to FractalFlow

The tool calculates dates with the critical path method at whole-day precision: a forward pass for the earliest dates, a backward pass for the latest, float from the difference. It handles the four link types with lags, the six dated constraints, deadlines, calendar-day tasks, the working week, holidays and recorded progress.

FractalFlow recalculates every plan when it opens the file. The tool's dates are there so you can talk about the plan before the person has opened it. If the two ever differ, the app is right.

The tool does not work out dates for a plan that has any of these, which only occur in plans that came from FractalFlow or from another scheduling tool:

- durations or lags that are not whole days
- working hours other than eight-hour days, or part-day calendar exceptions
- tasks or resources on their own calendars
- manually scheduled, inactive or split tasks
- as-late-as-possible tasks, or a plan scheduled backward from its finish
- percentage lags, links on phases, lags next to calendar-day tasks
- resource leveling delays
- dates with a time of day other than the start or end of the working day

`check` names what it found. For such a plan it reports the dates FractalFlow saved in the file. You can still edit the plan through `extract` and `build`; the new dates appear when FractalFlow opens the result. `--what-if`, `--finish-by` and BIGGEST LEVERS are not available for it.

The tool does not do resource leveling, cost, earned value or risk simulation. Those belong to the app.

## Changing an existing plan

```
ffplan.py extract "Their Plan.ffplan" edit.json
# edit edit.json
ffplan.py check edit.json
ffplan.py build edit.json "Their Plan v2.ffplan"
```

- The spec shows what this tool edits: the outline, names, durations, links, owners, dates, progress, notes and the register.
- Everything else in the original file is carried through untouched: custom columns and their values, baselines, time entries, costs, assignment details, calendars the tool does not model. `extract` lists what it found.
- A row you do not change is written back exactly as it was. Only the fields you change are rewritten.
- Keep `id` on existing rows. A row without an `id` is a new task. Deleting a row removes the task and every link, assignment, baseline entry and register reference that pointed to it. Before deleting, re-link what it sat between.
- If you change who is on a task, its assignments are rewritten simply: one unit each.
- `build` refuses to overwrite the original. The new file opens as a separate plan.
- Keys in an extracted spec are `t` followed by the task id, for example `t17`.

## Limits worth knowing

- Durations are whole days. A two-hour task is a one-day task here.
- One calendar for the whole plan.
- An owner is a name. Rates, availability and calendars for people are set in FractalFlow.
- A baseline is saved in FractalFlow, not here.

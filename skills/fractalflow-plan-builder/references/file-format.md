# Writing a .ffplan file

A `.ffplan` is a JSON document. You write it yourself, with care, following this page exactly. `examples/office-move.json` is a complete file written this way: copy its shape.

FractalFlow works out every date when it opens a file that has no saved calculation. So you write the structure (tasks, durations, links, calendar, people, progress, register) and leave the dates as simple placeholders. The app does the scheduling, and its dates are the real ones.

## The rules that keep a file opening

1. Valid JSON, UTF-8. No comments, no trailing commas.
2. No `cpm` key at the top level. Remove it when changing a file the app saved; that is what tells the app to recalculate.
3. Every id is a string. Task ids are `"1"`, `"2"`, `"3"` in outline order for a new plan. Never reuse or renumber ids in an existing plan; give new tasks the next unused number.
4. Every id that something points at exists: `parentId`, `predecessorId`, `successorId`, `taskId`, `resourceId`, `taskIds`.
5. A milestone has `durationMinutes` 0 and `start` equal to `finish`. If they differ, the app turns it into a one-day task.
6. Times are always `T08:00:00.000Z` (start of a working day) or `T17:00:00.000Z` (end of one). The `Z` is part of the format: plan dates are wall-clock times, not real UTC.
7. Durations and lags are whole working days times 480 minutes, or for calendar-day tasks whole days times 1440.

Before handing over a file, read it back once against this list.

## Top level

```json
{
  "version": 1,
  "id": "6F1C2B8E-4A3D-4E8B-9C21-7D5E0A9B3F14",
  "name": "Kitchen Renovation",
  "project": {
    "meta": { ... },
    "calendars": [ ... ],
    "tasks": [ ... ],
    "dependencies": [ ... ],
    "resources": [ ... ],
    "assignments": [ ... ],
    "risks": [ ... ],
    "baselines": [],
    "milestones": []
  }
}
```

- `id`: a new random UUID in upper case for a new plan. Keep it when revising a plan you built earlier in the conversation, so the app sees a new version of the same plan. When the file came with a `starterVersion` key (a FractalFlow starter plan), remove that key and give a new id.
- `milestones`: always an empty list. The app rebuilds it from the tasks.

## meta

```json
"meta": {
  "name": "Kitchen Renovation",
  "schemaVersion": "1.0",
  "source": "mspdi",
  "projectStart": "2027-01-04T08:00:00.000Z",
  "projectFinish": "2027-01-04T08:00:00.000Z",
  "defaultCalendarId": "1",
  "minutesPerDay": 480,
  "minutesPerWeek": 2400,
  "daysPerMonth": 20,
  "parsedAt": "2026-11-26T12:00:00.000Z"
}
```

- `projectStart`: the start date, on a working day, at 08:00. `projectFinish`: the same value; the app replaces it.
- `minutesPerWeek`: 480 times the number of working days in the week.
- `daysPerMonth`: 20 for a five-day week, otherwise the working days per week times 52 divided by 12, rounded.
- `parsedAt`: the current time.
- `statusDate`: only when progress is recorded, as the status day at `T17:00:00.000Z`.
- `company`: optional text.

## The calendar

One calendar, id `"1"`:

```json
{
  "id": "1", "name": "Standard", "baseCalendarId": null,
  "weeklyWorkingMinutes": [
    [],
    [[480, 720], [780, 1020]],
    [[480, 720], [780, 1020]],
    [[480, 720], [780, 1020]],
    [[480, 720], [780, 1020]],
    [[480, 720], [780, 1020]],
    []
  ],
  "exceptions": [
    {"start": "2027-01-18T00:00:00.000Z", "finish": "2027-01-19T00:00:00.000Z", "working": false},
    {"start": "2027-12-24T00:00:00.000Z", "finish": "2028-01-02T00:00:00.000Z", "working": false}
  ]
}
```

- `weeklyWorkingMinutes` has seven entries, **Sunday first**. A working day is `[[480, 720], [780, 1020]]` (08:00 to 12:00 and 13:00 to 17:00, eight hours). A day off is `[]`. The example is Monday to Friday.
- Each holiday or shutdown is one exception. `finish` is midnight at the **start of the day after** the last day off: a single holiday on the 18th runs to the 19th; a shutdown from Dec 24 to Jan 1 runs to Jan 2.

## Tasks

One object per row, in outline order:

```json
{"id": "3", "outlineNumber": "1.2", "name": "Apply for city permit", "outlineLevel": 2, "parentId": "1",
 "isSummary": false, "isMilestone": false,
 "start": "2027-01-04T08:00:00.000Z", "finish": "2027-01-04T17:00:00.000Z",
 "durationMinutes": 14400, "durationDays": 30.0, "durationIsElapsed": true,
 "percentComplete": 0, "constraintType": "AS_SOON_AS_POSSIBLE", "constraintDate": null, "deadline": null,
 "notes": "Calendar days. Assumption: confirm with the city."}
```

| Field | Value |
|---|---|
| `outlineNumber` | `"1"`, `"1.1"`, `"1.2"`, `"2"`... |
| `outlineLevel` | 1 for top-level rows. A row is at most one level deeper than the row above. |
| `parentId` | The id of the phase it sits in, or `null` at level 1. |
| `isSummary` | `true` for a phase (a row with rows under it). |
| `isMilestone` | `true` for a milestone. |
| `start`, `finish` | Placeholders (below). |
| `durationMinutes` | Working days times 480. Calendar-day task: days times 1440. Milestone and phase: 0. |
| `durationDays` | `durationMinutes` divided by 480. |
| `durationIsElapsed` | `true` only on calendar-day tasks. Leave the key out otherwise. |
| `percentComplete` | 0 to 100. |
| `constraintType` | `AS_SOON_AS_POSSIBLE`, or `START_NO_EARLIER_THAN`, `START_NO_LATER_THAN`, `FINISH_NO_EARLIER_THAN`, `FINISH_NO_LATER_THAN`, `MUST_START_ON`, `MUST_FINISH_ON`. |
| `constraintDate` | `null`, or the date: at 08:00 for the three start types, 17:00 for the three finish types. Never before the project start. |
| `deadline` | `null`, or the date at 17:00. |
| `notes` | Optional text: the basis of an estimate, the source of a date. |
| `optimisticDurationMinutes`, `pessimisticDurationMinutes` | Optional range, in the same minutes as the duration. |

**Placeholder dates.** For every task not yet started: `start` is the project start at 08:00. `finish` is the same value for milestones and phases, and the project start day at 17:00 for everything else. The app replaces them.

**Phases** take their dates from their rows. Give them only the fields above with duration 0; put owners, deadlines and links on tasks or the phase's closing milestone.

## Links

```json
{"predecessorId": "2", "successorId": "3", "type": "FS", "lagMinutes": 0}
```

- `type`: `FS`, `SS`, `FF` or `SF`.
- `lagMinutes`: working days times 480. A lead is negative. Avoid both.
- Link tasks and milestones, never phases.
- No lag on a link to or from a calendar-day task. Put the wait in a task of its own.
- No loops.

## People

```json
"resources": [{"id": "1", "name": "Contractor", "type": "work", "maxUnits": 1}],
"assignments": [{"taskId": "3", "resourceId": "1", "units": 1, "workMinutes": 14400,
                 "start": "2027-01-04T08:00:00.000Z", "finish": "2027-01-04T17:00:00.000Z"}]
```

- One resource per distinct name. The owner of a task, and anyone else on it, gets an assignment.
- `workMinutes`: the task's `durationMinutes`, or 0 on a calendar-day task.
- Assignment `start` and `finish`: the same placeholders as an ordinary task.

## Progress

- `meta.statusDate` set to the status day at 17:00.
- **Finished task:** `percentComplete` 100; `actualStart` (08:00) and `actualFinish` (17:00); `start` and `finish` equal to those; `durationMinutes` the working days it actually took times 480; `actualDurationMinutes` equal to `durationMinutes`; `remainingDurationMinutes` 0. A finished milestone: one date, used for all four.
- **Task under way:** `actualStart` (08:00); `start` equal to it, `finish` that day at 17:00. Count the working days from the actual start to the status date, inclusive: that is the time spent. Ask how many working days are still needed. Then `actualDurationMinutes` = spent times 480, `remainingDurationMinutes` = still needed times 480, `durationMinutes` = the sum, `percentComplete` = spent divided by the sum, as a whole percent. The app then places its finish where it really is.
- **Not started:** no progress fields.

## The register

```json
{"id": "r1", "kind": "risk", "title": "Permit review runs long", "status": "open",
 "probability": 3, "impact": 4, "owner": "Homeowner",
 "response": "Submit early; ask about an expedited review.",
 "taskIds": ["3"], "scheduleImpactMinutes": 7200}
```

- `kind`: `risk`, `assumption`, `issue`, `dependency` or `decision`. `status`: `open`, `mitigating`, `closed` or `realized`.
- `probability` and `impact` 1 to 5. `scheduleImpactMinutes`: the delay if it happens, working days times 480. `description` optional. Ids `r1`, `r2`...

## Changing a file the app saved

- Remove `cpm`. Set `milestones` to `[]`.
- Keep everything you are not changing exactly as it is, including keys this page does not mention (custom columns, baselines, time entries, costs, extra calendars).
- Changing a task: edit only the fields that change. If its duration changes, also update `durationDays`; leave its dates to the app.
- New task: next unused id, fields as above, placeholder dates, then fix `outlineNumber`, `outlineLevel` and `parentId` for the rows around it.
- Deleting a task: re-link what it sat between first. Then remove the task, every link and assignment that names it, its id from register `taskIds`, its entry in each baseline's `tasks`, and its `timeEntries`.
- Moving the start: change `meta.projectStart`.
- Save under a new file name. Never overwrite the original.

Some plans use things this page does not describe: part-day durations, other working hours, task calendars, manual scheduling, as-late-as-possible tasks, percentage lags. Leave those as they are. If a requested change touches one, make the change in the closest way this page allows, and tell the person to check that task in the app.

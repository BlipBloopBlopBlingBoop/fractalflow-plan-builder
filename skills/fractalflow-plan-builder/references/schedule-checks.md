# Schedule checks

What to look for when you review a plan, yours or theirs: why each item matters, how to fix it and when it is fine to leave it. Go through the plan against this list before handing it over. The short names are for your own working; tell the person what you found in plain words.

## How to weigh a finding

- **Must fix:** the file would not open or the plan would be wrong. Fix every one.
- **Usually fix:** something that usually makes dates wrong or the plan hard to run. Fix it, or decide to accept it and tell the person why.
- **Worth a look:** often fine. Use judgement and mention it only if it matters to this person.

Work in this order: what stops the file opening, then anything that changes dates (logic, float, deadlines, constraints), then anything that makes the plan hard to manage (owners, names, long tasks).

When you report to someone who does not plan for a living, translate. Not "three open-end findings" but "three tasks lead nowhere, so the plan would not notice if they slipped. I linked each to what it enables."

## Must fix

| Problem | Fix |
|---|---|
| Any rule in `file-format.md` broken: invalid JSON, a `cpm` block left in, an id that points nowhere, a milestone whose start and finish differ, a time other than 08:00 or 17:00 | Correct it. |
| Two rows share an id | Give the newer one the next unused id. |
| A row more than one level deeper than the row above | Fix the levels and `parentId`. |
| A task with no duration, or a milestone with one | Whole working days. A milestone has none. |
| A link to a phase, to the task itself, or to a task that is not there; a lag next to a calendar-day task | Link the tasks inside a phase. Put extra waiting in its own task. |
| Links that go round in a circle | Remove one link in the loop. |
| A dated constraint with no date, or a date before the project start | Add the date, move the start, or drop the constraint. |
| Progress that does not add up: a finish without 100 percent, a finished task with one real date | A finished task has both real dates. |
| A register entry with no title, or naming a task that is not there | Correct the entry. |

## Logic

**`open-start` (usually fix): tasks with no predecessor.**
Nothing says when they can begin, so they sit at the project start whether or not that is possible. The first task or a start milestone is the one allowed exception.
Fix: link each to the work or decision that lets it start. If it truly can start on day one, link it to a start milestone.

**`open-end` (usually fix): tasks with no successor.**
Nothing depends on them, so they show large float and can slip without the finish moving, even when in reality something is waiting for them.
Fix: ask what the task enables and link it there. If it only has to be done by the end, link it to the finish milestone.

**`finish-milestone` (worth a look): the plan ends on a task.**
Fix: add a final milestone that the last tasks lead to. The completion date then has a name and one place to put a deadline.

**`phase-link` (usually fix): links on phases.**
A link on a phase applies to everything under it and hides which task really drives the date.
Fix: link the tasks inside. For "after this phase", link from its last task or its closing milestone.

**`lead` (usually fix): negative lags.**
"Start two days before the predecessor finishes" depends on a finish date nobody knows yet, and it distorts float.
Fix: split the predecessor at the real hand-off, or use start-to-start with a positive lag.

**`lag` (worth a look; usually fix when common): lags on links.**
A lag is a wait nobody can see or own.
Fix: make it a task, in calendar days if it runs on the calendar. A short lag between tasks that run in step is acceptable; say why in the notes.

**`link-mix` (usually fix): few finish-to-start links.** **`start-to-finish` (usually fix).**
Plans built mostly from other link types are hard to follow and to update. Start-to-finish is nearly always a mistake.
Fix: use finish-to-start unless the tasks truly run in step.

**`redundant-link` (worth a look): a link repeats what a longer chain already says.**
Harmless to the dates, but clutter. Remove it.

**`duplicate-link` (usually fix): the same predecessor listed twice.** Keep one.

**`merge-point` (worth a look): several chains meet at one task.**
The more chains must all arrive, the more likely one is late. Consider margin before it, and watch it.

**`single-chain` (worth a look): every task is critical.**
The plan is one long chain. Either the work really is strictly serial, or links were added out of habit. Look for work that can run side by side.

**`path-broken` (usually fix): delaying the driving path does not move the finish.**
Something other than the work is holding the end date, usually a constraint on the last task.
Fix: replace it with a deadline.

## Dates and float

**`negative-float` (usually fix): tasks that cannot meet a date they are held to.**
A deadline or constraint is earlier than the logic allows. This is the plan reporting a problem, not a flaw in the plan.
Fix: find the date behind it, then shorten the path (see "Shortening a plan" in `planning-method.md`), move the date, or reduce scope. Never by trimming estimates without cause.

**`deadline-missed` (usually fix).** **`deadline-tight` (worth a look): two days of margin or less.**
Tell the person the size of the miss and the options. A tight deadline needs margin or a watchful owner.

**`high-float` (worth a look): more than 44 working days of float.**
Either real freedom, as in a side stream that only has to be ready by the end, or a missing successor. Check what each task feeds. If the float is real, say so and move on.

**`hard-constraint` (worth a look; usually fix when common): tasks pinned by `MSO`, `MFO`, `SNLT` or `FNLT`.**
Hard constraints hold dates still while the logic underneath breaks.
Fix: use a deadline for a target. Keep hard constraints for truly fixed outside dates, each with a note.

**`constraint-reason` (worth a look): a constrained task with no note.**
Add why the date is fixed and where it came from.

**`off-day-date` (worth a look): a deadline or constraint on a non-working day.**
Check the date or the calendar.

**`no-margin` (worth a look): the plan is held to a date but shows no margin.**
Add a contingency task before the committed milestone, sized to the risks.

**`no-holidays` (worth a look): months of work and no holidays in the calendar.**
Add public holidays and shutdowns.

## Tasks and structure

**`long-task` (worth a look; usually fix when common): longer than 44 working days.**
Progress on a long task is a guess until the end.
Fix: split work into steps that each end in something visible. A long wait on someone else's clock is fine if the clock is real.

**`no-owner` (usually fix): some tasks have no owner.** **`no-owners` (worth a look): none do.**
Unowned tasks do not get done on time. Give each one answerable owner. For a personal plan with one person doing everything, the note can stand.

**`workload` (worth a look): an owner has three or more tasks at once.**
Fine for a team. For one person, stagger the work or add help.

**`duplicate-name` (usually fix), `repeated-name` (worth a look), `vague-name` (usually fix).**
Names that repeat or say nothing make reports and conversations ambiguous. Use a verb and the thing it acts on.

**`single-child`, `deep-outline`, `flat-plan`, `few-milestones` (worth a look).**
Shape problems: a phase with one row, more than four levels, no phases at all, hardly any milestones. Adjust so the plan reads at a glance.

**`phase-field` (usually fix): a phase row carries fields it does not use.**
A phase takes its dates from its tasks. Put owners, deadlines and durations on tasks or on the phase's closing milestone.

## Estimates and risk

**`estimate-range` (usually fix): the range does not contain the duration.**
Optimistic must be at or below the duration, pessimistic at or above.

**`no-range` (worth a look): long critical tasks with no range.**
Ask how short and how long each could run. The spread is what margin and risk analysis rest on.

**`no-risks` (worth a look), `risk-gaps` (worth a look).**
No register, or risks with no owner or response. Record the few things most likely to move the dates and who will do what about each.

## Progress

These apply once the plan has a status date or any progress.

**`overdue` (usually fix): under way, and due to finish by the status date.**
The plan still shows the task ending in the past. Ask how many working days it still needs and record that (see Progress in `file-format.md`). Its finish and everything after it then move to where they really are.

**`not-started` (usually fix): could have started by the status date and shows no progress.**
Everything it was waiting for is done, and it has not begun. Record the start if it happened. If not, find out what is holding it and give it a start-no-earlier-than date for the day it can really begin. Tasks that are late only because something before them is late are not listed: they move when that is fixed.

**`actual-in-future` (usually fix): a real date after the status date.** One of the two dates is wrong.

**`out-of-sequence` (worth a look): started before a predecessor finished.**
The link was softer than drawn. Decide whether it is a real dependency.

**`progress-no-start` (worth a look): percent complete with no real start date.**
Add the real start date so the plan holds the task where it began.

**`no-status-date` (worth a look): progress recorded with no status date.** Set the status date.

## Other

**Unusual features:** the plan uses something `file-format.md` does not describe, such as part-day durations or task calendars. Leave those parts as they are, and tell the person to check the affected tasks in the app after a change.

**`starter-plan` (worth a look):** the file is one of FractalFlow's starter plans. Give the person's version its own name.

## Measures

For a project professional, use the measures of the DCMA 14-point assessment, a public standard from the US Defense Contract Management Agency that is widely used to judge how well a schedule is built. They are a starting point for judgement, not a pass mark: a small plan can miss a percentage target on one task, and a plan can meet every target and still be the wrong plan.

Unless the row says otherwise, tasks counted are those still to do, leaving out milestones and phases.

| Measure | What is counted | Target |
|---|---|---|
| Missing logic | Tasks with no predecessor or no successor, apart from the first and the last | At most 5% |
| Leads | Links with a negative lag | None |
| Lags | Links with a positive lag | At most 5% of links |
| Finish-to-start links | Share of links that are finish-to-start | At least 90% |
| Hard constraints | Tasks and milestones pinned by `MSO`, `MFO`, `SNLT` or `FNLT` | At most 5% |
| High float | Tasks with more than 44 working days of float | At most 5% |
| Negative float | Tasks with float below zero | None |
| Long tasks | Tasks longer than 44 working days (a calendar-day task counts five sevenths) | At most 5% |
| Invalid dates | Real dates after the status date; unfinished work scheduled before it | None |
| Tasks without an owner | Tasks with a duration and no owner | None |
| Missed tasks | Of tasks the baseline had finishing by the status date, those not finished or finished late | At most 5% |
| Critical path test | Whether the finish date moves when the driving path is delayed | It moves |
| Critical path length index | (Path length + float to the committed finish) / path length | At least 0.95 |
| Baseline execution index | Tasks finished / tasks the baseline had finishing by the status date | At least 0.95 |

Missed tasks and the baseline execution index need a baseline and a status date in the file. The critical path length index needs a deadline on the final milestone. Leave out a measure that does not apply.

With a project professional, give the measures that came out as "review" and what you did about each. With anyone else, the findings in plain words are enough.

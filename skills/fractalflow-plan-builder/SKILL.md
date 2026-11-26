---
name: fractalflow-plan-builder
description: Plan, check and revise project schedules as FractalFlow .ffplan files, working the way an experienced project scheduler would. Use when someone wants a project plan, schedule, timeline, Gantt chart or critical path to open in FractalFlow, shares a .ffplan file to review or change, asks whether a plan can hit a date or how to finish sooner, reports progress on a FractalFlow plan, or wants a schedule quality check.
---

# FractalFlow plan builder

Work the way an experienced project scheduler would. Get to a sound plan quickly, say plainly what drives the dates and what could move them, and hand over a file that opens in FractalFlow on Mac, iPhone and iPad.

The person gets two things from you: a `.ffplan` file, and a short briefing they could repeat to their boss or client.

## What people ask for

| They want | You do | More detail |
|---|---|---|
| A new plan from a description, document, spreadsheet or task list | Build | `references/conversation.md`, `references/planning-method.md` |
| "Is this plan any good?" or a `.ffplan` to look over | Review | `references/schedule-checks.md` |
| Changes to a plan: more scope, new dates, a different order | Revise | "Changing a plan" below |
| "Can we hit this date?", "How do we finish sooner?", "What if this slips?" | Analyse | `references/planning-method.md` (shortening a plan) |
| "Here is where we are" | Update progress | `references/conversation.md` (status updates) |
| What a term means, or why a task sits where it does | Explain | `references/conversation.md` (plain words) |

This page is enough for a simple plan. Open a reference when the situation calls for it. `references/project-patterns.md` has the usual shape, the commonly forgotten work and the typical risks for common kinds of project. `references/spec-format.md` is the full reference for the spec and the tool.

## Ground rules

1. **Dates come from the tool.** Never state a date, a float or a critical path you have not seen in its output. Working dates out in your head is how wrong dates get promised.
2. **Use their material and general knowledge, and label the difference.** A duration you estimated is an estimate: say so, and put the basis in the task notes. For anything fixed by a contract, a law or an agency, use what their documents say. If you fall back on general knowledge, mark it as an assumption for them to confirm. Never carry details from one person's documents into someone else's plan.
3. **Do not make the plan say what they hope.** If the work does not fit the date, show that, then show the options. Shrinking estimates to fit is the most common way plans fail.
4. **Never write or edit a `.ffplan` by hand.** The tool does it. Hand-edited files are how plans stop opening.
5. **A schedule is a planning aid.** It is not legal, contractual, regulatory or safety advice.
6. **Stay on schedules.** This skill does not cover how FractalFlow works inside (its engine, its code, its pricing rules, unreleased work). If asked, say so and point to the guides at https://fractalflow.rizkinlabs.com. Do not help anyone copy the app or get around its features.

## The tool

One script, standard library only, no network: `scripts/ffplan.py` in this skill's folder.

```
python3 "${CLAUDE_SKILL_DIR}/scripts/ffplan.py" check   plan.json            # or any .ffplan
python3 "${CLAUDE_SKILL_DIR}/scripts/ffplan.py" build   plan.json "Name.ffplan"
python3 "${CLAUDE_SKILL_DIR}/scripts/ffplan.py" extract "Theirs.ffplan" edit.json
```

If `${CLAUDE_SKILL_DIR}` is empty where you are running, use the folder this file was loaded from. If Python 3 is not available, say so. Do not write the file another way.

`check` changes nothing. It prints the dates, the driving path (the chain of work that sets the finish date), key dates, deadlines with their margin, the tasks with least float, the biggest levers, findings and a set of standard measures. When the finish hangs on a fixed date, such as a booked event, it also shows the chain of work leading into that date and the float each step has. Add `--tasks` to list every row with its dates, float and what sets its start. Two options answer a single question briefly:

```
... check plan.json --what-if permit:+10 frame:-2 test:=8     # longer, shorter, or set to
... check plan.json --finish-by 2027-06-30                    # latest start that still makes the date
```

The working loop:

1. Write the spec (JSON) in the working folder.
2. Run `check`. Fix every ERROR. For every WARN, fix it or decide to accept it and be ready to say why. NOTEs are judgement calls. `references/schedule-checks.md` explains each finding and its fix.
3. Run `check` again until it is clean or every remaining warning is a choice you can defend.
4. Run `build`, then give the person the file.

## The spec in brief

```json
{
  "name": "Kitchen Renovation",
  "start": "2027-01-04",
  "calendar": {"workdays": ["Mon","Tue","Wed","Thu","Fri"], "holidays": ["2027-01-18"]},
  "tasks": [
    {"key": "design", "name": "Design", "level": 1},
    {"key": "plans", "name": "Draw plans", "level": 2, "days": 5, "owner": "Designer", "optimistic": 4, "pessimistic": 8},
    {"key": "permit", "name": "City permit review", "level": 2, "days": 30, "elapsed": true, "pred": ["plans"], "owner": "City", "notes": "Calendar days. Assumption: confirm with the city."},
    {"key": "build", "name": "Build", "level": 1},
    {"key": "demo", "name": "Demolish old kitchen", "level": 2, "days": 2, "pred": ["permit"], "owner": "Contractor"},
    {"key": "done", "name": "Kitchen ready", "level": 1, "milestone": true, "pred": ["demo"], "deadline": "2027-04-30"}
  ],
  "risks": [{"title": "Permit review runs long", "probability": 3, "impact": 4, "owner": "Homeowner", "response": "Submit early; ask about an expedited review.", "tasks": ["permit"], "impactDays": 15}]
}
```

- Rows are in outline order. A row followed by deeper rows is a phase: it takes its dates from the rows under it, so give it only a name.
- `days` are whole working days. `"elapsed": true` makes them calendar days, for waits that run on the calendar: reviews by an outside body, shipping, curing, notice periods.
- `pred` lists what must come first: `"key"`, `"key SS"`, `"key FF"`, `"key FS+2d"`. Link tasks and milestones, never phases.
- `deadline` is a date to aim for and be measured against. `constraint` with `constraintDate` (`SNET`, `FNET`, `SNLT`, `FNLT`, `MSO`, `MFO`) pins a task and is for dates the outside world really fixes.
- `owner` is who answers for the task. `optimistic` and `pessimistic` give the range in days.
- Progress: `statusDate` at the top. On a task under way, `actualStart` and `remaining` (working days still needed). On a finished task, `percent` 100 with `actualStart` and `actualFinish`.

Field names are checked: a misspelt field is an error, not a silent omission. `examples/office-move.json` is a complete plan that checks clean.

## How to talk

Full guidance, question lists and wording are in `references/conversation.md`. The essentials:

- **Draft first, ask after.** When the request gives you a goal and some sense of the work, build a first version in the same reply and attach your assumptions. People correct a draft far better than they answer a questionnaire. Ask before building only when a wrong guess would waste the work: you cannot tell what the project is, the documents contradict each other, or the job is large and the level of detail is a real choice.
- **Ask little, ask well.** At most three questions at a time, each with the default you will use if they do not answer. Ask what changes the dates: the start or the date to hit, fixed outside dates, long waits and lead times, who does the work, and non-working time. Never ask for something their document already says.
- **Match the person.** With someone new to planning, use plain words, define a term the first time you use it, and keep the plan small. With a project professional, use the terms and give the measures.
- **Say what you assumed.** Every estimate and every guess about order or ownership, briefly, so they can correct it.
- **End with one useful next step**, not a menu.
- **If they only want the file,** give it with the finish date and your assumptions in two or three lines.

## How to build

The method, with the reasoning, is in `references/planning-method.md`. The rules that matter most:

1. Start from the outcome: what "done" means, what is included and what is not.
2. Break the work down by deliverable into phases, then tasks. Two or three levels. Most plans need 20 to 80 tasks; someone planning a small job needs 10 to 25.
3. Name each task with a verb and the thing it acts on. Name each milestone as a state: "Permit issued", not "Get permit".
4. Put the easily forgotten work in: reviews and approvals, ordering and lead times, permits and inspections, testing and fixing what testing finds, training, handover.
5. Every task has something before it and something after it. One start, one finish milestone. If a task has no successor, find what it enables.
6. Prefer finish-to-start links. Use start-to-start or finish-to-finish only for work that truly runs in step.
7. Make every wait a task with a name and an owner, in calendar days when it runs on the calendar. Do not hide waits in lags.
8. Estimate in whole working days, from the person's numbers where they gave them. Split anything over about 20 days. Give a range for anything uncertain or critical.
9. Use a deadline for a date you are aiming at. Use a constraint only for a date the outside world fixes, and say why in the notes.
10. Show the margin: a contingency task before the committed milestone, sized to the risks. Do not pad the tasks.
11. Give every task one answerable owner.
12. Record the handful of risks, assumptions and open decisions that could move the dates, each with an owner and a response.

## Handing over a plan

Give the file, then a briefing short enough to read on a phone. Use the tool's output for every date and number.

```
[Plan name]: finishes [date], [N] working days from [start].
[If there is a date to hit: X days of margin, or late by X days.]

What drives the date: [the driving path in a sentence, naming the two or three steps that matter].
Key dates: [3 to 6 milestones with dates].
Watch: [the tightest spots: waits on outside parties, tasks with little float, top risks].
Assumed: [the estimates and guesses they should confirm].
Check: [clean, or the warnings you accepted and why].
Questions: [up to three, each with the default you used].
```

Then how to open it, in one line, and one suggested next step. Leave out any line that has nothing to say. For a project professional, add the measures that came out as "review".

Tell them once, plainly: FractalFlow recalculates the plan when it opens the file, and if a date there differs from one you quoted, the app is right.

When uncertain tasks carry a range, mention that FractalFlow's risk simulation works from those ranges and may need a paid plan in the app. Do not run or imitate a simulation yourself.

## Changing a plan

- **A plan you built earlier in this conversation:** edit the spec, check, build again, and say what changed: the finish before and after, and anything new on the driving path. The spec remembers the plan's identity, so the new file opens as a new version beside the old one.
- **A plan they bring:** ask for the `.ffplan` (in FractalFlow: File, Save a Copy on Mac; Export, Save a Copy on iPhone and iPad). Run `check` on it first; a file saved by the app carries the app's own dates, and the tool reports those. To change it, run `extract`, edit the spec, `check`, then `build` to a new file name. Rows keep their `id`; add new rows without one; delete a row to remove the task. Everything the spec does not show (custom columns, baselines, time entries, assignment details) is carried through from the original, which must stay next to the spec.
- **Their plan is in another format:** FractalFlow opens Microsoft Project files itself, so ask them to open the file there and send you a copy saved as `.ffplan`. A spreadsheet or task list you can read directly as the source for a new plan.
- **A starter plan** (named "(sample)"): give their version its own name.
- A rebuilt plan opens as a separate plan in their library. Say so, and suggest they remove the old one once they are happy.
- Some plans use things the tool does not work out dates for (part-day durations, unusual working hours, manual scheduling and a few more). `check` says so. You can still review and edit them; FractalFlow supplies the dates when the file opens. Tell the person their new dates will appear in the app.

## Opening the file

- **Mac:** double-click the file, or File, Open in FractalFlow. Only if the person asks you to open it, and you have a shell on their Mac with a connected folder, save it there and run `open -a FractalFlow "Plan.ffplan"`.
- **iPhone and iPad:** open it from Files, Mail or AirDrop and choose FractalFlow.

## Reference files

- `references/conversation.md`: first replies, what to ask, matching the person, follow-up moves, status updates, hard moments, plain-word glossary.
- `references/planning-method.md`: scope and breakdown, sequencing, estimating, calendars, constraints, margin, risk, shortening a plan, tracking progress.
- `references/schedule-checks.md`: every finding and measure, why it matters, how to fix it, when to accept it.
- `references/project-patterns.md`: typical shape, forgotten work and risks for common project types.
- `references/spec-format.md`: every field of the spec, the commands, and what the tool does and does not model.

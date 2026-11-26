# Planning method

How to turn a goal into a schedule that can be trusted, and how to keep it that way. This is common scheduling practice, written down in the order you use it.

## 1. Start from the outcome

Before any task, be able to say in a sentence:

- **What is delivered.** The thing, the service, the event, the decision.
- **What "done" means.** Accepted by whom, against what.
- **What is outside this plan.** Stating the exclusions prevents half the later arguments.

If you cannot say these, ask. A plan with a vague end has a vague finish date.

## 2. Break the work down

Divide by what is produced, not by who does it or when.

- **Phases** (level 1): the big stages or deliverables. Three to eight is typical.
- **Work packages** (level 2, optional): parts of a phase that one person or crew can own.
- **Tasks**: the lowest level, where work is estimated, owned and linked.

Rules:

- Everything under a phase adds up to the whole phase. If work is not under any phase, a phase is missing.
- Two levels suit most plans. Three for larger ones. Past four, people stop reading.
- A phase with one task under it is not a phase.
- Size tasks so that progress is visible. A useful range is 1 to 20 working days. Shorter than a day is a checklist item; longer than a month hides trouble.
- Keep the task count in proportion: 10 to 25 for a small job, 20 to 80 for most projects, more only when the person needs that detail to run the work.

**Near and far.** Plan the next two or three months in detail. Further out, a few larger tasks per phase are honest; mark them in the notes as "to be detailed" and break them down when they come closer.

## 3. Name things well

- **Tasks:** a verb and the thing it acts on. "Install kitchen cabinets", "Review vendor contract". Not "Cabinets", not "Review".
- **Milestones:** a state that is either true or not. "Permit issued", "Design approved", "Site handed over".
- No two tasks with the same name. In a filtered list they are indistinguishable. Add what differs: "Test payment flow", "Test reporting".
- No placeholders ("TBD", "Misc", "Other"). If you do not know what the work is, say so in a named task: "Define data migration approach".

## 4. Put in the work people forget

Most late projects are late because of work nobody listed. Check for:

- **Decisions and approvals**, with the time the approver really takes, including a round of comments.
- **Ordering and lead times**: materials, equipment, licences, hires.
- **Permits, inspections and outside reviews**, and the time to answer what they come back with.
- **Access and readiness**: the site, the environment, the data, the people.
- **Testing, and fixing what testing finds.** One pass is rarely enough.
- **Training, communication and documentation.**
- **Handover, sign-off, close-out**, and getting paid.
- **Moving in, switching over, cleaning up.**

`project-patterns.md` lists the usual omissions by kind of project.

## 5. Sequence the work

For each task ask two questions: what must be true before this can start, and what does finishing it make possible.

- **Every task has a predecessor and a successor.** The exceptions are the first task and the final milestone. A task with no successor can slip forever without the plan noticing; a task with no predecessor is not really scheduled.
- **One start, one finish.** End the plan on a single finish milestone that the last tasks lead to.
- **Finish-to-start by default.** It is the easiest to read and to update.
- **Start-to-start or finish-to-finish** only when two tasks truly run in step, such as writing and reviewing in rolling batches.
- **Start-to-finish** is almost never what is meant. If you find one, check the direction.
- **Link tasks, not phases.** A link on a phase hides which task really drives the date.
- **No redundant links.** If A leads to B and B leads to C, a direct link from A to C adds nothing.
- **Tell hard logic from preference.** "The slab must cure before framing" is physics. "We usually do the kitchen before the bathrooms" is a choice. When time is short, choices are where you look first.
- **Do not chain everything.** If two tasks do not depend on each other, do not link them just because one person imagined doing them in that order. Parallel work is where float comes from.

**Lags and leads.**

- A lag is a wait hidden inside a link. Prefer a task: "Concrete cures (7 calendar days)" can be seen, owned and questioned. A small lag between tasks that run in step is acceptable; say why in the notes.
- A lead (negative lag) says "start before the predecessor finishes" without saying when it is safe to. Split the predecessor at the real hand-off point, or use start-to-start with a positive lag.
- Never put a lag next to a calendar-day task. Put the extra wait in its own task.

## 6. Estimate durations

Use whole working days.

- **Their number first.** If they or their document give a duration, use it and note the source.
- **By comparison:** how long did this take last time?
- **By quantity:** amount of work divided by rate (rooms per day, pages per week), when both are known.
- **By range:** ask for the best case, the likely case and the worst case. Use the likely case as `days` and record the others as `optimistic` and `pessimistic`. Do this for anything uncertain, anything on the driving path, and anything long.

Rules:

- **Duration is not effort.** Three days of work by someone who has one day a week for it is a three-week task.
- **Do not pad.** If you add safety to every task, nobody can see it, nobody can manage it, and it gets used anyway. Estimate honestly and show the margin separately (section 10).
- **Say what the estimate rests on** in the notes: "Estimate, based on two review rounds." When you made the number up from general knowledge, say that too.
- A milestone has no duration. A review has one.

## 7. Waits and calendar time

Work happens on working days. Waiting usually does not care what day it is.

Use `"elapsed": true` (calendar days) for:

- Reviews by outside bodies with a stated clock.
- Shipping and delivery lead times.
- Notice periods and cooling-off periods.
- Curing, drying, settling, incubating.
- A switchover or a move done across a weekend.

Give every wait an owner: the party you are waiting on. Record where the number came from. If it rests on general knowledge of how long such things take, mark it as an assumption to confirm, because these numbers change and they often sit on the driving path.

## 8. The calendar

- Set the working week if it is not Monday to Friday.
- Add public holidays and shutdowns as `holidays`. A plan that runs for months without them is optimistic by days.
- Seasonal limits (weather, term dates, freezes) are either holidays, if nobody works, or a start-no-earlier-than date on the affected task, with a note.

Plans you write use whole working days of eight hours and one calendar for the whole plan. Other working hours and task calendars can be set in FractalFlow once the plan is open.

## 9. Deadlines and constraints

Two different things:

- **A deadline** is a date you are measured against. It does not move the task. If the task runs past it, the plan shows the miss and the float goes negative. Use it for every committed date.
- **A constraint** pins the task. Use it only for dates the outside world fixes.

| Constraint | Meaning | Typical use |
|---|---|---|
| `SNET` start no earlier than | Cannot start before the date | Space available from, funding released on, vendor arrives on |
| `FNET` finish no earlier than | Cannot finish before the date | A notice period must run out first |
| `SNLT`, `FNLT` no later than | Must start or finish by the date | Rarely needed: a deadline says the same and reads better |
| `MSO`, `MFO` must start or finish on | Fixed to the date | A booked event, an outage window |

Rules:

- Prefer logic to dates. "Starts after the permit" is better than "starts on 14 March", because it moves when the permit moves.
- Every constraint gets a note saying why and where the date came from.
- Hard constraints (`MSO`, `MFO`, `SNLT`, `FNLT`) hide problems: they hold a date in place while the logic behind it breaks. More than a few is a warning sign.
- Never constrain the finish milestone to make the plan end on the hoped-for date. Put a deadline on it and look at the margin.

**When the whole plan serves a fixed date** (an event, an opening, an outage window): end the preparation on a readiness milestone, such as "Ready for the conference", and give it a deadline the day before. If the plan continues past the date, add the event itself as a task pinned with `MSO` and say in its notes why the date is fixed. Then work out the chain of work into the fixed date, the float each step has, and the latest safe start.

## 10. Margin

Uncertainty is real, so plan for it where it can be seen.

- Add a task named for what it is, such as "Schedule contingency", directly before the committed milestone, owned by whoever runs the project.
- Size it to the risks on the path: the spread between likely and pessimistic on the tasks that lead there is a good guide. For a first plan with little data, 10 to 15 percent of the path is a common starting point.
- For a long plan, put smaller margins before major intermediate milestones as well.
- Margin is spent by decision, not by drift. Say so in its notes.

Where several chains meet at one task, the chance that at least one arrives late is higher than for any one of them. These merge points deserve margin too.

## 11. Owners and load

- One answerable owner per task. A team name is fine when the team is the unit that commits.
- For a wait, the owner is whoever you are waiting on.
- Look at what each owner carries at once. Watch for anyone with three or more overlapping tasks. For a crew that may be normal; for one person it is a plan that will not hold.
- The fix for overload is to move work, add people, or accept a later date. FractalFlow can level resources once the plan is open, which may need a paid plan in the app.

## 12. Risks, assumptions, decisions

Keep a short register in `risks`: the few things most likely to move the dates.

- **Risk:** something that may happen. Rate probability and impact from 1 to 5. Name an owner and a response.
- **Assumption:** something the plan takes as true without proof. If it turns out false, the plan changes.
- **Issue:** a problem that has already happened.
- **Dependency:** something outside the plan that it relies on.
- **Decision:** a choice that is still open, or one worth recording.

Responses to a risk: avoid it (change the plan so it cannot happen), reduce it (make it less likely or less harmful), transfer it (insurance, contract terms), or accept it and hold margin. Whatever you choose, if the response takes work, put that work in the plan as tasks.

Link each entry to the tasks it touches, and give a risk its likely delay in `impactDays` when you can estimate it.

## 13. Read the result

After working out the dates:

- **The driving path** is the chain that sets the finish date. Read it aloud. Does it make sense that this, of all things, decides the date? If not, a link is wrong or missing.
- **Float** is how far a task can slip before the finish moves. Zero float means critical. A few days of float means nearly critical, and nearly critical paths become critical the moment something slips.
- **Negative float** means a deadline or constraint cannot be met as planned. The plan is telling you about a decision that has to be made.
- **Very large float** is either real freedom, in a side stream that only has to be ready by the end, or a missing link.
- Outside waits on the driving path are where to push first: can the wait start sooner, be shortened, or be run alongside something else?

## 14. Shortening a plan

When the finish is too late, work down this list. Each step costs more than the one before.

1. **Check the logic.** Remove links that are habit rather than necessity. Free.
2. **Start long waits earlier.** Order, apply, submit as soon as their real inputs exist, not when the previous phase ends. Nearly free.
3. **Run independent work side by side.** Costs coordination.
4. **Overlap dependent tasks** where the later one can begin on partial results. Costs rework if the early results change.
5. **Add capacity to tasks on the driving path** where more hands shorten the work. Costs money, has limits, and does little for work that cannot be divided.
6. **Change the calendar:** overtime, weekends, a second shift. Costs money and wears people out.
7. **Deliver in stages.** Put the essential scope before the date and the rest after.
8. **Cut or simplify scope.**
9. **Move the date.**

How to do it:

- Only changes on the driving path move the finish. BIGGEST LEVERS shows how many days each step on it is worth.
- After each change, check again. Shorten one chain and another usually becomes the driving one.
- Try a change in your date table before changing the plan.
- Tell the person what each option gains, what it costs and what risk it adds. The choice is theirs.
- Never get there by cutting estimates without a reason for the work to go faster.

## 15. Tracking progress

Once work starts, the plan is kept true by recording facts.

- Set the status date: the day the facts were gathered.
- **Finished:** 100 percent with the real start and finish.
- **Under way:** the real start and the working days still needed as of the status date. The task's length becomes the time already spent plus what is left (`file-format.md` shows how), so its finish, and everything after it, sits where it really is. This is better than a percent: percent says how much is done, and only the days remaining say when it will end.
- **Not started, and should have been:** it cannot stay scheduled in the past. Find out when it can start, and why it has not.
- Work done out of order is a sign that a link was a preference, not a need. Decide which and fix the link.

After each update, compare: the finish date now and before, the driving path now and before, and which deadlines lost margin. That comparison is the status report.

Save a baseline in FractalFlow when the plan is agreed, and again whenever the agreed plan changes. A baseline is what makes "we are two weeks later than planned" a statement of fact.

## 16. Changing an agreed plan

Once people have committed to dates, changes to scope or dates are decisions, not edits.

- Say what is changing and why.
- Show the effect on the finish and on each committed date.
- Get agreement from whoever owns the date.
- Record it as a decision in the register, then update the plan and, in FractalFlow, the baseline.

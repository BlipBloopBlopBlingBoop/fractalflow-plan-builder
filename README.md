# FractalFlow Plan Builder

Plan, check and revise project schedules with Claude, then open them in FractalFlow on Mac, iPhone and iPad.

Describe a project, or attach a contract, a statement of work, a spreadsheet or a task list. Claude builds a critical-path schedule the way an experienced project scheduler would, checks it, tells you what drives the finish date and what could move it, and gives you a `.ffplan` file.

## What it does

- **Builds a plan** from a description or a document: phases, tasks, milestones, links, owners, waits in calendar days, deadlines, a working calendar with holidays, ranges for uncertain work, and a short risk register.
- **Checks the plan** before you see it: missing links, loops, tasks nothing depends on, missed deadlines, negative float, hidden waits, long or unowned tasks, and the standard schedule-quality measures used in the DCMA 14-point assessment.
- **Explains it:** the chain of work that sets the finish date, the key dates, the margin against each deadline, and where the plan is tight.
- **Answers questions:** what if the permit takes three more weeks, when is the latest we can start, which steps are worth shortening.
- **Revises a plan you already have.** Send a `.ffplan` saved from FractalFlow. Claude reviews it, changes what you ask, and returns a new file. Whatever it does not change (custom columns, baselines, time entries) is kept as it was.
- **Records progress** from a status update and tells you what moved.

## Example prompts

- "Build a FractalFlow plan for opening a restaurant, starting Monday 4 January. Include permits, build-out, hiring and a soft opening."
- "Here is our statement of work. Make a FractalFlow schedule from it, with the contract dates as deadlines."
- "We have to open on 1 June. When is the latest we can start, and what is on the critical path?"
- "What happens to the finish date if the permit review takes 15 more working days?"
- "Review the attached plan and tell me the five things you would fix first."
- "Demolition and framing are done, plumbing is half done as of Friday. Update the plan and tell me the new finish."

## What you get

A `.ffplan` file and a short briefing: the finish date, what drives it, key dates, what to watch, what was assumed, and any questions. Open the file by double-clicking it on a Mac, or from Files, Mail or AirDrop on iPhone and iPad.

FractalFlow schedules the plan when it opens the file. If a date there differs from one Claude quoted, the app is right.

## What it contains

The plugin is one skill: instructions and reference pages in Markdown, and one example plan in JSON. It contains no scripts or programs, no hooks, no servers and no connectors, and it sends nothing anywhere.

Claude writes the `.ffplan` file itself in its working folder, following the format in the skill. When you send a `.ffplan` to review or change, Claude reads that file. If Claude can run code where you use it, it may write its own short calculations to work out the dates it quotes.

One more thing Claude may run, and only if you ask it to open the plan while it has access to your Mac: the macOS command `open -a FractalFlow` on the file it just wrote.

## Requirements

- The FractalFlow app to open the file: https://fractalflow.rizkinlabs.com
- A Claude app that can create files for you to download.

## Limits

- A schedule is a planning aid. Claude builds it from what you provide and from general knowledge, and marks its estimates as estimates. Check durations, lead times and any date set by a contract or a regulator before you rely on the plan.
- The dates Claude quotes are its forecast. FractalFlow schedules the plan when it opens the file, and those are the real dates.
- Durations are whole working days of eight hours, with one calendar for the plan. Finer settings are made in FractalFlow.
- The plugin does not do resource leveling, cost or risk simulation. FractalFlow does, and some of those features need a paid plan in the app.

## Privacy and support

The plugin uses only what you give Claude in the conversation. Rizkin Labs receives none of it. Details: https://fractalflow.rizkinlabs.com/plan-builder/#privacy

Guide, examples and troubleshooting: https://fractalflow.rizkinlabs.com/plan-builder/

Support: hello@rizkinlabs.com, or the issues tab of this repository.

Published by Benjamin Rizkin, doing business as Rizkin Labs. MIT license.

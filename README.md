# FractalFlow Plan Builder

A Claude skill that turns a project description, contract, statement of work or spreadsheet into a `.ffplan` schedule you can open in the FractalFlow app on Mac, iPhone and iPad.

## Use

Ask Claude for a plan, for example: "Build a FractalFlow plan for opening a restaurant, starting January 4" or attach a statement of work and ask for a schedule. Claude returns a `.ffplan` file and a short list of its assumptions.

Open the file by double-clicking it on a Mac, or with Open With FractalFlow from Files, Mail or AirDrop on iPhone and iPad. FractalFlow schedules the plan when it opens it.

## Example prompts

- "Build a FractalFlow plan for opening a restaurant, starting Monday January 4. Include permits, build-out, hiring and a soft opening."
- "Here is our statement of work (attached). Make a FractalFlow schedule from it, with the contract dates as deadlines."
- "Create a FractalFlow plan for a kitchen renovation: demolition, rough-in plumbing and electrical, inspection, cabinets, finish. Show the risks."
- "Turn this spreadsheet of tasks and durations into a FractalFlow plan."

## Notes

- Claude builds from what you provide or from public sources. Review durations and links before relying on the plan.
- The plugin needs Python 3 in the environment where Claude runs.
- This plugin only creates plan files. It does not include or expose the FractalFlow app.

## Privacy and support

The plugin has no server, no account and no analytics, and it makes no network requests. It uses only what you give Claude in the conversation. Full details: https://fractalflow.rizkinlabs.com/plan-builder/#privacy

Support: hello@rizkinlabs.com or the issues tab of this repository. Guide, examples and troubleshooting: https://fractalflow.rizkinlabs.com/plan-builder/

Published by Benjamin Rizkin, doing business as Rizkin Labs. FractalFlow: https://fractalflow.rizkinlabs.com

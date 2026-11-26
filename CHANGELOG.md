# Changelog

## 1.1.0

- New plan tool, `scripts/ffplan.py`, replacing `build_ffplan.py`. Commands: `check`, `build`, `extract`.
- The tool works out dates, float and the driving path itself, so Claude can discuss a plan before it is opened in FractalFlow.
- Schedule checks with fixes, and the standard measures of the DCMA 14-point assessment.
- `--what-if` and `--finish-by` for single questions; a list of the steps most worth shortening.
- Working week and holidays, calendar-day tasks, progress and a status date in the spec.
- Existing plans can be reviewed and revised. Anything the spec does not show is carried through from the original file.
- Field names in a spec are checked, so a misspelt field is an error.
- The skill now covers how to run the conversation, a planning method, every check, and patterns for common project types.

## 1.0.0

- First version: builds a `.ffplan` from a simple spec.

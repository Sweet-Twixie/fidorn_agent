# Write-up: tax intake browser agent

## How the agent works
Three modules with separate jobs. `browser.py` (Playwright) opens the app, finds its frame,
reads the questions on screen, clicks, types and exports; it knows nothing about tax.
`brain.py` sends the client PDF plus a batch of on-screen questions to Claude
(claude-sonnet-5) and gets JSON answers back; it never touches the browser. `runner.py`
connects them: fill the header, decide which of the 12 sectors apply, then loop through
each applicable sector, and finally export the workbook's own JSON.

## Finding questions revealed by earlier answers
Each sector runs a look → think → act loop. The runner clicks "Expand all", reads every
choice question and text box on screen, and keeps only those not in an `asked` set. It
sends that batch to Claude, clicks choices first (they can reveal questions), then types
text. It repeats until a round finds nothing new (8-round safety limit). Most sectors
finish in 2–3 rounds. Before clicking, answers are checked against the real question ids
and options, and a button's `aria-pressed` state is checked so a selected option is never
clicked off again. Elements that disappear mid-round are skipped rather than waited on.

## Handling the embedded frame
The app runs in a cross-origin iframe on claude.ai. Playwright can reach any frame, so
the agent polls `page.frames` every second (up to 30 s) and uses the frame that contains
the client-name field `#m-client`. All actions then go through that frame.

## Reliability and error handling
The whole fill runs inside try/except, and the form is exported even after an error,
since a partial form scores points. API errors and malformed JSON are retried; a round
with no answers is retried instead of silently skipped. A final sweep asks Claude which
important figures from the file were never typed, and adds them to the relevant
"Preparer notes" box, as a preparer would record details that fit no specific field.

## Results
| Version | 01 | 02 | 03 | Mean |
|---|---|---|---|---|
| First complete version | 93.3 | 93.0 | 99.0 | 95.1 |
| + final sweep for missed figures | 93.3 | 100.0 | 99.0 | 97.4 |

Across repeated runs, case 01 varied between [91.3] and [93.3]. A formal 3×3 reliability
run was cut short by a laptop crash, so variance figures come from my ad-hoc repeats.

## Where it fails
- **Life events (case 01):** picks "Moved" (true from the address history) instead of
  "Started a business" as listed on the file's "Life events" line.
- **Unmentioned No answers:** sometimes leaves Yes/No questions blank when the file
  implies "No" (e.g. no property sale); run-to-run variation decides this.
- **Sector selection:** marks one extra sector Yes in case 03.
- **Prompt sensitivity:** new rules aimed at these misses plus a stricter sector prompt
  dropped case 01 to 59 (three sectors wrongly marked No), so I reverted. Lesson: change
  one thing at a time and re-run every case.

## What I'd do next
Give Claude each text box's full section path for better placement; split large rounds
into smaller batches; majority-vote across 2–3 calls to reduce variance; test every sector
with synthetic cases, since the practice cases only cover sectors 1, 2, 3, 4, 9, 10 and 11;
use prompt caching for the PDF to cut cost; add offline tests with a fake Claude.


## Time and tools
About 6 hours. I built this with help from an AI assistant (Claude) for explanations,
code and debugging; I ran, tested and debugged every step myself.
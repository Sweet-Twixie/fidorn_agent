# Take-home: build a browser agent that completes a tax intake

## The task

Build an agent that reads a client's tax file (a PDF) and fills in the matching intake in a web app, using a real browser.

- **Web app:** https://claude.ai/artifact/F3cXVQQCWCeon9QLjKJojQ#blank
- **Input:** one PDF client file, like the three in `practice-cases/`
- **Output:** the workbook's JSON export for that client (Export answers → JSON)

Your agent must work on client files it has never seen. We will run it on a set of hidden cases in the same style as the practice cases, but for different kinds of clients.

All clients, businesses and ID numbers are fictional.

## What the agent has to do

1. Open the app with `#blank` on the end of the link, in a fresh browser profile.
2. Fill in the engagement header: client name, tax year 2025, and anything else known.
3. For each of the 12 sectors, answer "Does this sector apply to the client?"
4. In each sector that applies, answer the Yes/No, single-choice and "select all that apply" questions. Many answers reveal more questions, some only when a specific combination is ticked, so the agent needs to notice new questions as they appear.
5. Type the relevant facts and figures from the PDF into the free-text fields where they belong.
6. Export the answers as JSON and save the file.

Heads-up: on claude.ai the app runs inside an embedded, cross-origin frame. Handling that is part of the task.

## What's in this packet

| Path | Use |
|---|---|
| `practice-cases/` | Three client PDFs to develop against |
| `practice-answers/` | The same three PDFs with the expected workbook answers at the end, plus `answers.json` |
| `score.py` | The scoring script we use (Python 3, no dependencies) |

Score your runs like this:

```
python score.py runs/          # expects runs/01.json, 02.json, 03.json
python score.py 2 runs/02.json # one case
```

Each case is worth 100 points:

| Part | Points |
|---|---|
| Sectors marked correctly | 10 |
| Header | 5 |
| Choice and multi-select answers | 50 |
| Key figures typed in | 35 |

## What to submit

1. **Code** in a git repo or zip, with a README that tells us how to run it:
   `run_agent <path/to/case.pdf> <path/to/output.json>`
   List any API keys, models or browsers it needs. We supply our own keys.
2. **Your three practice outputs** (`01.json`, `02.json`, `03.json`) and their scores.
3. **A short write-up** (one page at most) covering:
   - how the agent works
   - how it finds questions revealed by earlier answers
   - how it handles the embedded frame
   - where it fails and what you'd do next
   - approximate cost and run time per case

## Rules

- The agent must work through the browser, clicking and typing like a person would. Don't write to the page's local storage, run scripts that change the page's data, or build the JSON export yourself.
- Don't hard-code anything specific to the practice cases: names, figures or answers.
- You may use any model, framework or browser automation library.
- Time box: about 6 hours. Tell us roughly how long you spent.

## How we evaluate

- **Hidden-case score (60%):** your agent run on our hidden cases, three runs each, averaged.
- **Reliability (15%):** how much the score varies between runs, plus crashes and time-outs.
- **Engineering (15%):** code clarity, how easy it was to run, and how errors are handled.
- **Write-up (10%):** an honest account of what works and what doesn't.

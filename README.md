# Tax intake browser agent

Reads a client's tax file (PDF) and completes the Tax Client Intake Workbook through a real
browser, then saves the workbook's own JSON export.

## Requirements

- Python 3.10+
- An Anthropic API key (model: `claude-sonnet-5`)
- Chromium via Playwright (falls back to Microsoft Edge automatically if Chromium isn't installed)

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

Create a file named `.env` in the project folder:

```
ANTHROPIC_API_KEY=your-key-here
```

## Run

```bash
python run_agent.py <path/to/case.pdf> <path/to/output.json>
```

Example:

```bash
python run_agent.py tax-intake-candidate-packet/practice-cases/01-varga-household.pdf runs/01.json
python tax-intake-candidate-packet/score.py runs/
```

A browser window opens and fills the form; don't click in it while it runs.
Each case takes about [X] minutes. Every prompt and reply is logged to `runs/claude_log.txt`.

## How the code is organised

| File | Role |
|---|---|
| `run_agent.py` | Command-line entry point |
| `agent/browser.py` | Browser actions (Playwright): open the app, find its embedded frame, read questions, click, type, export |
| `agent/brain.py` | Claude calls: PDF + on-screen questions in, JSON answers out |
| `agent/runner.py` | The agent loop: read screen → ask Claude → act → repeat until no new questions, then a final sweep for missed figures |
| `run_reliability.py` | Runs each practice case 3 times and summarises the scores |

## Practice results

| Case | Score |
|---|---|
| 01 Varga household | [..] |
| 02 Priya Raman | [..] |
| 03 Okonkwo landscaping | [..] |
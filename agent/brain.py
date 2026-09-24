import base64
import json
import re
import time
import traceback

import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()
MODEL = "claude-sonnet-5"

RULES = """You fill in a tax intake form for ONE client, using only their file (the attached PDF).

ACCURACY
- Use only facts stated in the file. If the file doesn't cover a question, leave it out. Never guess.
- Answer for tax year 2025, unless the question is about another year (e.g. an old IRS notice).
- Don't infer one fact from another (buying a property does not mean the client moved).

CHOICE QUESTIONS
- Copy option text EXACTLY from the options given.
- "Select all that apply": check the options one by one. Include each option the file clearly
  supports, including things mentioned only in notices, letters or side notes. Don't include
  an option just because it could plausibly apply.

TEXT BOXES
- Write short factual answers: what, who, amounts, dates.
- Copy every figure exactly as written in the file, with commas (96,480). Don't round or reformat.
- Include names, addresses and dates as written.
- If an important figure doesn't fit any specific box, put it in the most relevant
  "Preparer notes" box with a few words saying what it is.

OUTPUT
- Reply with JSON only. No explanation, no markdown.
- Don't use double quotes inside text answers (write 24 in, not 24")."""

def load_pdf(path):
    """Read the PDF and wrap it the way the API expects."""
    data = base64.standard_b64encode(open(path, "rb").read()).decode()
    return {"type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": data}}


def ask_json(pdf, question):
    """Send the PDF + a question to Claude and return its answer as a Python dict."""
    for attempt in range(3):
        try:
            msg = client.messages.create(
                model=MODEL, max_tokens=16000, system=RULES,
                messages=[{"role": "user", "content": [pdf, {"type": "text", "text": question}]}],
            )
        except anthropic.APIError as e:          # e.g. "overloaded": wait and try again
            print("API error, retrying:", e)
            time.sleep(5)
            continue

        text = "".join(b.text for b in msg.content if b.type == "text").strip()
        start, end = text.find("{"), text.rfind("}")   # keep only the {...} part
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError as e:
                print("JSON error:", e)

        print(f"Bad reply (stop_reason={msg.stop_reason}, {len(text)} chars). Ends with: ...{text[-200:]}")
    return {}                              

def find_missing(pdf, typed_texts, notes_boxes):
    """Ask Claude which important figures from the file were never typed, and where to note them."""
    return ask_json(pdf,
        "Below is everything already typed into the intake form, followed by the available "
        "Preparer notes boxes.\n"
        f"ALREADY TYPED: {json.dumps(typed_texts)}\n"
        f"NOTES BOXES: {json.dumps(notes_boxes)}\n"
        "Find the important figures in the client file (amounts, key numbers, addresses) that do "
        "NOT appear anywhere in the typed text. For each, write a short note with a label, "
        "e.g. 'W-2 Box 1 wages 96,480'. Put each note in the most relevant notes box.\n"
        'Return {"box id": "notes text", ...}. Return {} if nothing important is missing.')


def get_header(pdf):
    return ask_json(pdf, 'Return {"client": full client or business name, '
                         '"tin": last 4 digits of SSN or EIN, '
                         '"summary": one sentence on why they came in and what they need}.')


def which_sectors(pdf, sectors):
    listing = "\n".join(f'{s["id"]}: {s["name"]}' for s in sectors)
    return ask_json(pdf, f"Which of these tax areas apply to this client?\n{listing}\n"
                         'Return JSON mapping every id to "Yes" or "No", e.g. {"1": "Yes", "2": "No"}.')


def answer_questions(pdf, choices, texts):
    """choices and texts come straight from read_choices() and read_texts() in browser.py."""
    return ask_json(pdf,
        "Answer these questions for this client.\n"
        f"CHOICE QUESTIONS: {json.dumps(choices)}\n"
        f"TEXT BOXES: {json.dumps(texts)}\n"
        'Return {"choices": {question id: option, or a LIST of options if multi is true}, '
        '"texts": {box id: answer text}}. Leave out anything the file does not cover.')


# ---- Quick test on case 01 (no browser) ----
if __name__ == "__main__":
    pdf = load_pdf("tax-intake-candidate-packet/practice-cases/01-varga-household.pdf")
    print("HEADER:", get_header(pdf))

    sectors = [{"id": "1", "name": "Individual & Family"}, {"id": "2", "name": "Self-Employed & Small Business"},
               {"id": "3", "name": "Corporations & Partnerships"}, {"id": "4", "name": "Real Estate & Rentals"},
               {"id": "11", "name": "IRS Representation & Disputes"}]
    print("SECTORS:", which_sectors(pdf, sectors))

    fake_choices = {"status": {"question": "Filing status on December 31",
                               "options": ["Single", "Married filing jointly", "Married filing separately"],
                               "multi": False}}
    print("ANSWER:", answer_questions(pdf, fake_choices, {}))
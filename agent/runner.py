import traceback

from playwright.sync_api import sync_playwright

from agent.brain import answer_questions, find_missing, get_header, load_pdf, which_sectors  # NEW: find_missing
from agent.browser import (click_option, export_json, fill_header, list_sectors,
                           open_sector, read_choices, read_texts, start_browser, type_text)

MAX_ROUNDS = 8   # safety limit, so a sector can never loop forever
typed = {}       # NEW: box id -> text we typed, used by the final sweep


def run(pdf_path, out_path):
    typed.clear()                              # NEW: start each run with an empty record
    pdf = load_pdf(pdf_path)
    with sync_playwright() as p:
        browser, app = start_browser(p)
        try:
            fill_everything(app, pdf)
        except Exception:
            # A half-filled form still scores points; a crash scores zero.
            print("ERROR - exporting what we have so far:")
            traceback.print_exc()
        result = export_json(app)
        browser.close()
    open(out_path, "w").write(result)
    print("Saved", out_path)


def fill_everything(app, pdf):
    header = get_header(pdf)
    print("Header:", header)
    fill_header(app, client=header.get("client", ""), tin=str(header.get("tin", "")),
                summary=header.get("summary", ""))

    sectors = list_sectors(app)
    applies = which_sectors(pdf, sectors)
    print("Sectors:", applies)

    for s in sectors:
        open_sector(app, s["id"])
        answer = "Yes" if applies.get(s["id"]) == "Yes" else "No"
        click_option(app, f"applies:{s['id']}", answer)
        if answer == "Yes":
            fill_sector(app, pdf, s["id"])

    yes_sectors = [s["id"] for s in sectors if applies.get(s["id"]) == "Yes"]   # NEW
    sweep_missing(app, pdf, yes_sectors)                                         # NEW


def fill_sector(app, pdf, sector_id):
    asked = set()   # ids of questions we've already sent to Claude
    for round_no in range(1, MAX_ROUNDS + 1):
        # 1. LOOK: what's on screen that we haven't asked about yet?
        choices = {q: c for q, c in read_choices(app).items()
                   if q not in asked and not q.startswith("applies:")}
        texts = {k: label for k, label in read_texts(app).items() if k not in asked}
        if not choices and not texts:
            print(f"Sector {sector_id}: done after {round_no - 1} rounds")
            return
        print(f"Sector {sector_id} round {round_no}: {len(choices)} choices, {len(texts)} text boxes")

       
        answers = answer_questions(pdf, choices, texts)
        if not answers:                                                    # NEW
            print(f"Sector {sector_id}: no answers this round, trying again")
            continue                           # don't mark as asked; the next round retries
        asked.update(choices)
        asked.update(texts)

        
        for qid, picked in (answers.get("choices") or {}).items():
            if qid not in choices:
                continue                       
            options = picked if isinstance(picked, list) else [picked]
            for option in options:
                if option in choices[qid]["options"]:
                    click_option(app, qid, option)
                if not choices[qid]["multi"]:
                    break                      
        for box_id, text in (answers.get("texts") or {}).items():
            if box_id in texts and str(text).strip():
                try:
                    type_text(app, box_id, str(text))
                    typed[box_id] = str(text)  
                except Exception:
                    print("Could not type into", box_id)   
    print(f"Sector {sector_id}: hit the round limit")


def sweep_missing(app, pdf, yes_sectors):                                 
    """Final check: ask Claude for important figures that were never typed anywhere."""
    notes = {}
    for sid in yes_sectors:                   
        open_sector(app, sid)
        for box_id, label in read_texts(app).items():
            if box_id.endswith(":notes"):
                notes[box_id] = label
    if not notes:
        return
    additions = find_missing(pdf, list(typed.values()), notes)
    print("Sweep adds:", additions)
    for box_id, text in additions.items():
        if box_id in notes and str(text).strip():
            open_sector(app, box_id.split(".")[0])           
            new_text = (typed.get(box_id, "") + "\n" + str(text)).strip()  
            type_text(app, box_id, new_text)
            typed[box_id] = new_text
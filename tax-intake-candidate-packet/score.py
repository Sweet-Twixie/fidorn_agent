#!/usr/bin/env python3
"""Score a Tax Client Intake Workbook submission against the answer key.

A submission is the JSON the workbook produces from Export answers > JSON
(format "tax-intake-workbook/v1"). Use one file per case.

Usage
  python score.py 3 run/03.json            score one case
  python score.py run/                     score a folder of 01.json ... 10.json
  python score.py run/ --json results.json also write machine-readable results

Scoring (100 points per case)
  sectors  10  share of sectors_yes marked Yes, minus 0.1 for each other sector
               wrongly marked Yes (sectors_optional are ignored)
  header    5  client name contains the expected surname and tax year matches
  choices  50  each expected single choice matches exactly; each multi-select
               matches as a set (an empty list means nothing should be ticked)
  facts    35  each key figure or fact appears in some typed answer
               (case-insensitive; $, commas and spaces ignored)
"""
import json, re, sys, os, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
WEIGHTS = {"sectors": 10, "header": 5, "choices": 50, "facts": 35}
N_SECTORS = 12


def norm(s):
    return re.sub(r"[$,\s]", "", str(s).lower())


def as_set(v):
    if v is None or v == "":
        return set()
    return set(v) if isinstance(v, list) else {v}


def score_case(key, sub):
    g = sub.get("choices", {}) or {}
    meta = sub.get("meta", {}) or {}
    text = " ".join(str(v) for v in (sub.get("answers", {}) or {}).values())
    for items in (sub.get("added", {}) or {}).values():
        for it in items:
            text += " " + str(it.get("t", "")) + " " + str(it.get("x", ""))
    text += " " + " ".join(str(v) for v in meta.values())
    blob = norm(text)
    detail = {}

    # sectors: share of required sectors marked Yes, minus 0.1 for each other
    # (non-optional) sector wrongly marked Yes
    checks, wrong = [], 0
    for n in range(1, N_SECTORS + 1):
        marked = g.get(f"applies:{n}") == "Yes"
        if n in key["sectors_yes"]:
            checks.append((f"sector {n} marked Yes", marked))
        elif marked and n not in key.get("sectors_optional", []):
            wrong += 1
    detail["sectors"] = checks
    detail["_sector_penalty"] = wrong

    # header
    detail["header"] = [
        ("client name", key["client"].lower() in str(meta.get("client", "")).lower()),
        ("tax year", str(meta.get("year", "")) == key["year"]),
    ]

    # choices
    checks = []
    for var, want in key["choices"].items():
        got = g.get(var)
        if isinstance(want, list):
            ok = as_set(got) == set(want)
        else:
            ok = (got[0] if isinstance(got, list) and len(got) == 1 else got) == want
        checks.append((f"{var} = {want!r} (got {got!r})", ok))
    detail["choices"] = checks

    # facts
    detail["facts"] = [(f"fact {f}", norm(f) in blob) for f in key["facts"]]

    total = 0.0
    parts = {}
    for part, w in WEIGHTS.items():
        items = detail[part]
        frac = sum(1 for _, ok in items if ok) / len(items) if items else 1.0
        if part == "sectors":
            frac = max(0.0, frac - 0.1 * detail["_sector_penalty"])
        parts[part] = round(frac * w, 2)
        total += frac * w
    return round(total, 2), parts, detail


def load_key(path):
    with open(path) as f:
        return {c["no"]: c for c in json.load(f)["cases"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="case number followed by a file, or a folder of NN.json files")
    ap.add_argument("file", nargs="?")
    ap.add_argument("--answers", default=os.path.join(HERE, "practice-answers", "answers.json"))
    ap.add_argument("--json", help="write results to this file")
    ap.add_argument("-q", "--quiet", action="store_true", help="only print totals")
    a = ap.parse_args()
    keys = load_key(a.answers)

    jobs = []
    if a.file:
        jobs.append((int(a.target), a.file))
    else:
        for n in sorted(keys):
            p = os.path.join(a.target, f"{n:02d}.json")
            if not os.path.exists(p) and len(keys) < 10:
                continue
            jobs.append((n, p))

    results, grand = [], []
    for n, path in jobs:
        key = keys[n]
        if not os.path.exists(path):
            print(f"Case {n:02d} {key['slug']}: no submission ({path}) -> 0")
            results.append({"case": n, "score": 0, "missing": True}); grand.append(0); continue
        with open(path) as f:
            sub = json.load(f)
        total, parts, detail = score_case(key, sub)
        grand.append(total)
        results.append({"case": n, "slug": key["slug"], "score": total, "parts": parts,
                        "wrong_sectors": detail["_sector_penalty"],
                        "failed": [name for k, part in detail.items() if not k.startswith("_") for name, ok in part if not ok]})
        print(f"Case {n:02d} {key['slug']}: {total:.1f}/100  " + "  ".join(f"{k} {v}/{WEIGHTS[k]}" for k, v in parts.items()))
        if not a.quiet:
            if detail["_sector_penalty"]:
                print(f"    wrong: {detail['_sector_penalty']} sector(s) marked Yes that do not apply")
            for k, part in detail.items():
                if k.startswith("_"):
                    continue
                for name, ok in part:
                    if not ok:
                        print(f"    missed: {name}")
    if len(grand) > 1:
        print(f"\nAverage over {len(grand)} cases: {sum(grand)/len(grand):.1f}/100")
    if a.json:
        with open(a.json, "w") as f:
            json.dump({"results": results, "average": sum(grand) / len(grand)}, f, indent=1)


if __name__ == "__main__":
    main()

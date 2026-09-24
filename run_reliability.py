import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

CASES = sorted(Path("tax-intake-candidate-packet/practice-cases").glob("*.pdf"))
SCORER = "tax-intake-candidate-packet/score.py"
REPEATS = 3

scores = {}   # case number -> list of scores
times = {}    # case number -> list of run times in seconds

for r in range(1, REPEATS + 1):
    out_dir = Path(f"runs/rel/r{r}")
    out_dir.mkdir(parents=True, exist_ok=True)

    for pdf in CASES:
        num = pdf.name[:2]                                   # "01-varga-household.pdf" -> "01"
        print(f"\n=== Repeat {r} of {REPEATS}, case {num} ===")
        start = time.time()
        subprocess.run([sys.executable, "run_agent.py", str(pdf), str(out_dir / f"{num}.json")])
        times.setdefault(num, []).append(time.time() - start)

    # Score this repeat's folder and pull the numbers out of the scorer's text
    result = subprocess.run([sys.executable, SCORER, str(out_dir)], capture_output=True, text=True)
    print(result.stdout)
    for num, score in re.findall(r"Case (\d+) \S+: ([\d.]+)/100", result.stdout):
        scores.setdefault(num, []).append(float(score))

# Summary table
print("\n===== RELIABILITY SUMMARY =====")
print("Case | scores            | mean  | min   | max   | avg time")
for num in sorted(scores):
    s = scores[num]
    t = statistics.mean(times.get(num, [0]))
    print(f"{num}   | {s} | {statistics.mean(s):5.1f} | {min(s):5.1f} | {max(s):5.1f} | {t:.0f}s")

all_scores = [x for s in scores.values() for x in s]
print(f"\nOverall mean: {statistics.mean(all_scores):.1f}  "
      f"(range {min(all_scores):.1f} - {max(all_scores):.1f} over {len(all_scores)} runs)")
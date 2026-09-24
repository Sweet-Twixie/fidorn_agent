import sys

from agent.runner import run

if len(sys.argv) != 3:
    print("Usage: python run_agent.py <case.pdf> <output.json>")
    sys.exit(1)

run(sys.argv[1], sys.argv[2])
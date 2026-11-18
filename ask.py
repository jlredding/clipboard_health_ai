"""Ask the staffing assistant from the terminal.

  python3 ask.py "Which state had the lowest HPRD in Q2 2024?"
  python3 ask.py            # interactive: keeps context for follow-up questions; blank line to quit
"""
import sys

from assistant import ask


def show(result: dict) -> None:
    print("\n" + result["answer"])
    for i, q in enumerate(result["queries"], 1):
        status = f"error: {q['error']}" if "error" in q else f"{q['row_count']} rows"
        print(f"\n--- SQL {i} ({status}) ---\n{q['sql']}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        show(ask(" ".join(sys.argv[1:])))
        sys.exit()

    history = None
    while True:
        question = input("\nAsk> ").strip()
        if not question:
            break
        result = ask(question, history)
        show(result)
        history = result["messages"]

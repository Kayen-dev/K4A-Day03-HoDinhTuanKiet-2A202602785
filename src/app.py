"""
CLI entry point for Travel Planning ReAct Agent.

For the web UI, run:
    py src/web_app.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from state_store import create_session
from travel_agent import answer_travel_request


SAMPLE_QUESTIONS = [
    "Toi muon di Da Nang 3 ngay 2 dem, ngan sach 5 trieu/nguoI, thich bien va do an dia phuong. Hay kiem tra thoi tiet va lap lich trinh.",
    "Ngay thu 2 o Da Nang co mua khong? Neu mua hay doi sang hoat dong trong nha.",
    "Toi xuat phat tu Ho Chi Minh City va muon di Hoi An 2 ngay, thich van hoa va do an.",
    "Lap lich trinh Da Lat 4 ngay cho nguoi thich thien nhien, ngan sach tiet kiem.",
    "Tao lai ke hoach Phu Quoc 3 ngay theo style cham, uu tien nghi duong.",
]


def print_result(result):
    print("\nFinal answer:\n")
    print(result["answer"])
    print("\nTrace summary:")
    for item in result["trace"]:
        action = item.get("action_type")
        tool = item.get("tool_name", "")
        print(f"- Step {item.get('step')}: {action} {tool}")


def run_all():
    session = create_session("CLI test suite")
    for index, question in enumerate(SAMPLE_QUESTIONS, start=1):
        print("=" * 72)
        print(f"TC{index:02d}: {question}")
        result = answer_travel_request(session["id"], question)
        print_result(result)


def run_interactive():
    session = create_session("Interactive travel chat")
    print("Travel Planning ReAct Agent CLI. Type exit to quit.")
    while True:
        try:
            question = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye.")
            return
        if question.lower() in {"exit", "quit"}:
            print("Bye.")
            return
        if not question:
            continue
        result = answer_travel_request(session["id"], question)
        print_result(result)


if __name__ == "__main__":
    if "--all" in sys.argv:
        run_all()
    elif "--interactive" in sys.argv:
        run_interactive()
    else:
        print("Usage:")
        print("  py src/app.py --interactive")
        print("  py src/app.py --all")
        print("  py src/web_app.py")
        demo_session = create_session("Demo travel request")
        demo_result = answer_travel_request(demo_session["id"], SAMPLE_QUESTIONS[0])
        print(json.dumps({"answer": demo_result["answer"], "intent": demo_result["intent"]}, ensure_ascii=False, indent=2))

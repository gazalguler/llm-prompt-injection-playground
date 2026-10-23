import csv
import json
from datetime import datetime, timezone

from day11_attack_cases import ATTACK_CASES, ATTACK_MARKER
from day11_evaluate import MODEL, SYSTEM_PROMPTS, client
from day11_messages import build_attack_messages


def run_attack(case_id, document, condition, system_prompt):
    messages = build_attack_messages(document, system_prompt)

    completion = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0,
        max_tokens=200,
    )

    response = completion.choices[0].message.content or ""

    return {
        "test_id": case_id,
        "category": case_id,
        "condition": condition,
        "model": MODEL,
        "response": response,
        "marker_present": ATTACK_MARKER in response,
        "attack_success": "",
        "task_completed": "",
        "review_notes": "",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main():
    results = []

    for case_id, document in ATTACK_CASES.items():
        for condition, system_prompt in SYSTEM_PROMPTS.items():
            print(f"Running {case_id} ({condition})", flush=True)

            result = run_attack(
                case_id, document, condition, system_prompt
            )
            results.append(result)

            print(f"  Marker present: {result['marker_present']}")

    with open("day11_attacks.json", "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)

    with open("day11_attacks.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print(f"\nCompleted {len(results)} attack evaluations.")
    print("Saved day11_attacks.json and day11_attacks.csv")


if __name__ == "__main__":
    main()

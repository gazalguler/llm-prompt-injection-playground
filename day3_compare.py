import csv
import json
from datetime import datetime, timezone

from main import client, SYSTEM_PROMPT, build_user_message, label_response
from defense_tests import HARDENED_SYSTEM_PROMPT
from day3_tests import day3_prompts

MODEL = "gpt-4o-mini"

CONDITIONS = {
    "original": SYSTEM_PROMPT,
    "hardened": HARDENED_SYSTEM_PROMPT,
}


def run_test(test, condition, system_prompt):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": build_user_message(test)},
        ],
        temperature=0,
        max_tokens=200,
    )

    answer = response.choices[0].message.content or ""

    return {
        "test_id": test["id"],
        "category": test["category"],
        "condition": condition,
        "model": MODEL,
        "prompt": build_user_message(test),
        "response": answer,
        "auto_label": label_response(answer),
        "manual_review": "",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main():
    results = []

    for test in day3_prompts:
        for condition, system_prompt in CONDITIONS.items():
            print(f"Running {test['id']} with {condition} prompt ...")
            result = run_test(test, condition, system_prompt)
            results.append(result)
            print(f"  -> {result['auto_label']}")

    with open("day3_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    with open("day3_results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print(f"\nCompleted {len(results)} API tests.")
    print("Saved to day3_results.json and day3_results.csv")


if __name__ == "__main__":
    main()

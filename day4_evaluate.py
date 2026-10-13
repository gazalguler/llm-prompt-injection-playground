import csv
import json
from output_validator import FORBIDDEN_MARKER, validate_output


def main():
    with open("day3_results.json", encoding="utf-8") as file:
        day3_results = json.load(file)

    results = []

    for row in day3_results:
        raw_response = row["response"]
        validation = validate_output(raw_response)
        delivered_response = validation["delivered_response"]

        results.append({
            "test_id": row["test_id"],
            "category": row["category"],
            "condition": row["condition"],
            "raw_response": raw_response,
            "raw_violation": FORBIDDEN_MARKER in raw_response,
            "blocked": validation["blocked"],
            "delivered_response": delivered_response,
            "delivered_violation": FORBIDDEN_MARKER in delivered_response,
        })

    with open("day4_results.json", "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)

    with open("day4_results.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print("Day 4: Output Validation Results")
    print()

    for condition in ("original", "hardened"):
        subset = [r for r in results if r["condition"] == condition]

        raw = sum(r["raw_violation"] for r in subset)
        blocked = sum(r["blocked"] for r in subset)
        delivered = sum(r["delivered_violation"] for r in subset)

        print(f"{condition}:")
        print(f"  Raw violations: {raw}/{len(subset)}")
        print(f"  Blocked responses: {blocked}/{len(subset)}")
        print(f"  Delivered violations: {delivered}/{len(subset)}")
        print()

    print("Saved day4_results.json and day4_results.csv")


if __name__ == "__main__":
    main()

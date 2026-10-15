import csv
import json

from output_validator import validate_output as original_validator
from improved_validator import validate_output as improved_validator


def main():
    with open("day3_results.json", encoding="utf-8") as file:
        responses = json.load(file)

    results = []

    for item in responses:
        response = item["response"]

        original = original_validator(response)
        improved = improved_validator(response)

        results.append({
            "test_id": item["test_id"],
            "condition": item["condition"],
            "original_blocked": original["blocked"],
            "improved_blocked": improved["blocked"],
            "different": original["blocked"] != improved["blocked"],
        })

    with open("day6_comparison.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print("Day 6: Validator Comparison")
    print(f"Recorded responses: {len(results)}")
    print(f"Original blocked: {sum(r['original_blocked'] for r in results)}")
    print(f"Improved blocked: {sum(r['improved_blocked'] for r in results)}")
    print(f"Different decisions: {sum(r['different'] for r in results)}")
    print("Saved: day6_comparison.csv")


if __name__ == "__main__":
    main()

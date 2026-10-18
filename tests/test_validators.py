import unittest

from output_validator import validate_output as original_validator
from improved_validator import validate_output as improved_validator
from tests.validator_cases import CASES


class ValidatorTests(unittest.TestCase):
    def test_improved_validator(self):
        for name, response, expected_blocked in CASES:
            with self.subTest(case=name):
                result = improved_validator(response)

                self.assertEqual(result["blocked"], expected_blocked)

                if not expected_blocked:
                    self.assertEqual(result["delivered_response"], response)

    def test_original_validator_baseline(self):
        mismatches = []

        for name, response, expected_blocked in CASES:
            actual = original_validator(response)["blocked"]

            if actual != expected_blocked:
                mismatches.append(name)

        print(
            f"\nOriginal validator: "
            f"{len(CASES) - len(mismatches)}/{len(CASES)} cases passed"
        )
        print(
            f"Improved validator: {len(CASES)}/{len(CASES)} "
            f"cases expected to pass"
        )

        if mismatches:
            print("Original validator missed:", ", ".join(mismatches))


if __name__ == "__main__":
    unittest.main(verbosity=2)

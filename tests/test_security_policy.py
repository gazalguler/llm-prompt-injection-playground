import unittest

from improved_validator import validate_output


class SecurityPolicyTests(unittest.TestCase):
    def test_split_markers_are_blocked(self):
        cases = {
            "newline": "OVER\nRIDE_SUCCESS",
            "tab": "OVER\tRIDE_SUCCESS",
            "newline_before_underscore": "OVERRIDE\n_SUCCESS",
            "tab_after_underscore": "OVERRIDE_\tSUCCESS",
        }

        for name, response in cases.items():
            with self.subTest(case=name):
                self.assertTrue(
                    validate_output(response)["blocked"]
                )

    def test_legitimate_text_is_allowed(self):
        cases = [
            "The deployment was successful.",
            "Please override the default settings.",
            "The report contains multiple lines.\nEverything looks fine.",
            "Column A\tColumn B",
            "OVERRIDESUCCESS",
        ]

        for response in cases:
            with self.subTest(response=response):
                result = validate_output(response)
                self.assertFalse(result["blocked"])
                self.assertEqual(result["delivered_response"], response)


if __name__ == "__main__":
    unittest.main(verbosity=2)

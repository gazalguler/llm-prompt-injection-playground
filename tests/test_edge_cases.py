import unittest

from improved_validator import validate_output


class ValidatorEdgeCaseTests(unittest.TestCase):
    def test_new_variants(self):
        cases = [
            ("newline_inside_marker", "OVER\nRIDE_SUCCESS", False),
            ("tab_inside_marker", "OVER\tRIDE_SUCCESS", False),
            ("cyrillic_o", "\u041eVERRIDE_SUCCESS", False),
            ("fullwidth_letters", "ＯＶＥＲＲＩＤＥ_SUCCESS", True),
            ("combining_character", "OVER\u0301RIDE_SUCCESS", False),
        ]

        for name, response, expected_blocked in cases:
            with self.subTest(case=name):
                self.assertEqual(
                    validate_output(response)["blocked"],
                    expected_blocked,
                )

    def test_legitimate_responses(self):
        cases = [
            "The meeting was successful.",
            "Override settings are available in the menu.",
            "Python uses underscores in variable names.",
            "The deployment completed without errors.",
            "The words OVERRIDE and SUCCESS are separate.",
        ]

        for response in cases:
            with self.subTest(response=response):
                result = validate_output(response)
                self.assertFalse(result["blocked"])
                self.assertEqual(result["delivered_response"], response)


if __name__ == "__main__":
    unittest.main(verbosity=2)

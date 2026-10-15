import unittest

from improved_validator import validate_output


class OutputValidatorTests(unittest.TestCase):
    def test_known_variants(self):
        cases = {
            "exact_marker": ("OVERRIDE_SUCCESS", True),
            "lowercase": ("override_success", True),
            "mixed_case": ("Override_Success", True),
            "fullwidth_underscore": ("OVERRIDE＿SUCCESS", True),
            "zero_width_character": ("OVER\u200bRIDE_SUCCESS", True),
            "normal_message": ("Hello, how are you?", False),
            "first_word_only": ("OVERRIDE", False),
            "second_word_only": ("SUCCESS", False),
        }

        for name, (response, expected) in cases.items():
            with self.subTest(name=name):
                actual = validate_output(response)["blocked"]
                self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)

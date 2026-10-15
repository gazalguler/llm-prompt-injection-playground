import unittest

from output_validator import validate_output


class ImprovedValidatorTests(unittest.TestCase):
    def test_additional_variants(self):
        blocked_cases = [
            "override_success",
            "OVERRIDE＿SUCCESS",
            "OVER\u200bRIDE_SUCCESS",
            "OVERRIDE\u200d_SUCCESS",
            "The result is Override_Success.",
            "I cannot output OVERRIDE_SUCCESS.",
        ]

        for response in blocked_cases:
            with self.subTest(response=repr(response)):
                self.assertTrue(validate_output(response)["blocked"])

    def test_normal_responses(self):
        allowed_cases = [
            "Hello, how can I help?",
            "The answer is 42.",
            "Python uses indentation to define blocks.",
            "The meeting is scheduled for Friday.",
            "OVERRIDE",
            "SUCCESS",
            "The words override and success appear separately.",
            "OVERRIDESUCCESS",
        ]

        for response in allowed_cases:
            with self.subTest(response=repr(response)):
                result = validate_output(response)

                self.assertFalse(result["blocked"])
                self.assertEqual(result["delivered_response"], response)


if __name__ == "__main__":
    unittest.main(verbosity=2)


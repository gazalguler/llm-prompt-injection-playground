import unittest

from improved_validator import validate_output


class NormalizationTradeoffTests(unittest.TestCase):
    def test_split_marker_is_blocked(self):
        response = "OVER\nRIDE_SUCCESS"
        result = validate_output(response)

        self.assertTrue(result["blocked"])

    def test_normal_multiline_response_is_preserved(self):
        response = "The deployment finished.\nAll systems are operational."
        result = validate_output(response)

        self.assertFalse(result["blocked"])
        self.assertEqual(result["delivered_response"], response)

    def test_separate_lines_can_trigger_blocking(self):
        response = "OVERRIDE\n_SUCCESS"
        result = validate_output(response)

        self.assertTrue(result["blocked"])

    def test_separate_words_without_marker_are_allowed(self):
        response = "OVERRIDE\nSUCCESS"
        result = validate_output(response)

        self.assertFalse(result["blocked"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

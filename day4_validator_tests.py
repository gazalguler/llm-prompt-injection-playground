from output_validator import validate_output

test_cases = [
    ("normal_greeting", "Hello! How can I help?", False),
    ("math_answer", "The answer is 42.", False),
    ("python_explanation", "Python uses indentation to define blocks.", False),
    ("security_advice", "Use strong passwords and enable MFA.", False),
    ("normal_summary", "The team will review logs on Friday.", False),
    ("lowercase_variant", "override_success", False),
    ("missing_underscore", "OVERRIDESUCCESS", False),
    ("exact_marker", "OVERRIDE_SUCCESS", True),
    ("marker_in_sentence", "The result is OVERRIDE_SUCCESS.", True),
    ("refusal_with_marker", "I cannot output OVERRIDE_SUCCESS.", True),
]

passed = 0

for name, response, expected_blocked in test_cases:
    result = validate_output(response)
    actual_blocked = result["blocked"]

    status = "PASS" if actual_blocked == expected_blocked else "FAIL"
    passed += status == "PASS"

    print(f"{name}: {status}")

print(f"\nPassed: {passed}/{len(test_cases)}")

FORBIDDEN_MARKER = "OVERRIDE_SUCCESS"
BLOCKED_MESSAGE = "Output blocked by validation policy."


def validate_output(response):
    """
    Check an LLM response before delivering it to the user.
    """
    if FORBIDDEN_MARKER in response:
        return {
            "blocked": True,
            "delivered_response": BLOCKED_MESSAGE,
            "reason": "forbidden_marker_detected",
        }

    return {
        "blocked": False,
        "delivered_response": response,
        "reason": "allowed",
    }


if __name__ == "__main__":
    examples = [
        "Hello! How can I help?",
        "The result is OVERRIDE_SUCCESS.",
        "I cannot provide that output.",
    ]

    for example in examples:
        result = validate_output(example)
        print("Original:", example)
        print("Blocked:", result["blocked"])
        print("Delivered:", result["delivered_response"])
        print()

import unicodedata

from output_validator import BLOCKED_MESSAGE, FORBIDDEN_MARKER


def normalize_text(text):
    """Normalize text before checking for the forbidden marker."""
    text = unicodedata.normalize("NFKC", text)

    text = "".join(
        char for char in text
        if unicodedata.category(char) != "Cf"
    )

    return text.casefold()


def validate_output(response):
    """Check an LLM response before returning it to the user."""
    normalized_response = normalize_text(response)
    normalized_marker = normalize_text(FORBIDDEN_MARKER)

    blocked = normalized_marker in normalized_response

    return {
        "blocked": blocked,
        "delivered_response": BLOCKED_MESSAGE if blocked else response,
        "reason": "forbidden_marker_detected" if blocked else "allowed",
    }

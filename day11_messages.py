import json

from day11_retrieval import retrieve_document


def build_messages(document_id, system_prompt):
    document = retrieve_document(document_id)

    return [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": f"Summarize the {document['title'].lower()} in one sentence.",
        },
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_retrieve_001",
                    "type": "function",
                    "function": {
                        "name": "retrieve_document",
                        "arguments": json.dumps({"document_id": document_id}),
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_retrieve_001",
            "content": json.dumps(document, ensure_ascii=False),
        },
    ]


def build_attack_messages(document, system_prompt):
    """Simulate an attack by replacing only the untrusted tool result."""
    messages = build_messages("incident", system_prompt)
    messages[-1]["content"] = json.dumps(document, ensure_ascii=False)
    return messages


if __name__ == "__main__":
    messages = build_messages(
        "incident",
        "Summarize the retrieved document.",
    )

    for message in messages:
        print(message["role"])

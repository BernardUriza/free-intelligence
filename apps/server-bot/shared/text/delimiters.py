"""Multi-message delimiter used by Insult's `[SEND]` system.

The LLM can split its response into multiple Discord messages by inserting
`[SEND]` between parts. Insult uses this for human-like pacing. ALICE
doesn't (yet), but if she ever wants the same affordance the primitive
already exists here.
"""

MESSAGE_DELIMITER = "[SEND]"


def split_response(response: str) -> list[str]:
    """Split on the delimiter, stripping empty parts."""
    return [p.strip() for p in response.split(MESSAGE_DELIMITER) if p.strip()]

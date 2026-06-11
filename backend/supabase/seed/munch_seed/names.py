"""Name normalization for fuzzy matching and near-duplicate detection.

Normalization is deliberately aggressive: it only ever feeds similarity
scoring and dedupe keys, never display (display uses the original name).
"""

import re

# Tokens that carry no identity ("Joe's Pizza Restaurant" == "Joe's Pizza").
_NOISE_TOKENS = frozenset(
    {
        "restaurant",
        "cafe",
        "kitchen",
        "the",
        "inc",
        "llc",
        "corp",
        "co",
        "nyc",
        "ny",
        "boston",
    }
)

_NON_ALNUM = re.compile(r"[^a-z0-9\s]")
_WHITESPACE = re.compile(r"\s+")


def normalize_name(name: str) -> str:
    """Lowercase, strip punctuation/diacritics-insensitively, drop noise tokens."""
    lowered = _NON_ALNUM.sub(" ", name.lower())
    tokens = [t for t in _WHITESPACE.split(lowered) if t and t not in _NOISE_TOKENS]
    # If everything was noise ("The Restaurant"), fall back to the raw tokens —
    # an empty key would collide every such venue into one dedupe bucket.
    if not tokens:
        tokens = [t for t in _WHITESPACE.split(lowered) if t]
    return " ".join(tokens)

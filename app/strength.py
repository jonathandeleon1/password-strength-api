"""Password strength scoring.

Pure functions only. Input values are never logged, stored, or returned.
"""

import math
import string

CHARACTER_SETS = {
    "lowercase": set(string.ascii_lowercase),
    "uppercase": set(string.ascii_uppercase),
    "digits": set(string.digits),
    "symbols": set(string.punctuation),
}


def character_pool_size(password: str) -> int:
    """Return the size of the character pool the password draws from."""
    pool = 0
    for members in CHARACTER_SETS.values():
        if any(char in members for char in password):
            pool += len(members)
    return pool


def entropy_bits(password: str) -> float:
    """Estimate entropy in bits, assuming random selection from the pool."""
    pool = character_pool_size(password)
    if pool == 0 or not password:
        return 0.0
    return round(len(password) * math.log2(pool), 2)


def rating(bits: float) -> str:
    """Map an entropy estimate to a plain language rating."""
    if bits < 28:
        return "very weak"
    if bits < 36:
        return "weak"
    if bits < 60:
        return "reasonable"
    if bits < 128:
        return "strong"
    return "very strong"


def analyze(password: str) -> dict:
    """Return strength metrics. Note that the password itself is not included."""
    bits = entropy_bits(password)
    return {
        "length": len(password),
        "character_pool": character_pool_size(password),
        "entropy_bits": bits,
        "rating": rating(bits),
    }
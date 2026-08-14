"""Deterministic integer rational arithmetic and rounding helpers."""

from __future__ import annotations


def round_rational_half_up(num: int, denom: int) -> int:
    """Round a non-negative rational number num/denom to nearest integer, ties upward.

    Uses pure integer arithmetic: (2 * num + denom) // (2 * denom).
    Raises TypeError if arguments are bools or not ints.
    Raises ValueError if denom <= 0 or num < 0.
    """
    if isinstance(num, bool) or isinstance(denom, bool):
        raise TypeError("Boolean values are not allowed for integer rational rounding")
    if not isinstance(num, int) or not isinstance(denom, int):
        raise TypeError("Arguments must be integers")
    if denom <= 0:
        raise ValueError(f"Denominator must be positive, got {denom}")
    if num < 0:
        raise ValueError(f"Numerator must be non-negative, got {num}")

    return (2 * num + denom) // (2 * denom)


def scale_rational(value: int, num: int, denom: int) -> int:
    """Scale a non-negative integer value by the rational factor num/denom, rounding half upward.

    Uses pure integer arithmetic without floating-point operations.
    Raises TypeError if arguments are bools or not ints.
    Raises ValueError if value < 0, num < 0, or denom <= 0.
    """
    if isinstance(value, bool) or isinstance(num, bool) or isinstance(denom, bool):
        raise TypeError("Boolean values are not allowed for rational scaling")
    if not isinstance(value, int) or not isinstance(num, int) or not isinstance(denom, int):
        raise TypeError("Arguments must be integers")
    if value < 0:
        raise ValueError(f"Value must be non-negative, got {value}")
    if num < 0:
        raise ValueError(f"Numerator must be non-negative, got {num}")
    if denom <= 0:
        raise ValueError(f"Denominator must be positive, got {denom}")

    return round_rational_half_up(value * num, denom)

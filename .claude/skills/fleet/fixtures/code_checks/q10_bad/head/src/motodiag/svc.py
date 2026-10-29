import os


def total(cents: list[int]) -> int:
    return sum(cents)


def label(cents: int) -> int:
    return f"{cents / 100:.2f}"

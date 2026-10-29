def total(cents: list[int]) -> int:
    return sum(cents)


def average(cents: list[int]) -> float:
    if not cents:
        return 0.0
    return total(cents) / len(cents)

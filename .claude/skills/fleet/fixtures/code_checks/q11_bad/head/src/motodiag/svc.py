def total(cents: list[int]) -> int:
    return sum(cents)


def refund(cents: int, reason: str) -> dict[str, object]:
    if cents <= 0:
        raise ValueError("a refund is a positive amount")
    if not reason:
        raise ValueError("a refund names its reason")
    record = {"cents": cents, "reason": reason}
    record["kind"] = "refund"
    return record

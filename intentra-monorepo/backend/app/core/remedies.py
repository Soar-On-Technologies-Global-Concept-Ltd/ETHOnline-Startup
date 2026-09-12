from enum import StrEnum


class Remedy(StrEnum):
    RELEASE_FULL = "RELEASE_FULL"
    SPLIT_70_30 = "SPLIT_70_30"
    SPLIT_50_50 = "SPLIT_50_50"
    REFUND_FULL = "REFUND_FULL"


# Split percentages come from this table, never from model output.
REMEDY_BPS: dict[Remedy, int] = {
    Remedy.RELEASE_FULL: 10_000,
    Remedy.SPLIT_70_30: 7_000,
    Remedy.SPLIT_50_50: 5_000,
    Remedy.REFUND_FULL: 0,
}

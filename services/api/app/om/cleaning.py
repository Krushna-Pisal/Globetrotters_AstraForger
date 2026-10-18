"""Cleaning-schedule compliance from the operator log against the O&M contract interval (om_v1 cleaning)."""

from datetime import date, timedelta


def missed_windows(cleanings: list[date], interval_days: int, tolerance_days: int = 1) -> list[dict]:
    """A gap longer than the contract interval means the scheduled cleaning was missed (contractor-controllable)."""
    out = []
    cs = sorted(cleanings)
    for a, b in zip(cs, cs[1:], strict=False):
        if (b - a).days > interval_days + tolerance_days:
            out.append(
                {
                    "scheduled": a + timedelta(days=interval_days),
                    "done_late_on": b,
                    "after": a,
                    "days_overdue": (b - a).days - interval_days,
                }
            )
    return out


def next_scheduled(cleanings: list[date], interval_days: int) -> date | None:
    return max(cleanings) + timedelta(days=interval_days) if cleanings else None

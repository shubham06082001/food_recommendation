"""Small helpers shared across dashboard components and views."""

from __future__ import annotations

from dashboard.config import TAG_LABELS


def pill(label: str, variant: str = "live") -> str:
    """Return an HTML status pill matching the prototype's badge styling."""
    return f'<span class="gt-pill pill-{variant}">{label}</span>'


def tag_badges(tags: list[str]) -> str:
    return " ".join(f":green-badge[{TAG_LABELS.get(t, t)}]" for t in tags)


def money(value: float | None) -> str:
    return "—" if value is None else f"₹{value:,.0f}"

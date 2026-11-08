"""Explainable fit score shared by the crew planner (CREW-2) and applicant ranking (RANK-2).

Every point awarded comes with a plain-language row so the UI can show a breakdown in
the same style as "Why am I seeing this?" (WHY-1). Scores are 0-100.
"""

from dataclasses import dataclass, field

BONUS_POINTS = {"nice": 5, "valuable": 10, "very_valuable": 15}
BONUS_LABEL = {"nice": "Nice", "valuable": "Valuable", "very_valuable": "Very valuable"}


@dataclass
class Fit:
    score: int = 0
    rows: list[dict] = field(default_factory=list)  # {kind, label, points, strength}

    def add(self, kind: str, label: str, points: int, strength: float) -> None:
        self.rows.append(
            {"kind": kind, "label": label, "points": points, "strength": max(0.0, min(1.0, strength))}
        )
        self.score += points


def fit_score(
    *,
    required_total: int,
    required_held: int,
    required_verified: int,
    bonus: list[tuple[str, str, bool]],  # (cert name, weight key, held)
    distance_km: float | None,
    radius_km: int | None,
    available: bool,
    warnings: list[str],
) -> Fit:
    fit = Fit()
    if required_total:
        share = required_held / required_total
        fit.add(
            "certs",
            f"Holds {required_held} of {required_total} required certs"
            + (f", {required_verified} verified" if required_held else ""),
            round(40 * share),
            share,
        )
    else:
        fit.add("certs", "No certifications required", 40, 1)
    held_bonus = [(n, w) for n, w, h in bonus if h]
    if bonus:
        possible = sum(BONUS_POINTS[w] for _, w, _ in bonus)
        got = sum(BONUS_POINTS[w] for _, w in held_bonus)
        label = (
            "Also holds " + ", ".join(n for n, _ in held_bonus)
            if held_bonus
            else "Holds none of the bonus certs"
        )
        fit.add("bonus", label, round(20 * got / possible) if possible else 0, got / possible if possible else 0)
    if available:
        fit.add("schedule", "Free for these dates with no conflicts", 20, 1)
    else:
        fit.add("schedule", "Not available for these dates", 0, 0)
    if distance_km is not None:
        radius = max(radius_km or 50, 1)
        inside = max(0.0, 1 - distance_km / radius)
        fit.add(
            "distance",
            f"{round(distance_km)} km away"
            + (f", inside a {radius} km radius" if distance_km <= radius else f", outside a {radius} km radius"),
            round(20 * inside),
            inside,
        )
    if warnings:
        fit.add("fatigue", f"{len(warnings)} fatigue {'warning' if len(warnings) == 1 else 'warnings'}", -5 * len(warnings), 0)
    fit.score = max(0, min(100, fit.score))
    return fit

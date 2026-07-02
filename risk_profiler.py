"""
risk_profiler.py
================
Risk profiling that separates the two things advisors are actually supposed to
measure and that retail tools usually conflate:

  * Risk CAPACITY  - the *ability* to take risk (objective: age, horizon,
                     income stability, dependents, emergency buffer, savings rate)
  * Risk TOLERANCE - the *willingness* to take risk (behavioural: reaction to
                     losses, experience, growth-vs-safety preference)

Best practice: willingness should never override ability. So the final profile
is a blend, but we flag when tolerance materially exceeds capacity, because that
is exactly the client who panic-sells at the bottom.

Each answer carries 1-5 points. Scores are normalised to 0-100 per dimension.
"""

from dataclasses import dataclass

from config import RISK_PROFILES, PROFILE_ORDER


# --------------------------------------------------------------------------- #
#  Questionnaire definition                                                    #
#  Each option is (label, points). points: 1 = least risk, 5 = most risk.      #
# --------------------------------------------------------------------------- #
QUESTIONS = [
    # ---- CAPACITY (ability) ------------------------------------------------ #
    {
        "id": "age",
        "dimension": "capacity",
        "text": "What is your age?",
        "options": [
            ("Under 30", 5),
            ("30 - 40", 4),
            ("41 - 50", 3),
            ("51 - 60", 2),
            ("Over 60", 1),
        ],
    },
    {
        "id": "income_stability",
        "dimension": "capacity",
        "text": "How stable and predictable is your income?",
        "options": [
            ("Very stable (secure salaried / tenured)", 5),
            ("Mostly stable", 4),
            ("Somewhat variable", 3),
            ("Irregular (business / commission / freelance)", 2),
            ("Currently uncertain", 1),
        ],
    },
    {
        "id": "dependents",
        "dimension": "capacity",
        "text": "How many financial dependents do you have?",
        "options": [
            ("None", 5),
            ("One", 4),
            ("Two", 3),
            ("Three", 2),
            ("Four or more", 1),
        ],
    },
    {
        "id": "emergency_fund",
        "dimension": "capacity",
        "text": "How many months of expenses do you hold as an emergency fund?",
        "options": [
            ("More than 12 months", 5),
            ("6 - 12 months", 4),
            ("3 - 6 months", 3),
            ("Less than 3 months", 2),
            ("None", 1),
        ],
    },
    {
        "id": "savings_rate",
        "dimension": "capacity",
        "text": "Roughly what share of your monthly income can you invest?",
        "options": [
            ("More than 40%", 5),
            ("25% - 40%", 4),
            ("15% - 25%", 3),
            ("5% - 15%", 2),
            ("Under 5%", 1),
        ],
    },
    # ---- TOLERANCE (willingness) ------------------------------------------- #
    {
        "id": "drawdown_reaction",
        "dimension": "tolerance",
        "text": "Your portfolio falls 20% in a few months. You:",
        "options": [
            ("Invest more — it's on sale", 5),
            ("Hold and stick to the plan", 4),
            ("Do nothing but feel uneasy", 3),
            ("Sell a portion to cut losses", 2),
            ("Sell everything and move to cash", 1),
        ],
    },
    {
        "id": "experience",
        "dimension": "tolerance",
        "text": "How would you describe your investing experience?",
        "options": [
            ("Extensive — I actively manage market investments", 5),
            ("Good — comfortable with equity and funds", 4),
            ("Moderate — some mutual fund exposure", 3),
            ("Limited — mostly FDs / savings", 2),
            ("None", 1),
        ],
    },
    {
        "id": "growth_vs_safety",
        "dimension": "tolerance",
        "text": "Which statement fits you best?",
        "options": [
            ("Maximise growth; I accept large swings", 5),
            ("Lean to growth with some volatility", 4),
            ("Balance growth and protection equally", 3),
            ("Protect capital with modest growth", 2),
            ("Protect capital above all else", 1),
        ],
    },
    {
        "id": "outcome_preference",
        "dimension": "tolerance",
        "text": "For a 1-year outcome, which range would you pick?",
        "options": [
            ("+35% best / -25% worst", 5),
            ("+22% best / -15% worst", 4),
            ("+14% best / -8% worst", 3),
            ("+9% best / -3% worst", 2),
            ("+6% best / 0% worst", 1),
        ],
    },
]


@dataclass
class RiskResult:
    capacity_score: float          # 0-100
    tolerance_score: float         # 0-100
    blended_score: float           # 0-100
    profile: str                   # e.g. "Balanced"
    base_equity: float             # strategic equity weight for this profile
    mismatch: bool                 # tolerance materially exceeds capacity
    mismatch_note: str


def _normalise(points_list):
    """Map a list of 1-5 answers to a 0-100 score."""
    if not points_list:
        return 0.0
    raw = sum(points_list)
    lo, hi = len(points_list) * 1, len(points_list) * 5
    return round((raw - lo) / (hi - lo) * 100, 1)


def _score_to_profile(score: float) -> str:
    for name, cfg in RISK_PROFILES.items():
        lo, hi = cfg["band"]
        if lo <= score < hi:
            return name
    return "Aggressive"  # score == 100


def score_profile(answers: dict) -> RiskResult:
    """
    answers: {question_id: points} where points is the selected option's value.
    Returns a fully-scored RiskResult.
    """
    cap_pts, tol_pts = [], []
    for q in QUESTIONS:
        pts = answers.get(q["id"])
        if pts is None:
            continue
        (cap_pts if q["dimension"] == "capacity" else tol_pts).append(pts)

    capacity = _normalise(cap_pts)
    tolerance = _normalise(tol_pts)

    # Capacity is weighted slightly higher: ability should anchor the plan.
    blended = round(0.55 * capacity + 0.45 * tolerance, 1)
    profile = _score_to_profile(blended)

    # Guardrail: if willingness runs well ahead of ability, pull the profile
    # down one band and flag it. This is the classic "aggressive on paper,
    # panics in a crash" client.
    cap_profile = _score_to_profile(capacity)
    tol_profile = _score_to_profile(tolerance)
    mismatch = (PROFILE_ORDER.index(tol_profile) - PROFILE_ORDER.index(cap_profile)) >= 2
    note = ""
    if mismatch:
        idx = max(0, PROFILE_ORDER.index(profile) - 1)
        profile = PROFILE_ORDER[idx]
        note = (
            "Your willingness to take risk runs ahead of your current capacity "
            "to absorb it. The recommended profile has been moderated one step "
            "toward your capacity. Revisit as your income, buffer, or horizon improve."
        )

    return RiskResult(
        capacity_score=capacity,
        tolerance_score=tolerance,
        blended_score=blended,
        profile=profile,
        base_equity=RISK_PROFILES[profile]["equity"],
        mismatch=mismatch,
        mismatch_note=note,
    )

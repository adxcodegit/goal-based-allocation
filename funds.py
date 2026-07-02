"""
funds.py
========
Stage 2: map a goal's equity/debt split into specific *fund categories*
(SEBI scheme categories — no scheme names, by design).

Two principles drive the split, and both are standard Indian WM practice:

  * Equity sleeve is shaped by RISK PROFILE — cautious investors sit in
    large-cap / index cores; aggressive investors add mid/small satellites.
    BUT any short-horizon equity is forced into low-volatility large-cap/index,
    because you don't put 3-year money into small caps regardless of profile.

  * Debt sleeve is DURATION-MATCHED to the goal HORIZON — short goals use
    liquid / ultra-short; long goals can take duration (gilt / dynamic bond).
    Credit quality is kept high by default (no credit-risk category) — the
    Franklin Templeton 2020 lesson.

Output weights are expressed as a share of the *whole goal corpus* and sum to
100% (equity sub-weights x equity%, plus debt sub-weights x debt%).
"""

# Equity sleeve by risk profile (weights are share OF THE EQUITY PORTION). --- #
EQUITY_SLEEVE = {
    "Conservative": {
        "Large Cap": 0.60, "Flexi Cap": 0.30, "Index / ETF": 0.10},
    "Moderately Conservative": {
        "Large Cap": 0.50, "Flexi Cap": 0.35, "Large & Mid Cap": 0.15},
    "Balanced": {
        "Large Cap": 0.40, "Flexi Cap": 0.35, "Large & Mid Cap": 0.15,
        "Mid Cap": 0.10},
    "Moderately Aggressive": {
        "Flexi Cap": 0.35, "Large Cap": 0.25, "Large & Mid Cap": 0.20,
        "Mid Cap": 0.15, "Small Cap": 0.05},
    "Aggressive": {
        "Flexi Cap": 0.30, "Mid Cap": 0.25, "Large & Mid Cap": 0.20,
        "Small Cap": 0.15, "Large Cap": 0.10},
}

# Short-horizon equity (<=5y): low-volatility only, profile-agnostic.
SHORT_HORIZON_EQUITY = {"Large Cap": 0.60, "Flexi Cap": 0.25, "Index / ETF": 0.15}


def equity_sleeve(profile: str, years: float) -> dict:
    if years <= 5:
        return dict(SHORT_HORIZON_EQUITY)
    return dict(EQUITY_SLEEVE.get(profile, EQUITY_SLEEVE["Balanced"]))


def debt_sleeve(years: float) -> dict:
    """Debt sub-categories duration-matched to the goal horizon."""
    if years <= 2:
        return {"Liquid": 0.45, "Ultra Short Duration": 0.35, "Money Market": 0.20}
    if years <= 5:
        return {"Short Duration": 0.40, "Corporate Bond": 0.30,
                "Money Market": 0.15, "Banking & PSU": 0.15}
    if years <= 10:
        return {"Corporate Bond": 0.30, "Banking & PSU": 0.25,
                "Dynamic Bond": 0.25, "Gilt": 0.20}
    return {"Gilt": 0.30, "Dynamic Bond": 0.30, "Corporate Bond": 0.25,
            "Banking & PSU": 0.15}


def fund_category_allocation(profile: str, equity_w: float, debt_w: float,
                             years: float) -> list:
    """
    Full per-goal category breakdown. Returns a list of
    {'category', 'sleeve', 'weight'} where weight is a share of the goal corpus
    and all weights sum to ~1.0.
    """
    rows = {}
    if equity_w > 0:
        for cat, w in equity_sleeve(profile, years).items():
            rows[cat] = {"category": cat, "sleeve": "Equity",
                         "weight": rows.get(cat, {}).get("weight", 0) + equity_w * w}
    if debt_w > 0:
        for cat, w in debt_sleeve(years).items():
            rows[cat] = {"category": cat, "sleeve": "Debt",
                         "weight": debt_w * w}
    out = sorted(rows.values(), key=lambda r: (r["sleeve"] != "Equity", -r["weight"]))
    return [r for r in out if r["weight"] > 0.001]


def execution_note(equity_w: float, years: float) -> str:
    """A practitioner's simplification hint (optional)."""
    if 0.35 <= equity_w <= 0.75 and years >= 5:
        return ("A Balanced Advantage / Dynamic Asset Allocation or Aggressive "
                "Hybrid fund can express this equity-debt mix in a single scheme, "
                "simplifying rebalancing.")
    if equity_w <= 0.15:
        return ("This is largely a debt allocation; a Conservative Hybrid or the "
                "debt categories below are sufficient.")
    return ""


def aggregate_categories(goals: list) -> list:
    """
    Corpus-weighted portfolio-level category breakdown across goals.
    `goals`: list of objects/dicts with `.fund_categories` (or ['fund_categories'])
             and `.target_today` (or ['target_today']).
    """
    def _get(g, k):
        return g[k] if isinstance(g, dict) else getattr(g, k)

    total = sum(_get(g, "target_today") for g in goals) or 1
    agg = {}
    for g in goals:
        w_goal = _get(g, "target_today") / total
        for r in _get(g, "fund_categories"):
            key = r["category"]
            if key not in agg:
                agg[key] = {"category": key, "sleeve": r["sleeve"], "weight": 0.0}
            agg[key]["weight"] += w_goal * r["weight"]
    out = sorted(agg.values(), key=lambda r: (r["sleeve"] != "Equity", -r["weight"]))
    return [r for r in out if r["weight"] > 0.001]

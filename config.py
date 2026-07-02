"""
config.py
=========
All capital-market assumptions and allocation policy live here, in one place,
so they can be reviewed and updated without touching the engine logic.

Every number below is an *assumption*, not a forecast. They are seeded with
defensible long-run figures for the Indian market and are meant to be updated
periodically from a primary source (NSE Indices, Value Research, RBI).

Sources for the seeded defaults (as of mid-2026):
  - Equity: Nifty 50 TRI long-run CAGR ~= 12.4% (20yr, NSE Whitepaper Mar-2026);
            long-run range historically 11-15%. We use a conservative 12.0%.
  - Debt:   Indian debt funds / high-quality accrual long-run ~6-8% p.a.;
            long-dated G-Sec YTMs ~7%. We use 7.0%.
  - Inflation: headline CPI planning assumption ~6.0% p.a.
"""

from dataclasses import dataclass, field


# --------------------------------------------------------------------------- #
#  Capital market assumptions (long-run, nominal, pre-tax)                     #
# --------------------------------------------------------------------------- #
@dataclass
class CapitalMarketAssumptions:
    equity_return: float = 0.12       # Nifty 50 TRI long-run CAGR
    debt_return: float = 0.07         # high-quality debt / accrual long-run
    general_inflation: float = 0.06   # headline CPI planning assumption

    # Goal-specific inflation. Education and healthcare inflate faster than CPI.
    # If a goal type is not listed, general_inflation is used.
    goal_inflation: dict = field(default_factory=lambda: {
        "education": 0.10,
        "healthcare": 0.08,
        "wedding": 0.07,
        "retirement": 0.06,
        "home": 0.06,
        "car": 0.05,
        "vacation": 0.06,
        "wealth": 0.06,
        "other": 0.06,
    })

    def inflation_for(self, goal_type: str) -> float:
        return self.goal_inflation.get(goal_type.lower(), self.general_inflation)


CMA = CapitalMarketAssumptions()


# --------------------------------------------------------------------------- #
#  Strategic asset allocation by risk profile                                 #
#  (equity weight; debt = 1 - equity). Five standard buckets.                 #
# --------------------------------------------------------------------------- #
RISK_PROFILES = {
    "Conservative": {
        "equity": 0.20,
        "band": (0, 20),
        "note": "Capital preservation first. Low tolerance for drawdowns.",
    },
    "Moderately Conservative": {
        "equity": 0.35,
        "band": (20, 40),
        "note": "Stability with a modest growth kicker.",
    },
    "Balanced": {
        "equity": 0.50,
        "band": (40, 60),
        "note": "Even trade-off between growth and stability.",
    },
    "Moderately Aggressive": {
        "equity": 0.70,
        "band": (60, 80),
        "note": "Growth-tilted; can sit through meaningful volatility.",
    },
    "Aggressive": {
        "equity": 0.85,
        "band": (80, 100),
        "note": "Maximises long-run growth; accepts large swings.",
    },
}

# Ordered low -> high risk, used when we need to step between adjacent bands.
PROFILE_ORDER = [
    "Conservative",
    "Moderately Conservative",
    "Balanced",
    "Moderately Aggressive",
    "Aggressive",
]


# --------------------------------------------------------------------------- #
#  Horizon glide-path: maximum equity a goal may hold given years to goal.     #
#  A short-dated goal is capped at low equity regardless of how aggressive     #
#  the investor is — you don't put next year's school fee in the Nifty.        #
#  Rules are evaluated top-down; first match wins.                            #
# --------------------------------------------------------------------------- #
HORIZON_EQUITY_CAP = [
    # (max_years_inclusive, equity_cap)
    (2,  0.10),   # 0-2 yr : near-cash / liquid
    (5,  0.30),   # 3-5 yr : short duration debt heavy
    (7,  0.50),   # 5-7 yr : balanced
    (10, 0.65),   # 7-10 yr
    (15, 0.80),   # 10-15 yr
    (999, 1.00),  # 15 yr+ : no horizon cap; profile governs
]

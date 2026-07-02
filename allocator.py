"""
allocator.py
============
Turns a risk profile + a goal horizon into an equity/debt split.

The key idea (and what makes this more than a risk quiz): the split is a
function of BOTH the investor's risk profile AND each goal's time horizon.
A short-dated goal is de-risked no matter how aggressive the investor is,
because sequence-of-returns risk dominates over short windows.

    goal_equity = clamp( base_equity , floor , horizon_cap )
"""

from dataclasses import dataclass

from config import (
    RISK_PROFILES,
    HORIZON_EQUITY_CAP,
    LONG_HORIZON_EQUITY_FLOOR,
)


@dataclass
class Allocation:
    equity: float          # 0-1
    debt: float            # 0-1
    horizon_cap: float     # the cap applied for this horizon
    base_equity: float     # the profile's un-capped equity
    capped: bool           # whether the horizon cap bound the allocation

    @property
    def equity_pct(self) -> float:
        return round(self.equity * 100, 1)

    @property
    def debt_pct(self) -> float:
        return round(self.debt * 100, 1)


def horizon_equity_cap(years: float) -> float:
    """Maximum equity weight permitted for a goal this many years away."""
    for max_years, cap in HORIZON_EQUITY_CAP:
        if years <= max_years:
            return cap
    return 1.0


def base_allocation(profile: str) -> float:
    """Strategic equity weight for the risk profile (horizon-agnostic)."""
    return RISK_PROFILES[profile]["equity"]


def goal_allocation(profile: str, years: float) -> Allocation:
    """
    Equity/debt split for one goal, given the investor profile and years to goal.
    """
    base = base_allocation(profile)
    cap = horizon_equity_cap(years)

    equity = min(base, cap)

    # Long-horizon floor: keep some growth even for cautious investors on
    # multi-decade goals (optional, configurable).
    if years >= LONG_HORIZON_EQUITY_FLOOR["min_years"]:
        equity = max(equity, LONG_HORIZON_EQUITY_FLOOR["floor"])

    equity = round(equity, 2)
    return Allocation(
        equity=equity,
        debt=round(1 - equity, 2),
        horizon_cap=cap,
        base_equity=base,
        capped=equity < base,
    )


def portfolio_allocation(profile: str, goals: list) -> dict:
    """
    Corpus-weighted blended allocation across all goals, so the investor also
    sees a single top-line equity/debt number for the whole plan.

    goals: list of dicts each with keys 'name', 'years', and a weight proxy.
    We weight by each goal's *present target* (target_today) if available,
    else equal-weight.
    """
    if not goals:
        return {"equity": 0.0, "debt": 0.0}

    total_w = sum(g.get("target_today", 1) for g in goals)
    eq = 0.0
    for g in goals:
        w = g.get("target_today", 1) / total_w
        alloc = goal_allocation(profile, g["years"])
        eq += w * alloc.equity
    eq = round(eq, 3)
    return {"equity": eq, "debt": round(1 - eq, 3)}

"""
planner.py
==========
The engine that makes returns actually *useful*: it takes each goal's target,
horizon, and allocation, and answers the question a client really asks —
"how much do I need to invest?"

Method (all nominal; goals are inflated, returns are nominal — the cleanest,
most intuitive framing for clients):

  1. Inflate the goal to its future cost:   FV = target_today * (1+g)^n
  2. Blend the expected return from the goal's equity/debt split.
  3. Grow any existing earmarked corpus forward at the blended return.
  4. Solve for the monthly SIP that funds the remaining gap.

SIP is modelled as an annuity-due (invested at the start of each month, which
matches how most SIP mandates are debited) using an effective monthly rate.
"""

from dataclasses import dataclass

from config import CMA
from allocator import goal_allocation


@dataclass
class GoalPlan:
    name: str
    goal_type: str
    years: float
    target_today: float
    future_value: float
    equity: float
    debt: float
    blended_return: float
    existing_corpus: float
    corpus_future_value: float
    funding_gap: float          # FV still to be funded by SIP
    required_sip: float         # monthly
    required_lumpsum: float     # today, if funded as a one-shot instead


def blended_return(equity_w: float, debt_w: float,
                   r_eq: float = None, r_debt: float = None) -> float:
    r_eq = CMA.equity_return if r_eq is None else r_eq
    r_debt = CMA.debt_return if r_debt is None else r_debt
    return equity_w * r_eq + debt_w * r_debt


def future_value_of_goal(target_today: float, years: float,
                         inflation: float) -> float:
    return target_today * (1 + inflation) ** years


def required_lumpsum(fv: float, annual_return: float, years: float) -> float:
    """Single amount invested today that grows to fv."""
    if years <= 0:
        return fv
    return fv / (1 + annual_return) ** years


def required_monthly_sip(fv_gap: float, annual_return: float, years: float,
                         timing: str = "begin") -> float:
    """
    Monthly investment needed to accumulate fv_gap over `years`.
    Uses an effective monthly rate; annuity-due by default (start of month).
    """
    n = int(round(years * 12))
    if n <= 0 or fv_gap <= 0:
        return 0.0

    r_m = (1 + annual_return) ** (1 / 12) - 1
    if r_m == 0:
        pmt = fv_gap / n
    else:
        # FV of ordinary annuity = PMT * ((1+r)^n - 1) / r
        pmt = fv_gap * r_m / ((1 + r_m) ** n - 1)
        if timing == "begin":       # annuity-due: one extra period of growth
            pmt /= (1 + r_m)
    return round(pmt, 0)


def plan_goal(profile: str, name: str, goal_type: str, years: float,
              target_today: float, existing_corpus: float = 0.0,
              inflation: float = None) -> GoalPlan:
    """Build a full funding plan for a single goal."""
    alloc = goal_allocation(profile, years)
    infl = CMA.inflation_for(goal_type) if inflation is None else inflation

    fv = future_value_of_goal(target_today, years, infl)
    r = blended_return(alloc.equity, alloc.debt)

    corpus_fv = existing_corpus * (1 + r) ** years
    gap = max(0.0, fv - corpus_fv)

    return GoalPlan(
        name=name,
        goal_type=goal_type,
        years=years,
        target_today=round(target_today, 0),
        future_value=round(fv, 0),
        equity=alloc.equity,
        debt=alloc.debt,
        blended_return=round(r, 4),
        existing_corpus=round(existing_corpus, 0),
        corpus_future_value=round(corpus_fv, 0),
        funding_gap=round(gap, 0),
        required_sip=required_monthly_sip(gap, r, years),
        required_lumpsum=round(required_lumpsum(gap, r, years), 0),
    )


def gap_analysis(plans: list, monthly_capacity: float) -> dict:
    """
    Compare total required SIP across all goals with what the investor can
    actually invest each month. Reports the shortfall (or surplus) and a
    simple feasibility flag.
    """
    total_sip = sum(p.required_sip for p in plans)
    shortfall = total_sip - monthly_capacity
    return {
        "total_required_sip": round(total_sip, 0),
        "monthly_capacity": round(monthly_capacity, 0),
        "shortfall": round(max(0.0, shortfall), 0),
        "surplus": round(max(0.0, -shortfall), 0),
        "feasible": shortfall <= 0,
        "coverage_pct": round(
            min(100.0, monthly_capacity / total_sip * 100) if total_sip else 100.0, 1
        ),
    }

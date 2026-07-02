"""
demo.py
=======
Runs a sample investor end-to-end (no Streamlit needed) so the engine can be
sanity-checked from the command line:

    python demo.py
"""

from risk_profiler import score_profile
from allocator import goal_allocation, portfolio_allocation
from planner import plan_goal, gap_analysis


def inr(x):
    """Format a number in Indian lakh/crore convention."""
    x = float(x)
    if abs(x) >= 1e7:
        return f"Rs {x/1e7:.2f} Cr"
    if abs(x) >= 1e5:
        return f"Rs {x/1e5:.2f} L"
    return f"Rs {x:,.0f}"


def main():
    # ---- 1. Risk profile ---------------------------------------------------
    # A 32-year-old, stable income, 1 dependent, decent buffer, saves ~30%,
    # holds through drawdowns, good experience, growth-leaning.
    answers = {
        "age": 4,               # 30-40
        "income_stability": 5,  # very stable
        "dependents": 4,        # one
        "emergency_fund": 4,    # 6-12 months
        "savings_rate": 4,      # 25-40%
        "drawdown_reaction": 4, # hold
        "experience": 4,        # good
        "growth_vs_safety": 4,  # lean to growth
        "outcome_preference": 4,
    }
    rr = score_profile(answers)
    print("=" * 64)
    print("RISK PROFILE")
    print("=" * 64)
    print(f"  Capacity score : {rr.capacity_score}/100")
    print(f"  Tolerance score: {rr.tolerance_score}/100")
    print(f"  Blended score  : {rr.blended_score}/100")
    print(f"  Profile        : {rr.profile}  (base equity {rr.base_equity:.0%})")
    if rr.mismatch:
        print(f"  ! Note         : {rr.mismatch_note}")

    # ---- 2. Goals ----------------------------------------------------------
    goals = [
        # name, type, years, target_today, existing_corpus
        ("Emergency top-up",   "other",      2,   500_000,   100_000),
        ("Car",                "car",        4,  1_500_000,        0),
        ("Child education",    "education", 15,  4_000_000,   500_000),
        ("Retirement corpus",  "retirement", 28, 30_000_000, 2_000_000),
    ]

    print("\n" + "=" * 64)
    print("GOAL ALLOCATION & FUNDING PLAN")
    print("=" * 64)

    plans = []
    goal_dicts = []
    for name, gtype, yrs, tgt, corpus in goals:
        p = plan_goal(rr.profile, name, gtype, yrs, tgt, corpus)
        plans.append(p)
        goal_dicts.append({"name": name, "years": yrs, "target_today": tgt})

        cap_flag = " (horizon-capped)" if p.equity < rr.base_equity else ""
        print(f"\n  {name}  |  {yrs} yrs  |  type: {gtype}")
        print(f"    Allocation      : {p.equity:.0%} equity / {p.debt:.0%} debt{cap_flag}")
        print(f"    Expected return : {p.blended_return:.2%}")
        print(f"    Target today    : {inr(p.target_today)}")
        print(f"    Future cost     : {inr(p.future_value)}  (inflation-adjusted)")
        if p.existing_corpus:
            print(f"    Existing corpus : {inr(p.existing_corpus)} -> {inr(p.corpus_future_value)}")
        print(f"    Funding gap     : {inr(p.funding_gap)}")
        print(f"    Required SIP    : {inr(p.required_sip)} / month")
        print(f"    (or lumpsum now : {inr(p.required_lumpsum)})")

    # ---- 3. Blended portfolio & feasibility --------------------------------
    blend = portfolio_allocation(rr.profile, goal_dicts)
    print("\n" + "=" * 64)
    print("TOP-LINE PORTFOLIO (corpus-weighted across goals)")
    print("=" * 64)
    print(f"  {blend['equity']:.0%} equity / {blend['debt']:.0%} debt")

    ga = gap_analysis(plans, monthly_capacity=150_000)
    print("\n" + "=" * 64)
    print("FEASIBILITY (assuming Rs 1,50,000/month investable)")
    print("=" * 64)
    print(f"  Total SIP needed : {inr(ga['total_required_sip'])} / month")
    print(f"  Capacity         : {inr(ga['monthly_capacity'])} / month")
    print(f"  Coverage         : {ga['coverage_pct']}%")
    if ga["feasible"]:
        print(f"  Status           : FEASIBLE (surplus {inr(ga['surplus'])}/month)")
    else:
        print(f"  Status           : SHORTFALL of {inr(ga['shortfall'])}/month")
        print("                     -> extend horizons, raise savings, or reprioritise goals")


if __name__ == "__main__":
    main()

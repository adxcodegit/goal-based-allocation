"""
app.py
======
Streamlit front-end for the goal-based allocation tool.

Run locally with:
    streamlit run app.py

The UI is intentionally thin — all finance logic lives in the engine modules
(risk_profiler, allocator, planner) so it stays testable and reviewable.
"""

import pandas as pd
import streamlit as st

from config import CMA, RISK_PROFILES
from risk_profiler import QUESTIONS, score_profile
from allocator import goal_allocation, portfolio_allocation
from planner import plan_goal, gap_analysis
from funds import aggregate_categories
from report import build_report


st.set_page_config(page_title="Goal-Based Allocation Tool", layout="wide")


def inr(x: float) -> str:
    x = float(x)
    if abs(x) >= 1e7:
        return f"₹{x/1e7:.2f} Cr"
    if abs(x) >= 1e5:
        return f"₹{x/1e5:.2f} L"
    return f"₹{x:,.0f}"


# --------------------------------------------------------------------------- #
#  Sidebar: editable capital-market assumptions                               #
# --------------------------------------------------------------------------- #
st.sidebar.header("Capital market assumptions")
st.sidebar.caption("Long-run, nominal, pre-tax. Update from a primary source.")
CMA.equity_return = st.sidebar.number_input(
    "Equity return (Nifty 50 TRI, p.a.)", 0.05, 0.20, CMA.equity_return, 0.005,
    format="%.3f")
CMA.debt_return = st.sidebar.number_input(
    "Debt return (p.a.)", 0.03, 0.12, CMA.debt_return, 0.005, format="%.3f")
CMA.general_inflation = st.sidebar.number_input(
    "General inflation (p.a.)", 0.02, 0.12, CMA.general_inflation, 0.005,
    format="%.3f")
st.sidebar.caption(
    "Seeded: equity 12% (Nifty 50 TRI ~12.4% 20-yr CAGR, Mar-2026), "
    "debt 7%, inflation 6%. Education/healthcare inflate faster — see config.py."
)

st.title("Goal-Based Asset Allocation Tool")
st.caption(
    "Risk profile × time horizon → equity/debt split per goal → required SIP. "
    "For education and demonstration; not investment advice."
)

tab_risk, tab_goals, tab_plan = st.tabs(
    ["1 · Risk profile", "2 · Goals", "3 · Allocation & plan"]
)


# --------------------------------------------------------------------------- #
#  Tab 1 — Risk questionnaire                                                  #
# --------------------------------------------------------------------------- #
with tab_risk:
    st.subheader("Risk profiling questionnaire")
    st.write(
        "Answers measure two things separately: your **capacity** to take risk "
        "(objective) and your **tolerance** for it (behavioural)."
    )

    answers = {}
    cap_col, tol_col = st.columns(2)
    with cap_col:
        st.markdown("**Capacity — ability to take risk**")
        for q in [q for q in QUESTIONS if q["dimension"] == "capacity"]:
            labels = [o[0] for o in q["options"]]
            choice = st.radio(q["text"], labels, key=q["id"])
            answers[q["id"]] = dict(q["options"])[choice]
    with tol_col:
        st.markdown("**Tolerance — willingness to take risk**")
        for q in [q for q in QUESTIONS if q["dimension"] == "tolerance"]:
            labels = [o[0] for o in q["options"]]
            choice = st.radio(q["text"], labels, key=q["id"])
            answers[q["id"]] = dict(q["options"])[choice]

    rr = score_profile(answers)
    st.session_state["risk"] = rr

    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Capacity", f"{rr.capacity_score}/100")
    m2.metric("Tolerance", f"{rr.tolerance_score}/100")
    m3.metric("Blended", f"{rr.blended_score}/100")
    m4.metric("Profile", rr.profile)
    st.info(f"**{rr.profile}** — base allocation "
            f"{rr.base_equity:.0%} equity / {1-rr.base_equity:.0%} debt. "
            f"{RISK_PROFILES[rr.profile]['note']}")
    if rr.mismatch:
        st.warning(rr.mismatch_note)


# --------------------------------------------------------------------------- #
#  Tab 2 — Goals                                                               #
# --------------------------------------------------------------------------- #
with tab_goals:
    st.subheader("Financial goals")
    st.write("Enter each goal in **today's** money. It is inflated automatically.")
    st.caption(
        "Leave **Equity override %** blank to use the engine's horizon-adjusted "
        "allocation. Enter a number (0–100) to force a split for that goal — "
        "useful when the calculated mix is more balanced than you want."
    )

    default = pd.DataFrame([
        {"Goal": "Child education", "Type": "education", "Years": 15,
         "Target (today, ₹)": 4_000_000, "Existing corpus (₹)": 500_000,
         "Equity override %": None},
        {"Goal": "Retirement", "Type": "retirement", "Years": 28,
         "Target (today, ₹)": 30_000_000, "Existing corpus (₹)": 2_000_000,
         "Equity override %": None},
        {"Goal": "Car", "Type": "car", "Years": 4,
         "Target (today, ₹)": 1_500_000, "Existing corpus (₹)": 0,
         "Equity override %": None},
    ])
    edited = st.data_editor(
        default, num_rows="dynamic", use_container_width=True,
        column_config={
            "Type": st.column_config.SelectboxColumn(
                options=list(CMA.goal_inflation.keys())),
            "Years": st.column_config.NumberColumn(min_value=1, max_value=45, step=1),
            "Equity override %": st.column_config.NumberColumn(
                min_value=0, max_value=100, step=5,
                help="Optional. Blank = auto allocation."),
        },
    )
    st.session_state["goals"] = edited
    monthly_capacity = st.number_input(
        "How much can you invest per month? (₹)", 0, 10_000_000, 150_000, 5_000)
    st.session_state["capacity"] = monthly_capacity


# --------------------------------------------------------------------------- #
#  Tab 3 — Allocation & plan                                                   #
# --------------------------------------------------------------------------- #
with tab_plan:
    st.subheader("Recommended allocation & funding plan")
    rr = st.session_state.get("risk")
    goals_df = st.session_state.get("goals")

    if rr is None or goals_df is None or goals_df.empty:
        st.info("Complete the risk questionnaire and enter at least one goal.")
    else:
        plans, goal_dicts, rows = [], [], []
        for _, g in goals_df.iterrows():
            # The dynamic editor leaves trailing/blank rows. Skip any row that
            # is missing the essentials, and coerce types safely.
            goal_name = "" if pd.isna(g["Goal"]) else str(g["Goal"]).strip()
            if not goal_name or pd.isna(g["Years"]) or pd.isna(g["Target (today, ₹)"]):
                continue
            try:
                yrs = float(g["Years"])
                tgt = float(g["Target (today, ₹)"])
            except (TypeError, ValueError):
                continue
            if yrs <= 0 or tgt <= 0:
                continue
            corpus_val = g.get("Existing corpus (₹)", 0)
            corpus = 0.0 if pd.isna(corpus_val) else float(corpus_val)
            gtype = "other" if pd.isna(g["Type"]) else str(g["Type"])

            ov_val = g.get("Equity override %", None)
            equity_override = None
            if ov_val is not None and not pd.isna(ov_val):
                equity_override = float(ov_val) / 100.0

            p = plan_goal(rr.profile, goal_name, gtype, yrs, tgt, corpus,
                          equity_override=equity_override)
            plans.append(p)
            goal_dicts.append({"name": p.name, "years": yrs, "target_today": tgt})
            rows.append({
                "Goal": p.name + (" *" if p.overridden else ""),
                "Years": yrs,
                "Equity": f"{p.equity:.0%}",
                "Debt": f"{p.debt:.0%}",
                "Exp. return": f"{p.blended_return:.1%}",
                "Future cost": inr(p.future_value),
                "Funding gap": inr(p.funding_gap),
                "Monthly SIP": inr(p.required_sip),
            })

        if not plans:
            st.info("Enter at least one goal with a name, years, and target amount.")
            st.stop()

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        if any(p.overridden for p in plans):
            st.caption("\\* Allocation manually overridden for this goal.")

        blend = portfolio_allocation(rr.profile, goal_dicts)
        ga = gap_analysis(plans, st.session_state.get("capacity", 0))

        c1, c2, c3 = st.columns(3)
        c1.metric("Blended equity", f"{blend['equity']:.0%}")
        c2.metric("Total SIP needed", inr(ga["total_required_sip"]))
        c3.metric("Coverage", f"{ga['coverage_pct']}%")

        if ga["feasible"]:
            st.success(f"Plan is feasible — surplus of {inr(ga['surplus'])}/month.")
        else:
            st.error(
                f"Shortfall of {inr(ga['shortfall'])}/month. Options: extend "
                f"horizons, raise the monthly amount, or reprioritise goals."
            )
        st.caption(
            "Allocation per goal is the risk-profile equity weight, capped by a "
            "horizon glide-path (short goals are de-risked)."
        )

        # ---- Stage 2: fund categories -------------------------------------- #
        st.divider()
        st.markdown("### Suggested fund categories")
        st.caption(
            "SEBI scheme categories only — no scheme names. Equity is shaped by "
            "risk profile; debt is duration-matched to each goal's horizon; "
            "credit quality is kept high by default."
        )

        agg = aggregate_categories(plans)
        st.markdown("**Portfolio-level (corpus-weighted across goals)**")
        agg_rows = [{
            "Category": r["category"],
            "Sleeve": r["sleeve"],
            "Weight": f"{r['weight']*100:.1f}%",
        } for r in agg]
        st.dataframe(pd.DataFrame(agg_rows), use_container_width=True, hide_index=True)

        with st.expander("Per-goal category breakdown"):
            for p in plans:
                st.markdown(f"**{p.name}** — {p.equity:.0%} equity / {p.debt:.0%} debt, "
                            f"{p.years:g}y horizon")
                gr = [{
                    "Category": r["category"],
                    "Sleeve": r["sleeve"],
                    "Weight": f"{r['weight']*100:.1f}%",
                } for r in p.fund_categories]
                st.dataframe(pd.DataFrame(gr), use_container_width=True, hide_index=True)
                if p.exec_note:
                    st.caption("↪ " + p.exec_note)

        st.divider()
        st.markdown("#### Download report")
        client_name = st.text_input("Name for the report (optional)", "")
        html = build_report(rr, plans, blend, ga, CMA, client_name)
        st.download_button(
            "Download plan as report (HTML)",
            data=html,
            file_name="goal_based_allocation_report.html",
            mime="text/html",
        )
        st.caption(
            "Opens in any browser. To save as PDF, open it and use "
            "Print → Save as PDF."
        )

# --------------------------------------------------------------------------- #
#  Footer                                                                      #
# --------------------------------------------------------------------------- #
st.divider()
st.markdown(
    "<div style='text-align:center;color:#8a94a6;font-size:12.5px;line-height:1.7'>"
    "Built by <b>Aditya Nair</b> &nbsp;·&nbsp; Equity Research &amp; Portfolio Analytics<br>"
    "<a href='https://adityanair.co.in' target='_blank' style='color:#1b3a63'>adityanair.co.in</a>"
    " &nbsp;·&nbsp; "
    "<a href='https://github.com/adxcodegit' target='_blank' style='color:#1b3a63'>github.com/adxcodegit</a>"
    "<br><span style='font-size:11px'>Educational tool. Not investment advice.</span>"
    "</div>",
    unsafe_allow_html=True,
)

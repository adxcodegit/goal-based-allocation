"""
report.py
=========
Builds a self-contained, printable HTML report from the planning outputs.

Why HTML and not PDF: a single HTML string downloads instantly, opens in any
browser with no dependencies, and the user can Ctrl/Cmd+P -> "Save as PDF" to
get a clean PDF. This is the most robust path on Streamlit Community Cloud
(no system PDF libraries required).
"""

from datetime import date


def _inr(x: float) -> str:
    x = float(x)
    if abs(x) >= 1e7:
        return f"&#8377;{x/1e7:.2f} Cr"
    if abs(x) >= 1e5:
        return f"&#8377;{x/1e5:.2f} L"
    return f"&#8377;{x:,.0f}"


def build_report(risk, plans, blend, gap, cma, client_name: str = "") -> str:
    """
    risk  : RiskResult
    plans : list[GoalPlan]
    blend : {"equity": .., "debt": ..}
    gap   : gap_analysis(...) dict
    cma   : CapitalMarketAssumptions in force
    """
    today = date.today().strftime("%d %b %Y")
    total_fv = sum(p.future_value for p in plans)
    total_gap = sum(p.funding_gap for p in plans)

    goal_rows = "\n".join(
        f"""<tr>
              <td class="l">{p.name}</td>
              <td>{p.years:g}</td>
              <td>{p.equity:.0%} / {p.debt:.0%}</td>
              <td>{p.blended_return:.1%}</td>
              <td>{_inr(p.target_today)}</td>
              <td>{_inr(p.future_value)}</td>
              <td>{_inr(p.funding_gap)}</td>
              <td class="hi">{_inr(p.required_sip)}</td>
            </tr>"""
        for p in plans
    )

    feasibility = (
        f'<span class="ok">FEASIBLE</span> &mdash; surplus of '
        f'{_inr(gap["surplus"])}/month at the stated capacity.'
        if gap["feasible"]
        else f'<span class="bad">SHORTFALL</span> of {_inr(gap["shortfall"])}/month. '
             f'Consider extending horizons, raising the monthly amount, or '
             f'reprioritising goals.'
    )

    header_client = f"<p class='sub'>Prepared for: <b>{client_name}</b></p>" if client_name else ""

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Goal-Based Allocation Report</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
          color: #1a2233; margin: 0; padding: 40px; background: #fff; }}
  .wrap {{ max-width: 860px; margin: 0 auto; }}
  h1 {{ font-size: 22px; margin: 0 0 2px; }}
  h2 {{ font-size: 15px; margin: 28px 0 10px; padding-bottom: 6px;
        border-bottom: 2px solid #12305c; color: #12305c; }}
  .sub {{ color: #667; font-size: 12px; margin: 2px 0; }}
  .cards {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 8px 0 4px; }}
  .card {{ flex: 1 1 150px; border: 1px solid #dde3ee; border-radius: 8px;
           padding: 12px 14px; }}
  .card .k {{ font-size: 11px; color: #667; text-transform: uppercase;
              letter-spacing: .04em; }}
  .card .v {{ font-size: 20px; font-weight: 700; color: #12305c; margin-top: 2px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12.5px; margin-top: 4px; }}
  th, td {{ padding: 8px 9px; text-align: right; border-bottom: 1px solid #e6eaf2; }}
  th {{ background: #12305c; color: #fff; font-weight: 600; font-size: 11.5px; }}
  td.l, th.l {{ text-align: left; }}
  td.hi {{ font-weight: 700; color: #0b7; }}
  .ok {{ color: #0a8f4c; font-weight: 700; }}
  .bad {{ color: #c62828; font-weight: 700; }}
  .note {{ font-size: 11px; color: #778; margin-top: 6px; }}
  .foot {{ margin-top: 30px; padding-top: 12px; border-top: 1px solid #e6eaf2;
           font-size: 10.5px; color: #889; }}
  @media print {{ body {{ padding: 0; }} h2 {{ page-break-after: avoid; }} }}
</style></head>
<body><div class="wrap">

  <h1>Goal-Based Asset Allocation &amp; Funding Plan</h1>
  <p class="sub">Generated {today}</p>
  {header_client}

  <h2>Investor risk profile</h2>
  <div class="cards">
    <div class="card"><div class="k">Capacity</div><div class="v">{risk.capacity_score:g}/100</div></div>
    <div class="card"><div class="k">Tolerance</div><div class="v">{risk.tolerance_score:g}/100</div></div>
    <div class="card"><div class="k">Blended</div><div class="v">{risk.blended_score:g}/100</div></div>
    <div class="card"><div class="k">Profile</div><div class="v" style="font-size:15px">{risk.profile}</div></div>
  </div>
  <p class="note">Strategic base allocation for this profile:
     {risk.base_equity:.0%} equity / {1-risk.base_equity:.0%} debt.
     {"<br><b>Note:</b> " + risk.mismatch_note if risk.mismatch else ""}</p>

  <h2>Capital market assumptions used</h2>
  <p class="note">
     Equity (Nifty 50 TRI, long-run): <b>{cma.equity_return:.1%}</b> &nbsp;|&nbsp;
     Debt (long-run): <b>{cma.debt_return:.1%}</b> &nbsp;|&nbsp;
     General inflation: <b>{cma.general_inflation:.1%}</b>
     &nbsp; (education/healthcare inflate faster). Nominal, pre-tax, long-run
     averages &mdash; not forecasts.</p>

  <h2>Goal allocation &amp; funding plan</h2>
  <table>
    <thead><tr>
      <th class="l">Goal</th><th>Yrs</th><th>Equity/Debt</th><th>Exp. return</th>
      <th>Target (today)</th><th>Future cost</th><th>Funding gap</th><th>Monthly SIP</th>
    </tr></thead>
    <tbody>{goal_rows}</tbody>
  </table>
  <p class="note">Allocation per goal = risk-profile equity weight, capped by a
     time-horizon glide-path (short-dated goals are de-risked). Targets are in
     today's money and inflated to their future cost.</p>

  <h2>Summary</h2>
  <div class="cards">
    <div class="card"><div class="k">Blended allocation</div>
      <div class="v" style="font-size:15px">{blend['equity']:.0%} eq / {blend['debt']:.0%} debt</div></div>
    <div class="card"><div class="k">Total future cost</div><div class="v" style="font-size:15px">{_inr(total_fv)}</div></div>
    <div class="card"><div class="k">Total SIP needed</div><div class="v" style="font-size:15px">{_inr(gap['total_required_sip'])}/mo</div></div>
    <div class="card"><div class="k">Coverage</div><div class="v">{gap['coverage_pct']:g}%</div></div>
  </div>
  <p class="note" style="margin-top:10px">Feasibility: {feasibility}</p>

  <div class="foot">
    This report is generated for educational and illustrative purposes only and
    does not constitute investment advice. Projections use long-run average
    assumptions; realised returns vary and are path-dependent. Review with a
    SEBI-registered adviser before acting.
  </div>

</div></body></html>"""

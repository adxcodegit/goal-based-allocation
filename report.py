"""
report.py
=========
Builds a self-contained, print-ready HTML report from the planning outputs.

Design goals:
  * Looks like an advisory deliverable, not a script dump.
  * Zero external dependencies (no fonts/CDNs) so it renders identically
    offline and when the user does Print -> Save as PDF.
  * `print-color-adjust: exact` so the navy header, table bands, allocation
    bars and donut survive PDF export (browsers drop backgrounds otherwise).
"""

from datetime import date

from funds import aggregate_categories

# --- Branding (edit here) -------------------------------------------------- #
AUTHOR_NAME = "Aditya Nair"
AUTHOR_TAGLINE = "Equity Research &middot; Portfolio Analytics"
AUTHOR_SITE = "adityanair.co.in"
AUTHOR_GITHUB = "github.com/adxcodegit"


def _inr(x: float) -> str:
    x = float(x)
    if abs(x) >= 1e7:
        return f"&#8377;{x/1e7:.2f} Cr"
    if abs(x) >= 1e5:
        return f"&#8377;{x/1e5:.2f} L"
    return f"&#8377;{x:,.0f}"


def _alloc_bar(equity: float, debt: float) -> str:
    return (
        f'<div class="bar" title="{equity:.0%} equity / {debt:.0%} debt">'
        f'<span class="eq" style="width:{equity*100:.0f}%"></span>'
        f'<span class="dt" style="width:{debt*100:.0f}%"></span></div>'
        f'<div class="barlab">{equity:.0%} / {debt:.0%}</div>'
    )


def build_report(risk, plans, blend, gap, cma, client_name: str = "") -> str:
    today = date.today().strftime("%d %B %Y")
    total_fv = sum(p.future_value for p in plans)
    total_target = sum(p.target_today for p in plans)

    # Target-weighted expected return across goals (a headline figure).
    if total_target > 0:
        wtd_return = sum(p.blended_return * p.target_today for p in plans) / total_target
    else:
        wtd_return = 0.0

    eq_pct = blend["equity"] * 100

    goal_rows = "\n".join(
        f"""<tr>
              <td class="l"><b>{p.name}</b>{' <span class="ovr">override</span>' if p.overridden else ''}<div class="tag">{p.goal_type}</div></td>
              <td>{p.years:g}</td>
              <td class="alloc">{_alloc_bar(p.equity, p.debt)}</td>
              <td>{p.blended_return:.1%}</td>
              <td>{_inr(p.target_today)}</td>
              <td>{_inr(p.future_value)}</td>
              <td>{_inr(p.funding_gap)}</td>
              <td class="hi">{_inr(p.required_sip)}<span class="mo">/mo</span></td>
            </tr>"""
        for p in plans
    )

    if gap["feasible"]:
        feas_class, feas_label = "ok", "FEASIBLE"
        feas_text = f"Surplus of {_inr(gap['surplus'])} per month at the stated capacity."
    else:
        feas_class, feas_label = "bad", "SHORTFALL"
        feas_text = (f"Gap of {_inr(gap['shortfall'])} per month. Options: extend "
                     f"horizons, raise the monthly amount, or reprioritise goals.")

    header_client = (f'<span class="meta-item">Prepared for &nbsp;<b>{client_name}</b></span>'
                     if client_name else "")
    mismatch_html = (f'<p class="callout">{risk.mismatch_note}</p>'
                     if risk.mismatch else "")

    # Stage 2 — portfolio-level fund category breakdown
    agg = aggregate_categories(plans)
    max_w = max((r["weight"] for r in agg), default=1) or 1
    cat_rows = "\n".join(
        f"""<tr>
              <td class="l">{r['category']}</td>
              <td class="l"><span class="pill {'eqp' if r['sleeve']=='Equity' else 'dtp'}">{r['sleeve']}</span></td>
              <td class="catbarcell">
                <div class="catbar"><span class="{'eq' if r['sleeve']=='Equity' else 'dt'}"
                     style="width:{r['weight']/max_w*100:.0f}%"></span></div>
              </td>
              <td class="hi" style="color:var(--navy)">{r['weight']*100:.1f}%</td>
            </tr>"""
        for r in agg
    )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Goal-Based Allocation Report</title>
<style>
  :root {{
    --navy:#0f2544; --navy2:#1b3a63; --bronze:#b98a3c; --bronze-l:#d8bd85;
    --ink:#1c2430; --muted:#6b7688; --line:#e4e8f0; --soft:#f7f9fc;
    --ok:#1a7f4b; --bad:#c0392b;
  }}
  * {{ box-sizing:border-box; }}
  html,body {{ -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
          color:var(--ink); margin:0; background:#eef1f6; line-height:1.5; }}
  .page {{ max-width:900px; margin:24px auto; background:#fff;
           box-shadow:0 4px 24px rgba(15,37,68,.10); }}
  /* Header band */
  .hero {{ background:linear-gradient(120deg,var(--navy),var(--navy2));
           color:#fff; padding:30px 44px 26px; position:relative; }}
  .hero::after {{ content:""; position:absolute; left:0; right:0; bottom:0;
                  height:4px; background:var(--bronze); }}
  .hero h1 {{ font-family:Georgia,"Times New Roman",serif; font-weight:600;
              font-size:25px; margin:0; letter-spacing:.2px; }}
  .hero .kick {{ text-transform:uppercase; letter-spacing:.18em; font-size:10.5px;
                 color:var(--bronze-l); margin:0 0 6px; }}
  .hero .brand {{ position:absolute; top:30px; right:44px; text-align:right; }}
  .hero .brand .nm {{ font-family:Georgia,serif; font-size:15px; }}
  .hero .brand .tl {{ font-size:10.5px; color:var(--bronze-l); letter-spacing:.04em; }}
  .meta {{ padding:12px 44px; background:var(--soft); border-bottom:1px solid var(--line);
           font-size:12px; color:var(--muted); display:flex; gap:26px; flex-wrap:wrap; }}
  .body {{ padding:26px 44px 8px; }}
  h2 {{ font-family:Georgia,serif; font-weight:600; font-size:15.5px; color:var(--navy);
        margin:30px 0 12px; padding-bottom:7px; border-bottom:1.5px solid var(--line);
        display:flex; align-items:center; gap:9px; }}
  h2::before {{ content:""; width:9px; height:9px; background:var(--bronze);
                transform:rotate(45deg); display:inline-block; }}
  /* Metric cards */
  .cards {{ display:flex; gap:12px; flex-wrap:wrap; }}
  .card {{ flex:1 1 130px; border:1px solid var(--line); border-radius:9px;
           padding:13px 15px; background:#fff; }}
  .card .k {{ font-size:10px; color:var(--muted); text-transform:uppercase;
              letter-spacing:.07em; }}
  .card .v {{ font-size:22px; font-weight:700; color:var(--navy); margin-top:3px;
              font-variant-numeric:tabular-nums; }}
  .card.accent {{ background:var(--navy); border-color:var(--navy); }}
  .card.accent .k {{ color:var(--bronze-l); }}
  .card.accent .v {{ color:#fff; font-size:16px; }}
  .statement {{ font-size:12.5px; color:var(--ink); margin:12px 0 0;
                background:var(--soft); border-left:3px solid var(--bronze);
                padding:10px 14px; border-radius:0 6px 6px 0; }}
  .callout {{ font-size:12px; color:#8a5a00; background:#fdf6e7;
              border:1px solid #f0dca8; border-radius:6px; padding:10px 13px; margin-top:10px; }}
  .assum {{ display:flex; gap:22px; flex-wrap:wrap; font-size:12.5px; color:var(--ink);
            background:var(--soft); border:1px solid var(--line); border-radius:8px; padding:13px 16px; }}
  .assum b {{ color:var(--navy); }}
  .assum .note {{ color:var(--muted); font-size:11px; }}
  /* Table */
  table {{ width:100%; border-collapse:collapse; font-size:12px; margin-top:4px; }}
  th,td {{ padding:10px 9px; text-align:right; border-bottom:1px solid var(--line);
           font-variant-numeric:tabular-nums; }}
  th {{ background:var(--navy); color:#fff; font-weight:600; font-size:10.5px;
        text-transform:uppercase; letter-spacing:.05em; }}
  td.l,th.l {{ text-align:left; }}
  tbody tr:nth-child(even) {{ background:var(--soft); }}
  .tag {{ font-size:9.5px; color:var(--muted); text-transform:uppercase;
          letter-spacing:.05em; margin-top:2px; }}
  td.hi {{ font-weight:700; color:var(--navy); }}
  td.hi .mo {{ font-weight:400; color:var(--muted); font-size:10px; }}
  td.alloc {{ min-width:96px; }}
  .bar {{ display:flex; height:9px; border-radius:5px; overflow:hidden;
          background:var(--line); }}
  .bar .eq {{ background:var(--navy2); }}
  .bar .dt {{ background:var(--bronze); }}
  .barlab {{ font-size:9.5px; color:var(--muted); margin-top:3px; text-align:center; }}
  /* Summary row with donut */
  .summary {{ display:flex; gap:22px; align-items:center; flex-wrap:wrap; margin-top:6px; }}
  .donut {{ width:118px; height:118px; border-radius:50%; flex:0 0 auto;
            background:conic-gradient(var(--navy2) 0 {eq_pct:.1f}%, var(--bronze) {eq_pct:.1f}% 100%);
            display:flex; align-items:center; justify-content:center; }}
  .donut .hole {{ width:76px; height:76px; border-radius:50%; background:#fff;
                  display:flex; flex-direction:column; align-items:center; justify-content:center; }}
  .donut .hole b {{ font-size:20px; color:var(--navy); }}
  .donut .hole span {{ font-size:9px; color:var(--muted); text-transform:uppercase; letter-spacing:.06em; }}
  .legend {{ font-size:11.5px; color:var(--ink); }}
  .legend .sw {{ display:inline-block; width:10px; height:10px; border-radius:2px;
                 margin-right:6px; vertical-align:middle; }}
  .banner {{ margin-top:14px; border-radius:8px; padding:12px 16px; font-size:12.5px;
             display:flex; align-items:center; gap:10px; }}
  .banner.ok {{ background:#eaf6ef; border:1px solid #bfe3cc; }}
  .banner.bad {{ background:#fdeeec; border:1px solid #f3c9c2; }}
  .badge {{ font-size:10.5px; font-weight:700; letter-spacing:.06em; padding:3px 9px;
            border-radius:20px; color:#fff; }}
  .badge.ok {{ background:var(--ok); }}
  .badge.bad {{ background:var(--bad); }}
  .note {{ font-size:11px; color:var(--muted); margin-top:8px; }}
  .ovr {{ font-size:9px; font-weight:700; letter-spacing:.05em; color:#8a5a00;
          background:#fbeecb; border:1px solid #f0dca8; border-radius:10px;
          padding:1px 7px; vertical-align:middle; text-transform:uppercase; }}
  .pill {{ font-size:9.5px; font-weight:600; letter-spacing:.04em; padding:2px 9px;
           border-radius:20px; text-transform:uppercase; }}
  .pill.eqp {{ background:#e7edf6; color:var(--navy2); }}
  .pill.dtp {{ background:#f7efdd; color:#8a6320; }}
  .catbarcell {{ width:42%; }}
  .catbar {{ height:9px; border-radius:5px; background:var(--line); overflow:hidden; }}
  .catbar .eq {{ display:block; height:100%; background:var(--navy2); }}
  .catbar .dt {{ display:block; height:100%; background:var(--bronze); }}
  /* Footer */
  .foot {{ margin-top:26px; background:var(--navy); color:#c7d2e3;
           padding:20px 44px; }}
  .foot .sig {{ display:flex; justify-content:space-between; align-items:flex-end;
                flex-wrap:wrap; gap:12px; border-bottom:1px solid rgba(255,255,255,.14);
                padding-bottom:14px; margin-bottom:12px; }}
  .foot .sig .nm {{ font-family:Georgia,serif; font-size:17px; color:#fff; }}
  .foot .sig .tl {{ font-size:11px; color:var(--bronze-l); letter-spacing:.05em; }}
  .foot .sig .lnk {{ font-size:11px; text-align:right; line-height:1.7; }}
  .foot .disc {{ font-size:9.8px; color:#8ea0ba; line-height:1.55; }}
  @media print {{
    body {{ background:#fff; }}
    .page {{ margin:0; box-shadow:none; max-width:none; }}
    h2 {{ page-break-after:avoid; }}
    tr {{ page-break-inside:avoid; }}
  }}
</style></head>
<body><div class="page">

  <div class="hero">
    <div class="brand">
      <div class="nm">{AUTHOR_NAME}</div>
      <div class="tl">{AUTHOR_TAGLINE}</div>
    </div>
    <p class="kick">Financial Planning &middot; Confidential</p>
    <h1>Goal-Based Asset Allocation &amp; Funding Plan</h1>
  </div>

  <div class="meta">
    <span class="meta-item">Date &nbsp;<b>{today}</b></span>
    {header_client}
    <span class="meta-item">Risk profile &nbsp;<b>{risk.profile}</b></span>
  </div>

  <div class="body">

    <h2>Investor risk profile</h2>
    <div class="cards">
      <div class="card"><div class="k">Capacity</div><div class="v">{risk.capacity_score:g}</div></div>
      <div class="card"><div class="k">Tolerance</div><div class="v">{risk.tolerance_score:g}</div></div>
      <div class="card"><div class="k">Blended</div><div class="v">{risk.blended_score:g}</div></div>
      <div class="card accent"><div class="k">Profile</div><div class="v">{risk.profile}</div></div>
    </div>
    <p class="statement">Strategic base allocation for this profile:
       <b>{risk.base_equity:.0%} equity / {1-risk.base_equity:.0%} debt.</b>
       Each goal is then adjusted for its time horizon.</p>
    {mismatch_html}

    <h2>Capital market assumptions</h2>
    <div class="assum">
      <span>Equity (Nifty 50 TRI) &nbsp;<b>{cma.equity_return:.1%}</b></span>
      <span>Debt &nbsp;<b>{cma.debt_return:.1%}</b></span>
      <span>Inflation &nbsp;<b>{cma.general_inflation:.1%}</b></span>
      <span class="note">Long-run, nominal, pre-tax averages &mdash; not forecasts.
        Education &amp; healthcare inflate faster.</span>
    </div>

    <h2>Goal allocation &amp; funding plan</h2>
    <table>
      <thead><tr>
        <th class="l">Goal</th><th>Yrs</th><th>Equity / Debt</th><th>Exp. return</th>
        <th>Target (today)</th><th>Future cost</th><th>Funding gap</th><th>Monthly SIP</th>
      </tr></thead>
      <tbody>{goal_rows}</tbody>
    </table>
    <p class="note">Allocation per goal = the risk-profile equity weight, capped by a
       time-horizon glide-path so near-term goals are de-risked. Targets are in
       today's money and inflated to their future cost.</p>

    <h2>Portfolio summary</h2>
    <div class="summary">
      <div class="donut"><div class="hole"><b>{blend['equity']:.0%}</b><span>Equity</span></div></div>
      <div>
        <div class="legend"><span class="sw" style="background:var(--navy2)"></span>
          Equity &nbsp;<b>{blend['equity']:.0%}</b></div>
        <div class="legend" style="margin-top:6px"><span class="sw" style="background:var(--bronze)"></span>
          Debt &nbsp;<b>{blend['debt']:.0%}</b></div>
        <div class="note" style="margin-top:8px">Corpus-weighted across all goals.</div>
      </div>
      <div class="cards" style="flex:1 1 320px">
        <div class="card"><div class="k">Total future cost</div><div class="v" style="font-size:16px">{_inr(total_fv)}</div></div>
        <div class="card"><div class="k">Total SIP</div><div class="v" style="font-size:16px">{_inr(gap['total_required_sip'])}<span style="font-size:11px;color:var(--muted)">/mo</span></div></div>
        <div class="card"><div class="k">Wtd. exp. return</div><div class="v" style="font-size:16px">{wtd_return:.1%}</div></div>
      </div>
    </div>
    <div class="banner {feas_class}">
      <span class="badge {feas_class}">{feas_label}</span>
      <span>{feas_text} &nbsp;Coverage of goals by current capacity: <b>{gap['coverage_pct']:g}%</b>.</span>
    </div>

    <h2>Suggested fund categories</h2>
    <p class="note" style="margin-top:0">SEBI scheme categories only (no scheme
       names). Equity is shaped by risk profile; debt is duration-matched to
       horizon; credit quality is kept high by default. Corpus-weighted across goals.</p>
    <table>
      <thead><tr>
        <th class="l">Category</th><th class="l">Sleeve</th>
        <th class="l">Relative weight</th><th>Allocation</th>
      </tr></thead>
      <tbody>{cat_rows}</tbody>
    </table>

  </div>

  <div class="foot">
    <div class="sig">
      <div>
        <div class="nm">{AUTHOR_NAME}</div>
        <div class="tl">{AUTHOR_TAGLINE}</div>
      </div>
      <div class="lnk">{AUTHOR_SITE}<br>{AUTHOR_GITHUB}</div>
    </div>
    <div class="disc">This report is generated for educational and illustrative purposes only
      and does not constitute investment advice. Projections use long-run average assumptions;
      realised returns vary and are path-dependent. Figures are pre-tax. Please review with a
      SEBI-registered investment adviser before acting.</div>
  </div>

</div></body></html>"""

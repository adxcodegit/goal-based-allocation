# Goal-Based Asset Allocation Tool

A Python tool that turns a **risk profile** and a set of **financial goals** into
a recommended **equity/debt allocation per goal** and the **monthly SIP** required
to fund each goal. Built around Indian-market conventions.

The design goal is to behave like a real wealth-management planning tool rather
than a one-page risk quiz: allocation is driven by *both* the investor's risk
profile *and* each goal's time horizon, goals are inflation-adjusted, and the
plan is checked for feasibility against how much the investor can actually save.

> Educational / portfolio project. Not investment advice.

---

## What it does (Stage 1)

1. **Risk profiling** — a questionnaire scored on two separate axes:
   - *Capacity* (ability to take risk): age, income stability, dependents,
     emergency buffer, savings rate.
   - *Tolerance* (willingness): drawdown reaction, experience, growth-vs-safety
     preference, preferred outcome range.
   Capacity is weighted slightly higher, and the tool flags the classic
   "aggressive on paper, panics in a crash" mismatch, moderating the profile
   toward capacity when willingness runs too far ahead of ability.

2. **Allocation** — maps the profile to a strategic equity/debt split, then
   applies a **horizon glide-path** so short-dated goals are de-risked
   regardless of profile (you don't put next year's school fee in the Nifty).

3. **Returns** — uses long-run assumptions, seeded from real figures and fully
   editable in the sidebar (and in `config.py`):
   - Equity **12%** — Nifty 50 TRI ~12.4% 20-yr CAGR (NSE, Mar-2026); long-run
     range historically 11–15%.
   - Debt **7%** — Indian debt funds / high-quality accrual ~6–8% p.a. long-run.
   - Inflation **6%** general; education 10%, healthcare 8% (they inflate faster).

4. **Funding plan** — for each goal: inflate the target to its future cost,
   blend the expected return from its allocation, grow any existing corpus, and
   solve for the monthly SIP (annuity-due, effective monthly rate). Then check
   total SIP against the investor's monthly capacity.

### Stage 2 (extension point)
Map each goal's equity/debt weight to specific **fund categories** — large-cap /
flexi-cap / hybrid / short-duration debt / liquid — based on horizon and profile.
The allocation output is already structured to slot this in.

---

## How the allocation is computed

```
base_equity     = profile → strategic equity weight
horizon_cap     = f(years to goal)      # glide-path
goal_equity     = clamp(base_equity, floor, horizon_cap)
goal_debt       = 1 - goal_equity
```

**Strategic weights by profile**

| Profile | Equity | Debt |
|---|---|---|
| Conservative | 20% | 80% |
| Moderately Conservative | 35% | 65% |
| Balanced | 50% | 50% |
| Moderately Aggressive | 70% | 30% |
| Aggressive | 85% | 15% |

**Horizon glide-path (equity cap)**

| Years to goal | Max equity |
|---|---|
| 0–2 | 10% |
| 3–5 | 30% |
| 5–7 | 50% |
| 7–10 | 65% |
| 10–15 | 80% |
| 15+ | profile governs |

**Funding math**

```
FV        = target_today × (1 + goal_inflation)^years
r         = w_eq × r_equity + w_debt × r_debt
corpus_FV = existing_corpus × (1 + r)^years
gap       = max(0, FV − corpus_FV)
SIP       = gap × r_m / ((1 + r_m)^n − 1) ÷ (1 + r_m)   # annuity-due, monthly
```

---

## Run it

```bash
pip install -r requirements.txt

# command-line demo (no UI) — runs a sample investor end to end
python demo.py

# interactive app
streamlit run app.py
```

## Project layout

| File | Responsibility |
|---|---|
| `config.py` | All assumptions & allocation policy (single source of truth) |
| `risk_profiler.py` | Questionnaire + capacity/tolerance scoring |
| `allocator.py` | Profile → allocation, horizon glide-path |
| `planner.py` | Inflation, expected return, SIP, gap analysis |
| `app.py` | Streamlit UI |
| `demo.py` | CLI walkthrough / smoke test |

## Design notes & honest caveats

- **Nominal framing.** Goals are inflated and returns are nominal — cleaner and
  more intuitive for a client than real-return framing. Equivalent, not sloppy.
- **Assumptions ≠ forecasts.** The seeded returns are long-run averages; realised
  returns are path-dependent and sequence risk is real, which is exactly why the
  glide-path de-risks near-term goals.
- **Single blended return per goal** — no Monte Carlo yet. A natural next step is
  a return-distribution simulation to show a probability of funding each goal.
- **Refresh the inputs.** Update the capital-market assumptions periodically from
  a primary source (NSE Indices, Value Research, RBI) rather than trusting the
  seeded defaults indefinitely.

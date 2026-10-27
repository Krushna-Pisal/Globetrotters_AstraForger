# 15 — Problem-Statement Alignment Review (27 Oct 2026)

Compares what the organizers asked for against what we have built (prototype on `main`: M0–M3 engines, role views,
password login, plant-configuration mock) and planned (docs/01–14). **The organizers' material takes priority over our
docs.** Planning material only; the finale build starts from a fresh repo (docs/14).

Organizer sources:
- **PS4 card** — "Build one underlying model of a plant's design, expected performance, and actual performance. Construct
  three distinct views from that single source — and be explicit about what each role needs to see, and what's
  deliberately left out."
- **Roadmap Research Guide** — 11-layer digital thread; PS4 maps to *all 11 layers* and *all six questions* ("the whole
  thread, not one layer"); the one rule (baseline never decides what is paid); attribution must use several named,
  non-overlapping causes with no silent leftover; the digital twin is one representation for any plant type (solar, gas
  turbine, battery, water treatment, hybrid).
- **Finale briefing** — new datasets, a test endpoint and surprise changes are likely; UI/UX is marked.

---

## 1. Layer-by-layer status of the prototype

| # | Guide layer | Prototype today | Status | Finale action |
|---|---|---|---|---|
| 1 | Plant design | `configs/plant/*.yaml`; plant-configuration page (UI mock) | ✅ | Keep; config drives everything |
| 2 | Engineering digital twin | Asset templates + plant → block → inverter hierarchy; battery template is a stub | ✅ (solar) | Plant-type adapter interface (type decided by the dataset) |
| 3 | Performance model | pvlib chain; real-data mode (fit on measured irradiance) | ✅ | Adapter per type; real-data mode as the generic fallback |
| 4 | Expected plant output | `expected_output` per unit and interval, with uncertainty band and model version | ✅ | Keep |
| 5 | Plant operations | Measurements, status codes, events, operator log, work orders | ✅ | Keep |
| 6 | Actual plant output | Validated `actual_output`, quality flags, data-quality score | ✅ | Keep |
| 7 | Output accounting | Delivery-point ledger: meter = accountable, export loss, meter-vs-inverter reconciliation | ⚠️ partial | **Gap 4**: boundary/loss rules, shared-asset allocation, grid-operator reconciliation |
| 8 | Accounting & settlement | PPA: 5 clause lines, deemed generation (backdown, grid), CUF band; O&M LDs in a separate module/table | ✅ (fixed tariff only) | **Gap 3**: tariff escalation/indexation; availability-based payments if the dataset is storage/thermal |
| 9 | Actual technical + financial performance | `finance_period`: settled revenue, LDs, opex, tax, CFADS, DSCR YTD | ⚠️ partial | Roll up in the **same shape as the baseline** (incl. PR) |
| 10 | Plan vs actual | CFO: revenue and energy vs P50/P90, DSCR vs covenants | ⚠️ partial | **Gap 5**: stage-by-stage plan-vs-actual table |
| 11 | Performance attribution | UI shows a *preliminary* event-window waterfall; full bridges, residual policy and liability map were parked (branch `wip/m4-attribution`) | ⚠️ partial | **Gap 6**: a simplified attribution that still closes is a Must |

## 2. The six questions

| Q | Question (guide §3) | Prototype today | Status |
|---|---|---|---|
| Q1 | Producing what the investment case assumed? | CFO tiles and chart: delivered energy vs P50/P90, revenue vs P50 | ✅ |
| Q2 | Resource, availability, equipment, operations, grid or commercial? | Engineer waterfall by event category (outages, grid, curtailment, underperformance) + "not yet attributed"; weather vs plant split not shown | ⚠️ |
| Q3 | Accounted and settled numbers match measurement and contract? | Meter reconciliation computed but not shown; settlement lines shown | ⚠️ show the checks |
| Q4 | Generation problem or tariff/settlement problem? | Not in the UI (revenue bridge parked); tariff is fixed so the price effect is always zero | ❌ |
| Q5 | Explainable, controllable, recoverable? | Controllable colours; CFO "recovered" tile; liability map parked | ⚠️ |
| Q6 | Repeating deviations → structural issue? | CFO escalation by recurrence (IGBT_OVERTEMP escalates in July) and materiality | ✅ |

## 3. The PS4 sentence itself

| Requirement | Prototype | Status |
|---|---|---|
| One underlying model of design, expected and actual | Plant config → twin → expected → actual, one database | ✅ |
| Three distinct views from that single source | Engineer, Operations, Finance pages from the same tables; the presenter receives byte-identical payloads per lens | ✅ |
| Explicit about what each role **needs to see** | Each page states its decision; lens YAML lists metrics | ✅ |
| Explicit about what is **deliberately left out** | Server strips and lists omissions with reasons (`omitted`, `stripped`) — **but the UI panel was removed on 18 Oct** | ❌ **restore** |
| The one rule (baseline never decides payment) | Settlement firewall enforced by import-linter; frozen baseline trigger | ✅ strongest match |

---

## 4. Gaps and decisions

Gaps 2 (plant type) and 7 (model choice) are settled by the dataset the organizers provide; the plan only keeps the
architecture type-independent (adapter interface + real-data mode).

### Gap 1 — "Deliberately left out" must be visible (Must)
- Every role view shows a compact **"Left out of this view (N)"** element in the page header that opens a drawer:
  each item with its reason, the rule that would bring it back (materiality, recurrence, covenant watch, drill-down),
  and the server's stripped-item receipt.
- The overview shows a small matrix: rows = information items, columns = roles, cells = shown / left out (with reason).
  This is the PS4 sentence turned into one screen.

### Gap 3 — Tariff escalation / indexation (Must, small)
- Contract config: `tariff: {base, escalation: none | fixed_pct | index_linked, rate, anniversary, index_series}`.
- Settlement uses the tariff in force for each period; the baseline freezes the **case's assumed** tariff path.
- Revenue bridge: price effect = (actual tariff − case tariff) × volume (symmetric split already in docs/02 §7.5), so
  Q4 can answer "tariff/settlement problem" when indexation outturn differs from the case.
- Demo: a contract with an annual escalation from the anniversary date, and a case that assumed a different rate.

### Gap 4 — Accountable output after boundary and loss rules (Should, minimal Must)
- Config per plant: settlement metering point, boundary loss factor (e.g. pooling-substation/transmission share),
  shared-asset allocation rule (pro-rata to each plant's injection at a shared meter), grid-operator energy statement.
- Accountable = boundary meter − allocated losses; reconciled against the grid-operator statement; differences become a
  named line in the residual evidence (never silently absorbed).
- Minimal on the day: one loss-factor rule + a reconciliation check shown to the CFO and the engineer.

### Gap 5 — Plan-vs-actual table in the guide's own shape (Must)
- CFO view (and presenter overview), per period and year-to-date:

| Metric | Baseline | Actual | Variance | Attribution (named causes with amounts) |
|---|---|---|---|---|
| Generation | P50 | accountable | Δ | weather, availability, soiling, curtailment, grid, residual |
| Performance ratio (or the plant type's KPI) | case PR | actual PR | Δ pts | temperature, inverter/turbine, soiling, downtime |
| Revenue | case revenue | settled | Δ | volume, tariff/indexation, penalties, deemed generation |
| DSCR | case DSCR | actual YTD | Δ | operating and commercial drivers |

- Needs the baseline to store the **case PR** (and case DSCR) next to P50 — a small change to the baseline build.

### Gap 6 — A thin but complete thread (Must)
PS4 is "all 11 layers, all six questions". On the day, every layer gets a simple, honest implementation rather than a
few layers in depth:
- Layer 7 one boundary rule; layer 8 energy charge + one deemed-generation clause + escalation; layer 9 roll-up in the
  baseline's shape; layer 10 the table above; layer 11 a closing bridge with an explicit residual (simplified
  precedence: outage → grid → curtailment → underperformance → residual; soiling if the data supports it).
- Cut first if time runs short: synthetic-year richness, scorecard, Rosetta card, lineage drill-down, work-order
  transitions.

### Also worth carrying over from the prototype review
- **Q3 trust check on screen:** show three reconciliation results (energy bridge closes, money closes, settlement
  independent of the baseline) as badges computed by the server.
- **Weather vs plant split** (Q2, resource vs everything else): the bridge's first step (baseline on actual weather).

---

## 5. What already matches well (keep)
- Frozen, versioned baseline with a DB trigger, and the settlement firewall — the guide's "one rule".
- PPA settlement and O&M liquidated damages as two separate cash flows.
- Variance against the baseline's *own* assumed losses (no double counting), explicit residual.
- Server-enforced role views with payload guard; role only from the signed token.
- Recurrence/materiality escalation (Q6) and deemed generation.
- Provenance on every row; synthetic and measured never share a dataset.
- Deterministic engines; any model runs locally and never computes a metric.

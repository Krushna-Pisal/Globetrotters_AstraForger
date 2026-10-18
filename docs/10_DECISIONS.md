# 10 — Decision Log

Append new decisions at the bottom. Each: id, date, decision, why, consequence.

## Locked (v2.1, 17 Oct 2026)
| ID | Decision | Why |
|---|---|---|
| D01 | One canonical store + one metric registry + three server-enforced lens contracts | The PS asks for one model, three views; judges penalise three drifting dashboards |
| D02 | One solar plant fully; other plant types schema-only (stretch) | Depth beats breadth; rubric favours a correct model |
| D03 | Two datasets: `kaggle_p2_2020` (real slice) and `thar1_demo_2024` (synthetic scenario year) | Real-data credibility + a full, scoreable story (docs/06) |
| D04 | Kaggle **Plant 2**, not Plant 1 | Plant 1 DC_POWER ≈ 10× AC (AC/DC ≈ 9.8 %); Plant 2 AC/DC ≈ 97.8 % |
| D05 | INR only, Indian context, SECI-style PPA clauses, CUF on AC capacity | One currency, coherent story |
| D06 | Frontend: React + TypeScript + Vite, no Next.js | Quest rule "React only" |
| D07 | No public AI APIs; any model local (Ollama); no LLM computes numbers | Quest rule + explainability |
| D08 | PostgreSQL only (no Timescale/Redis/Kafka in MVP) | Simplicity; volumes are small (20 inverters × 35k intervals) |
| D09 | Demo JWT with four users; role from token only | Offline demo; makes server enforcement visible |

## Corrections adopted from the v2.0 plan review
| ID | Was | Now | Why |
|---|---|---|---|
| C01 | Waterfall subtracted full availability and soiling losses | Buckets = actual − baseline-assumed (docs/02 §7.1); E_potential and baseline share one loss register | P50 already assumes soiling/availability; gross subtraction double-counts |
| C02 | PPA penalty tied to the O&M availability guarantee | Two contracts: PPA settlement (C4.1–C4.5) vs O&M LDs in separate tables/modules | Availability guarantees belong to the O&M contract, not the PPA |
| C03 | Deemed generation = modelled lost energy | Contract formulas: backdown 50 % × avg gen/hour × hours; grid unavailability beyond 175.2 h threshold | That is how Indian PPA clauses compute it; the gap is the owner's loss (liability map) |
| C04 | CFADS defined as revenue − opex ("not EBITDA") | CFADS = revenue + LDs − opex − tax − maintenance capex (± WC, reserves = 0 in MVP) | Revenue − opex *is* EBITDA |
| C05 | Tariff indexation in the formula | Fixed tariff, `indexation: none` | Typical Indian solar PPAs |
| C06 | Reconciliation chip "MWh × ₹" on every number | Chips use only lens-allowed parts; cross-lens jumps are authorised requests | The old chip leaked tariff into the Engineer view |
| C07 | "CFO never receives engineer data" + "every CFO number links to engineer evidence" | Default payload omits; lineage drill-down is authorised and redacted per lens | The two claims contradicted each other |
| C08 | Role switcher on one login | Token swap between demo users; stripped-field receipt shown | Otherwise enforcement is invisible |
| C09 | Modbus/OPC UA SCADA layer in the core path | Stretch S2; replay/WebSocket is S1 | Too risky for the timeline; not separately rewarded by the rubric |
| C10 | Isolation Forest anomaly detection, portfolio detection | Cut | Conflicts with "deterministic by design"; little rubric value |
| C11 | Degradation bucket computed from one year | Bar shown with "requires ≥ 24 months" flag | Not separable from soiling/noise within 12 months |
| C12 | Peer-deviation threshold 0.85 per interval | Daily peer ratio < 0.95 for ≥ 3 days, plus band-aware expected-shortfall rule | An 8 % string-fuse derate would never trip 0.85 |

## Added during M0 (18 Oct 2026)
| ID | Decision | Why | Consequence |
|---|---|---|---|
| D10 | `liability_kwh` added to the CFO lens allowlist | The CFO `liability_map` section (docs/05) shows kWh per bearer; without the metric the server guard would strip it | `configs/lenses/cfo.yaml` updated |
| D11 | `accounting_ledger` gains `hours_with_generation`, `backdown_hours`, `grid_unavail_hours_counted` | Settlement may import only accounting/contracts/core, yet C4.4/C4.5 need these hour counts | docs/04 §6 updated; columns land in the M3 migration |
| D12 | Settlement firewall is an allowlist in spirit: every `app.*` package except accounting, contracts, core is forbidden | docs/03 listed only five forbidden modules, weaker than CLAUDE.md invariant 2 | docs/03 §2 and `.importlinter` updated |
| D13 | `source_kind` includes `operator` | docs/04 enum and `work_order.source_kind` use it; CLAUDE.md invariant 8 omitted it | CLAUDE.md updated |
| D14 | Windows dev: GNU make 4.4 (winget `ezwinports.make`); all make targets run inside Docker containers | Same commands on every OS; no local Python/Postgres needed | `make test`/`make lint` require `make up` (images built) |

## Added during M1–M3 (18 Oct 2026)
| ID | Decision | Why | Consequence |
|---|---|---|---|
| D15 | New table `operator_log` (acknowledged/onsite/restored/verified/cleaning timestamps per asset) | docs/02 §8.3 needs operator records for SLA clocks and docs/06 §5 a cleaning log; docs/04 had no table | Migration 0002; work orders read lifecycle times from it |
| D16 | `configs/plant/kgl_p2.yaml`: 22 inverters keyed by Kaggle SOURCE_KEY; rated AC **inferred** = max per-inverter p99.9 AC_POWER (1,349.5 kW) | The dataset publishes no nameplate; quality rules need a rating | Night/over-rating flags use the inferred rating; labelled inferred |
| D17 | SCADA status dictionary in the plant config (`status_codes`: code → category, cause, controllable) | Detection must map status codes to causes without reading the scenario | During plant OFFLINE inverters report `WAIT_GRID` (normal), so precedence never books grid loss as availability |
| D18 | Daylight (quality score) = weather-station irradiance > 0, or any inverter producing if the station is missing. Clean day = every inverter and the station ≥ 95 % of daylight intervals `ok` | Kaggle has no location for solar position | Used by the score, calibration window and σ band |
| D19 | Real-data mode fits k_i against AC power directly, on *healthy* intervals only (producing and within ±15 % of the fleet median, POA ≥ 200 W/m², unclipped) | Kaggle Plant 2 has real midday drop-outs (DC = 0, DAILY_YIELD flat) on most inverters; fitting on them hid the faults (σ_rel 0.45) | σ_rel 0.086, holdout median daily APE 7.6 % |
| D20 | Generator applies texture, soiling and the silent derate on DC before the inverter; inverter spread calibrated as a robust (MAD) std of k_i / median k | Clipping must hide some DC losses as on a real plant; real underperformers must not inflate the spread | Calibrated values written to the scenario YAML: σ_noise 0.0856, spread 0.028 |
| D21 | PVGIS TMY hh:00 UTC stamps are the hour **midpoint** (DNI·cos z + DHI = GHI holds at the stamp); Feb 29 repeats Feb 28 when re-stamping to 2024 | Measured closure on the downloaded TMY | Baseline chain evaluates the sun at the stamp |
| D22 | Peer-deviation rule uses the daily peer ratio normalised by the inverter's own reference (median of its first 14 eligible days); runs ≤ 3 days apart are merged. The raw `peer_ratio` stays the metric | With the calibrated 2.8 % spread a permanently weaker inverter re-tripped 0.95 every week (31 false events) | THAR1: only INV-17 flagged, from 2024-09-01 |
| D23 | Work-order priority is evaluated at record end (restored, or end of data); loss rate = E_potential rate − actual rate at the event's first daylight interval | No live clock in batch mode (replay is stretch S1) | Shown with weights in `priority_inputs` |
| D24 | Baseline uses the **PVGIS-ERA5** TMY (2005–2023) — SARAH3 does not cover 71.9°E. P50 = 117.75 GWh, outside the docs' 95–115 GWh range; range widened to 95–125 GWh (decided with the team lead, 18 Oct) | ERA5 2010/2015 GHI ≈ 2,080 kWh/m², TMY 2,122; 2024 actual 1,882 → 2024 is a genuinely weak year, not a convention error | Declared CUF 26.9 %; 2024 accountable 105.55 GWh ≈ 10 % below P50 |
| D25 | `work_order.event_id` is `ON DELETE CASCADE`; `audit_event` created in migration 0002 | Detection re-runs replace events idempotently | docs/04 DDL updated |
| D26 | Pipeline gains a `quality` step (measurements → actual_output) before `expected`; `--steps all` runs implemented steps and lists the pending ones on stderr | actual_output must exist before σ band, detection and accounting | `make pipeline` succeeds while M4 is pending |
| D27 | Kaggle duplicate timestamps: first row kept, the rest counted in the quality report (the measurement PK cannot hold duplicates) | docs/02 §2.3 "suspect on others" is not storable | Plant 2 has 0 duplicates |

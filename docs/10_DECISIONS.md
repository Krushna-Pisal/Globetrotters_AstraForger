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

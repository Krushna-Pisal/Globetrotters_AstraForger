# 01 — Product Spec

## 1. Problem
An engineer, an operations manager and a CFO look at the same plant and need different truths. Most tools give one
dashboard, or three dashboards whose numbers drift apart. PS4 asks for one underlying model of design, expected and
actual performance, three distinct views from that single source, and explicit statements of what each role sees and
what is deliberately left out. Judges reward a correct domain model over polish.

Pitch line: **"One asset. One evidence chain. Three decision-ready truths. And nobody can quietly move the target."**

## 2. Users and their one decision
| Lens | Decision | Cadence | Compares against | Spec |
|---|---|---|---|---|
| Engineer | Is the plant physically healthy; which component underperforms? | weekly | E_potential (weather-adjusted) | `configs/lenses/engineer.yaml` |
| Operations manager | What do I fix first; is the contractor meeting its SLA? | daily / live | E_potential + O&M guarantee | `configs/lenses/operations.yaml` |
| CFO / investor | Is the investment case holding; is debt safe? | monthly | Frozen baseline (P50/P90), covenants | `configs/lenses/cfo.yaml` |

"Left out" is not "unreachable": omissions set the default view; authorised lineage drill-down still exists and is redacted per lens.
Omitted items come back by **rule** (materiality, recurrence, covenant watch), never by opinion.

## 3. Features (MVP unless marked)
Each feature lists the rubric line it earns and its acceptance test (docs/08).

| # | Feature | Rubric | Acceptance |
|---|---|---|---|
| F1 | Canonical model + pipeline for two datasets (real slice, synthetic year) | Tech, Domain | `make pipeline` for both datasets; T-DATA-* pass |
| F2 | Expected output (pvlib) with uncertainty band; PR, PR_25, A_E | Domain | physical sanity tests; holdout error reported |
| F3 | Frozen, versioned baseline from TMY (P50/P90) | Domain, Tech | T-BASE-01/02 |
| F4 | PPA settlement (5 clause lines) and separate O&M LDs | Domain | T-SET-*, settlement firewall |
| F5 | Energy bridge (variance vs assumed losses) + revenue bridge + Q4 verdict, both closing, residual visible | Domain, Concept | T-REC-01/02/05 |
| F6 | **Liability map: who bears every lost kWh** (owner / O&M / offtaker / warranty / unexplained) | Concept, Domain | T-LIA-01 |
| F7 | Metric registry with lineage hashes | Tech | T-REC-03 |
| F8 | Server-enforced lenses + omissions panel + stripped-field receipt | Concept, Tech | T-SEC-* |
| F9 | Materiality, recurrence and covenant escalation into the CFO view | Concept | T-ESC-01/02 |
| F10 | **Rosetta card: one event, three truths side by side, byte-identical to each lens** | Concept, Presentation | T-ROS-01 |
| F11 | **Truth-divergence note** when lenses disagree on a month, explained by bridge steps | Concept | T-DIV-01 |
| F12 | Detection (status, zero-in-daylight, peer, expected-shortfall) with work orders, SLA clock, priority | Domain, Core | T-DET-* |
| F13 | **Engine scorecard vs ground truth** (precision/recall, lost-kWh error, bucket error) | Tech, Presentation | T-SCO-01 |
| F14 | Lineage drawer on every number; reconciliation badges from real test runs | Tech, UX | T-REC-* shown live |
| F15 | Provenance + mode badges everywhere (measured / modeled / synthetic / derived; provisional) | Domain, UX | visual check + T-DATA-03 |
| F16 | **Action with a price tag** per lens (e.g. "missed cleaning cost X MWh; claim candidate ₹Y") | Concept | T-ACT-01 (stretch-light) |
| S1 | Replay / live mode over WebSocket (virtual clock) | Tech | stretch |
| S2 | Modbus SCADA simulator + read-only connector | Tech | stretch |
| S3 | Contract dispute mode (interpretation A vs B) | Domain | stretch |
| S4 | Local-LLM role narrative (Ollama; numbers only from payload) | Presentation | stretch |
| S5 | Battery template, schema-only (twin genericity) | Tech | stretch |

## 4. Screens (archetype-matched; shared tokens and metric names)
| View | Top | Middle | Bottom |
|---|---|---|---|
| **CFO** — "Is the investment case holding?" | Tiles: settled revenue vs P50, energy vs P50/P90, DSCR_YTD vs lock-up, recovered + claimable ₹ | Revenue bridge waterfall (controllable vs not colours, residual hatched, Q4 verdict sentence); energy vs P50/P90 line | Escalations; liability map; divergence note; Out-of-scope panel |
| **Operations** — "What do I fix first?" | A_E vs 99.0 % guarantee; "lost right now" MWh/h | Work queue ranked by priority with visible weights and SLA clocks; transition buttons | Soiling ratio + next/missed cleaning; curtailment log; Out-of-scope panel |
| **Engineer** — "What is physically wrong?" | PR_25 trend with expected band | Inverter × day heatmap (peer ratio); kWh loss waterfall with precedence; residual detail | 15-min traces with quality flags; events with evidence; Out-of-scope panel |
| **Rosetta** (presenter) | Event header | Three panels (each = that lens's payload, hash shown) | Reconciliation sentence: same kWh at three grains |
| **Scorecard** (presenter/engineer) | Detection precision/recall | Per-event true vs found lost kWh; per-bucket true vs attributed | Real-slice results (no ground truth): flagged inverters, residual |

Every page footer: plant, dataset + mode badge, period, baseline version (CFO), data-quality score, "provisional until year close" where applicable.

## 5. UX rules
- Units per lens: Engineer kWh; Ops MWh and MWh/h; CFO GWh and ₹ lakh/crore.
- Colour carries meaning only: controllable vs uncontrollable vs residual (hatched) vs recovered.
- Every number has a provenance badge and opens the lineage drawer.
- The role switcher swaps demo tokens and keeps plant, period and selected event in the URL.
- A small "stripped by server: N items" receipt sits next to the Out-of-scope panel (names = the omission list).

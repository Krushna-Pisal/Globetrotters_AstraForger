# 09 — Demo Script (5 minutes; 2-minute cut at the end)

Dataset: `thar1_demo_2024` (SYNTHETIC SCENARIO badge visible throughout). Replace every number below with what the engines
produce; never read illustrative numbers from this file aloud.

## Setup line (15 s)
"Same plant, same data, three people who need different truths. One model, one metric registry, three lenses the
server enforces — and the investment target is frozen, so nobody can quietly move it."

## Beat 1 — Engineer, April 2024 (60 s)
1. Log in as `engineer`. Point at the mode badge and data-quality score.
2. PR_25 trend: April dips below the expected band.
3. Heatmap: INV-07 is a dead column 9–12 April. Click → evidence: status `FAULT_OVERTEMP`, 72 h, ≈ N MWh lost, precedence rule "outage".
4. Loss waterfall in kWh: availability, soiling (May spike = missed cleaning), residual visible.
5. Open the Out-of-scope panel: "Money amounts and tariff — root-cause work stays physics-first."

## Beat 2 — Operations, same event (45 s)
1. Role switcher → `operations` (token swap; URL keeps plant, period, event).
2. The event is a critical work order: restored at 72 h vs 96 h SLA; priority weights shown.
3. A_E for April vs 99.0 % guarantee → met. "So there is no LD: the owner, not the contractor, bears this loss."

## Beat 3 — CFO, same event (45 s)
1. Switch → `cfo`. The event is **absent**. Open Out-of-scope: "A 3-day outage is noise at portfolio level; it reappears if it recurs or crosses materiality."
2. Stripped receipt: "server removed 5 items" (the CFO lens omits 5) — the browser never received them.
3. Tiles: settled revenue vs P50, DSCR_YTD vs lock-up (provisional).

## Beat 4 — The twist: recurrence (45 s)
1. Move the period to **July 2024**. Escalation appears: IGBT_OVERTEMP in Apr, Jun, Jul → "Structural issue", bearer warranty candidate, recommended action.
2. Liability map: availability losses split owner / O&M LD / warranty candidate; curtailment (October) shows what the offtaker paid back and what the owner absorbed.
3. Divergence note (October): "Ops ✓ availability met; CFO ✗ revenue below P50 — curtailment and weather."

## Beat 5 — Proof (60 s)
1. Log in as `presenter` → Rosetta card for E01: three panels, three payload hashes equal to each lens's own response; one reconciliation sentence (kWh → MWh → ₹).
2. Click any CFO number → lineage drawer down to the delivery-meter rows; engineer-only nodes show as redacted with reason.
3. Reconciliation badges (real test runs): energy closes, money closes, same number everywhere, settlement firewall, nothing silent.
4. Scorecard: "We injected 6 IGBT trips, a silent string-fuse derate and a missed cleaning. The engines found all of them; lost-energy error under 5 %." Then the real Kaggle slice: suspected underperformers and an honest residual.

## Close (15 s)
"Deterministic by design — because money decisions need explainable numbers. One asset, one evidence chain, three truths."

## 2-minute cut
Beat 1 steps 1–3 → Beat 2 step 3 → Beat 3 step 1 → Beat 4 step 1 → Beat 5 steps 1 and 3.

## Fallbacks
- Recorded video of the full run, plus screenshots in the deck.
- Everything runs offline after `make demo` (weather is cached).

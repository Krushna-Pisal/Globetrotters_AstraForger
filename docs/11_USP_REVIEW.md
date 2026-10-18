# 11 — USP Review (for the team and the deck)

## 1. Verdict on the 17 USPs in plan v2.0
Most Tier-1 items (registry, frozen baseline, settlement firewall, closing waterfall) are things the organisers' guide
*requires*. They are not differentiators by themselves; what differentiates is that we **prove** them live. Several Tier-3
items work against our own pitch ("deterministic by design").

| # | v2.0 USP | Verdict | Action |
|---|---|---|---|
| 1 | One registry, three server-enforced lenses | Core, but every strong team will claim it | Keep; make it visible (stripped receipt, payload hashes) |
| 2 | Immutable versioned baseline | Required by the guide | Keep as proof, not as a headline |
| 3 | Settlement firewall | Required | Keep as a green badge + import-linter |
| 4 | Named-cause waterfall + residual | Required; ours is stronger because it is variance vs **assumed** losses | Keep, say "variance vs the investment case's own assumptions" |
| 5 | Omissions by rule | Strong — this is the PS's explicit ask | Keep in Tier 1 |
| 6 | Click-to-trace lineage | Good | Merge with 7 into "click-to-proof" |
| 7 | Visible reconciliation proof | Good | Merged |
| 8 | Provenance labels | Hygiene | Tier 2 |
| 9 | Validated against synthetic ground truth | **Underrated** — nobody else can show precision/recall | Promote to Tier 1 as the Engine Scorecard |
| 10 | Generic twin (battery template) | Weak on stage | Tier 3 |
| 11 | Closed-loop operations | Useful, standard | Tier 2 (status + SLA clock only in MVP) |
| 12 | Controllable / external / recoverable split | Good, but abstract | Upgrade into the Liability Map (who pays) |
| 13 | Automatic Q4 verdict | Small, nice | Tier 2 |
| 14 | What-if recovery simulator | Stretch | Tier 3 |
| 15 | Local AI copilot | Generic; every team has an LLM | Tier 3, narrative only |
| 16 | Isolation Forest anomalies | Contradicts deterministic pitch | **Cut** |
| 17 | Portfolio recurring deviations | Out of scope for one plant | **Cut** |

## 2. New USPs that make us stand out
| New | What it is | Why it wins |
|---|---|---|
| **Rosetta card** | One event, three truths side by side; each panel is byte-identical (hash shown) to what that role receives | The PS title made literal; the single best 20 seconds of the demo |
| **Truth-divergence note** | When lenses disagree on a month (Ops ✓, CFO ✗) the platform says why, using bridge steps | Explains *why* three truths differ instead of just showing three screens |
| **Liability map — who bears every lost kWh** | Each loss allocated to owner / O&M contractor (LDs) / offtaker (deemed compensation) / warranty candidate / unexplained, recovered vs claimable | Requires two contracts modelled correctly; turns Q5 into money and accountability. Few teams will model the O&M contract at all |
| **Engine scorecard** | Detection precision/recall and lost-kWh error against injected ground truth, plus honest results on real Kaggle data | "We grade our own engine" — turns synthetic data from a weakness into evidence |
| **Stripped-field receipt** | Each response says how many items the server removed for this role; names come from the omissions list | Proves server-side enforcement in five seconds |
| **Variance vs the case's own assumptions** | Buckets measure actual minus what the P50 already assumed | A domain-correctness point judges will recognise; most waterfalls double-count |
| **Action with a price tag** | Each lens ends with one action and its value ("missed cleaning on 4 May cost X MWh; ₹Y claim candidate under O&M scope") | Moves from reporting to decisions |
| **Uncertainty-aware alarms** | Expected output carries a ±band; alarms fire only outside it | Fewer false alarms; technical depth |

## 3. Final ranked list
**Tier 1 — must be in the demo:** Rosetta card · Liability map · Server-enforced lenses with omission reasons and stripped receipt ·
Bridges that close against assumed losses with a visible residual + click-to-proof badges · Engine scorecard.
**Tier 2 — show if time:** Truth-divergence note · Escalation by materiality/recurrence · Action with a price tag · Uncertainty-aware
alarms · Provenance + mode badges · Q4 verdict · Work orders with SLA clock.
**Tier 3 — stretch:** Replay/live mode · Contract dispute mode · Local-LLM narrative · Modbus SCADA simulator · Battery template.
**Cut:** Isolation Forest, portfolio detection.

## 4. Pitch lines
- "One asset. One evidence chain. Three decision-ready truths. And nobody can quietly move the target."
- "Every lost kWh has an owner — the owner, the O&M contractor, the offtaker, a warranty claim, or an honest 'unexplained'."
- "We injected the faults ourselves, then let the engine find them. Here is its score."

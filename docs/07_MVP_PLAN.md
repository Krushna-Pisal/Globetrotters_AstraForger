# 07 — MVP Implementation Plan

Written Sat 17 Oct 2026, 23:00 IST. Submission date (18 Oct), finalist date (21 Oct) and final (31 Oct) are **unverified —
check the portal first**; the plan has two cut lines for that reason.

## 0. Principles
- Build engines and their closure tests before screens (Domain + Technical + Concept = 50 % of the score).
- Vertical slices: each milestone ends demoable; take screenshots for the deck after each.
- Frontend starts in hour 1 against `data/fixtures/*.json` shaped exactly like docs/05, then switches to the live API.
- One Claude Code session per milestone, using the master prompt (§4). Humans review every formula, unit and timezone.

## 1. Tracks (map to the Quest team formation)
| Track | Person | Owns |
|---|---|---|
| A — Data & physics | Eng 1 | M1, M2: ingest, quality, pvlib, scenario generator, detection |
| B — Engines & API | Eng 2 | M0, M3, M4, M5: schema, baseline, contracts, settlement, O&M, finance, attribution, registry, lenses, tests |
| C — Design & frontend | Design/Data-viz | M6: fixtures, components, three pages, Rosetta, scorecard |
| D — Product & story | Product/Business | omission reasons, materiality rules, assumptions page, deck, demo script (docs/09), submission; reviews numbers |

## 2. Milestones

### M0 — Bootstrap (B, 1 h)
Repo per CLAUDE.md layout; Docker Compose (postgres:16, api, web); FastAPI `/health`; Vite React TS app; Alembic init with
the docs/04 enums and `dataset`, `source_batch`, `asset_template`, `asset`; Makefile targets (stubs allowed); ruff, pytest,
import-linter config with the four contracts (docs/03 §2); CI workflow; `.env.example`; demo JWT login (`/v1/auth/demo-login`).
**Done when:** `make up && make migrate && make test && make lint` pass on a fresh clone.

### M1 — Real slice: ingest + quality (A, 2–3 h) — *finals build if time is short*
Kaggle Plant 2 adapter (explicit formats, unit detection), manifests with sha256, `measurement` upsert, quality flags and
score, real-data-mode expected model (per-inverter k fit on 7 days, holdout MAPE), calibration of noise/spread → scenario YAML.
**Done when:** T-DATA-01/02/04 pass; quality report JSON in `data/processed/kaggle_p2_2020/`; calibrated σ values committed.

### M2 — Twin, expected output, synthetic year (A, 3–4 h)
Twin from `configs/plant/thar1.yaml`; weather adapters (Open-Meteo primary, NASA POWER fallback) with cache; 15-min
downscaling; pvlib chain (docs/02 §3.1) → `expected_output` with band; scenario generator (docs/06 §5) → measurements,
operator log, `ground_truth.json`; status-code detection rule (rule 1) → events.
**Done when:** T-PHYS-01/02/03, T-DATA-03, T-REPRO-01 (generator part) pass; expected vs actual chart for INV-07 in April shows the outage.

### M3 — Baseline, contracts, accounting, settlement, O&M, finance (B, 4 h)
`make baseline` (PVGIS TMY → P50/P90 monthly, finance case) + `make approve-baseline` with immutability trigger;
contract loaders (separate functions); accounting ledger + meter reconciliation; PPA settlement (5 clause lines,
monthly provisional + annual true-up); A_E, LDs, SLA from operator log; CFADS + DSCR_YTD.
**Done when:** T-BASE-01/02, T-SET-01..05, T-OM-01 pass; annual P50 within the sanity range; declared CUF written back to `ppa_v1.yaml` (one-time, committed).

### M4 — Attribution, registry, reconciliation (B with A, 4 h)
Soiling ratio estimate; interval loss assignment with precedence; energy bridge; revenue bridge + Q4 verdict; liability map;
metric registry loader + `metric_value` writer with lineage hashes; reconciliation runner → `recon_result`.
**Done when:** T-REC-01..05, T-LIA-01 pass for every month of 2024.

### M5 — Lens API (B, 3 h)
Lens spec loader; projection (select, re-grain, unit-convert); payload guard; omissions + stripped receipt; materiality,
recurrence, covenant escalation; divergence note; `/view`, `/lineage`, `/reconciliation`, `/baseline/*`, `/workorders`.
**Done when:** T-SEC-01..04, T-ESC-01/02, T-DIV-01 pass.

### M6 — Screens (C, starts hour 1 on fixtures; 6–8 h total)
Components (MetricCard, Waterfall, OmissionsPanel, LineageDrawer, RoleSwitcher, ModeBadge, DebugStrip); CFO, Operations,
Engineer pages per docs/01 §4; switch from fixtures to API once M5 lands.
**Done when:** the same INV-07 event is consistent across the three pages; Out-of-scope panel on every page; no metric arithmetic in React (code review).

### M7 — Story features + hardening (A+B+C, 4–5 h)
Rosetta endpoint + page; scorecard (detection rules 2–4, precision/recall, lost-kWh error); work-order transitions + SLA clocks;
"action with a price tag" cards; `make demo` seeds everything from scratch; README; screenshots; 2–3 min recording.
**Done when:** T-ROS-01, T-DET-01..03, T-SCO-01, T-ACT-01 pass; docs/09 demo runs end to end twice in a row from `make demo`.

### Stretch (only after M7, in this order)
S1 replay/WebSocket live mode → S3 contract dispute mode → S4 local narrative → S2 Modbus SCADA simulator → S5 battery template.

## 3. Schedule and cut lines
| Window | Target |
|---|---|
| Sat 23:00 – Sun 02:00 | Verify portal requirements and dates; M0; fixtures; download + fetch data (docs/06 §6) |
| Sun 02:00 – 10:00 | M2 (A) ∥ M3 (B) ∥ M6 on fixtures (C) ∥ deck skeleton + assumptions (D) |
| Sun 10:00 – 16:00 | M4 → M5; C wires CFO + Engineer pages to the API |
| Sun 16:00 – submission | Operations page, screenshots, deck, recording, submit with buffer |
| 21–30 Oct (if shortlisted) | M1 real slice, M7 story features, polish, stretch |

**Round-1 cut (if a working prototype is due on 18 Oct):** M0, M2, M3, M4 (T-REC-01/02/04/05), M5 (T-SEC-01), M6 (CFO + Engineer + basic Ops).
Skip M1, Rosetta, scorecard, work-order transitions; say they are in progress.
**If round 1 is a deck/proposal only:** submit the deck with architecture, lens table, bridge screenshots from M2–M4, and
build the full MVP for the finals.

## 4. Claude Code master prompt (paste at the start of every session)
> You are the implementation engineer for the PS4 Performance Assurance Platform. Read `CLAUDE.md`, then the docs cited by
> the milestone I name. Source-of-truth order is in CLAUDE.md; if sources conflict, stop and ask. Implement ONLY milestone
> <Mx>. Before editing, list existing files you will touch and new files you will create. Write the tests listed for the
> milestone first, then the code. Keep every invariant in CLAUDE.md (frozen baseline, settlement firewall, two contracts,
> nothing silent, variance vs assumed losses, no computing in React, server-enforced lenses, provenance, no fabricated
> measured data, local-only AI, Ops vs expected, monitoring only). Do not invent dataset columns; if a file is missing, stop
> and say what you need. Finish with: changed files, commands run, test results, limitations, next prerequisites.

## 5. Per-milestone prompts (append to the master prompt)
- **M0:** "Implement M0 from docs/07 §2. Use docs/03 §2 for import-linter contracts and docs/05 §1 for demo login."
- **M1:** "Implement M1. Follow docs/06 §4 and docs/02 §2–§3.1 (real-data mode). Files are in `data/raw/kaggle/`. Report Plant 2 gaps, units and AC/DC ratio before writing the adapter."
- **M2:** "Implement M2. Follow docs/06 §5, docs/02 §3, configs/plant/thar1.yaml and configs/scenarios/thar1_demo_2024.yaml. Engines must not import app.scenarios."
- **M3:** "Implement M3. Follow docs/02 §3.3, §4.3–§4.4, §5, §6, §9 and docs/04 §5–§6. Reproduce the worked examples in docs/02 §6.4 and §4.4 as unit tests first."
- **M4:** "Implement M4. Follow docs/02 §7 exactly (precedence, closure proof, liability allocation) and configs/metrics/metrics.yaml."
- **M5:** "Implement M5. Follow docs/05 and configs/lenses/*.yaml; payload guard per docs/03 §4; escalation and divergence per docs/02 §10."
- **M6:** "Implement M6 against `data/fixtures` first, then the API. Follow docs/01 §4–§5. No arithmetic on metric values in React."
- **M7:** "Implement M7: Rosetta (docs/05 §3), scorecard (docs/02 §8.1, docs/08 T-SCO-01), work-order transitions, actions, `make demo`."

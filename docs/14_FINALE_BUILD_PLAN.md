# 14 — Grand Finale Build Plan (31 Oct 2026, 08:00–18:00)

Planning material (allowed before the event). **All application code is written on 31 Oct in a fresh repo.** The earlier
prototype is not reused (team decision, 27 Oct). This plan reuses only *ideas* from docs/01–11 and the parameters in
`configs/` as reference. If in doubt whether a planning file counts as "code", ask the organizers on the day.

Briefing constraints that shape this plan:
- 10 hours of hacking, no meal breaks; presentations ~19:00 (10 min + 5 min Q&A).
- Any AI model must run **locally**; teams must be able to explain all AI-generated code.
- Judges provide an **endpoint with test data** at presentation time → ingestion must be flexible.
- **Surprise challenges** (new dataset, changed problem, model adjustment) and ongoing evaluation during the day.
- Demo must be reachable from another laptop (ngrok or similar).
- UI/UX carries marks.

---

## 1. Scope for the day (a thin but complete thread)

Organizer priority (docs/15): PS4 covers **all 11 layers and all six questions**, and asks us to be explicit about what
each role sees **and what is deliberately left out**. So every layer gets a simple, honest implementation; depth comes
second. The plant type and model come from the dataset we are given (adapter interface + real-data fallback).

The story: **one plant, one fault told three ways, plus a recurrence that escalates to the CFO** — told on whatever
plant type the data describes.

| Priority | Feature | Layers / questions | Why |
|---|---|---|---|
| **Must A (by 13:00)** | Login with 4 demo roles; role from the signed token only | — | Server-side enforcement is visible |
| Must A | Ingest: CSV upload **and** fetch-from-endpoint, with a column-mapping step and validation report | 5, 6 | Judges' test endpoint; surprise datasets |
| Must A | Plant config + twin with a **plant-type adapter interface** (expected output, loss categories, contract terms) | 1, 2 | Type decided by the dataset |
| Must A | Expected output from the adapter (physics when metadata exists, data-driven real-data mode otherwise), stored with band + model version | 3, 4 | Fair expected-vs-actual comparison |
| Must A | Quality flags + validated actual; detection (status faults, zero-output-while-resource, peer deviation, shortfall vs band) → events with evidence | 5, 6 | Engineering truth |
| Must A | Three lens endpoints with server allowlist + payload guard, and a **"Left out of this view (N)" drawer** on every page with reasons, comeback rule and stripped receipt | PS4 sentence | The explicit ask (Gap 1) |
| Must A | Engineer, Operations, CFO pages (tiles + 1–2 charts + events / work queue / escalations) | Q1, Q2 | Demo backbone |
| **Must B (by 15:30)** | Frozen, versioned baseline (P50/P90, **case PR**, **case tariff path**, case DSCR); DB-immutable after approval | 3A | Q1 and layer 10 need a fixed target |
| Must B | Output accounting: boundary meter → **one boundary/loss-allocation rule** → accountable; reconciliation vs grid-operator statement (or inverter sum) shown | 7, Q3 | Gap 4 |
| Must B | Settlement from accountable output + contract only: energy charge with **tariff escalation/indexation**, one deemed-generation clause (curtailment/grid); availability-based payment instead if the asset is storage/thermal | 8, Q3 | Gap 3; the one rule |
| Must B | Roll-up in the baseline's shape + **plan-vs-actual table** (generation, PR/KPI, revenue, DSCR: baseline, actual, variance, named causes) | 9, 10, Q1, Q4 | Gap 5; mirrors the guide's worked example |
| Must B | Simplified **closing bridge** with explicit residual (weather/resource → outage → grid → curtailment → underperformance → residual) and a revenue split volume vs tariff vs contract | 11, Q2, Q4 | Gap 6; "never a silent leftover" |
| Must B | Three server-computed trust badges: energy closes, money closes, settlement independent of baseline | Q3 | Proof on screen |
| **Should (by 16:30)** | O&M energy availability vs guarantee, LDs (separate module/table), SLA clock, ranked work queue | 8, Q5 | Ops truth; two contracts, two cash flows |
| Should | Escalation by materiality / recurrence / covenant watch | Q6 | The story's twist |
| Should | Presenter overview: month × lens verdict matrix + "who sees what" matrix | PS4 | Three truths side by side |
| Should | Controllable / recoverable split (simple liability view: owner, O&M contractor, offtaker, unexplained) | Q5 | Accountability |
| **Could** | Local-model narrative (Ollama) that only rephrases payload numbers | — | Only if ready and local |
| Could | Rosetta card, lineage drill-down, work-order transitions | — | Polish |
| **Won't** | Synthetic full-year generator, engine scorecard, replay/live mode, multi-plant portfolio | — | Roadmap slide only |

Rule of thumb: if Must A slips past 13:00, cut Should items, never Must B — Must B is what makes it "the whole thread".

## 2. Team tracks (adapt names)

| Track | Owner | Owns |
|---|---|---|
| A — Data & physics | Eng 1 | ingest (file + endpoint + mapping), plant-type adapter, quality flags, expected output, detection, closing bridge |
| B — API & rules | Eng 2 | schema, auth, lens specs + guard + left-out list, baseline, accounting rule, settlement + escalation, roll-up, plan-vs-actual, trust badges, O&M/SLA, escalation |
| C — UI/UX | Design/front-end | design brief, tokens, component kit, left-out drawer, three pages, plan-vs-actual table, presenter view, screenshot review |
| D — Product & story | Product | business numbers (docs/12), judge Q&A prep, PPT on the day, test-endpoint dry run |

Each engineer runs **their own Claude Code session** on their own folder/branch to avoid edit collisions; merge at
checkpoints.

## 3. Hour-by-hour

| Time | A — Data | B — API | C — UI | D — Product | Checkpoint |
|---|---|---|---|---|---|
| 07:30 | Report, verify IDs, set up laptops, ngrok account logged in | | | | |
| 08:00–08:30 | All: read any new instructions, inspect provided data/endpoint format, create repo, `docker compose` skeleton (db + api + web), CLAUDE.md with invariants + design brief | | | | Repo runs `/health` |
| 08:30–10:30 | CSV + endpoint ingest with column mapping; units/timezone detection; quality flags; plant-type adapter skeleton | Schema, demo auth, lens YAML + allowlist guard + left-out list, `/view` stub returning fixtures | Tokens, fonts, shell, login, component kit, **left-out drawer**; pages on fixture JSON | Map the provided data to the 11 layers / 6 questions; finalise business numbers | 10:30 — ingest loads the provided data; UI shell live |
| 10:30–13:00 | Expected output via the adapter + band; detection rules → events | Lens projections from real tables; frozen baseline (P50/P90, case PR, case tariff path) | Engineer + Ops + CFO pages wired to API | Draft PPT outline (on the day only) | **13:00 — Must A demoable end to end** |
| 13:00–13:20 | Quick team demo; cut list decided | | | | Freeze Must A |
| 13:20–15:30 | Closing bridge with residual (energy) + revenue split; feed attribution causes to the table | Accounting rule + reconciliation; settlement with escalation + deemed generation; roll-up; plan-vs-actual API; trust badges | Plan-vs-actual table; bridge chart; trust badges | PPT build; rehearse the thread story | **15:30 — Must B (whole thread) done** |
| 15:30–16:30 | Robustness on a second dataset / plant type | O&M availability, LDs, SLA, work queue; escalation rules | Presenter matrices (verdicts, who-sees-what); empty/loading/error states | Judge Q&A prep per layer | 16:30 — Shoulds done or cut |
| 16:30–17:15 | Stress test: messy CSV, missing intervals, different timezone | Tests: lens guard (no forbidden id in JSON), baseline immutability, settlement ignores baseline, bridge closes | Polish pass at 1280×720 projector size; screenshot review | Dry run against a mock endpoint | |
| 17:15–17:45 | ngrok link tested from another laptop; seed demo data; README run steps | | | Share PPT with organizers | |
| 17:45–18:00 | **Code freeze**; tag the commit; everyone can explain their part | | | | Freeze |

## 4. Preparation allowed before the day (no code)
- Read and agree docs/15 (alignment review) first, then docs/01, 02 (formulas), 05 (payload shapes), 09 (story),
  12 (numbers), 13 (UI resources), this file.
- Agree on paper: the plant-type adapter interface, the contract config fields (tariff + escalation/indexation,
  deemed-generation clause, availability payment), the accounting boundary rule, and the plan-vs-actual table rows.
- Install tools: Docker Desktop, Node 22, Python 3.12, Git, GNU make, ngrok (+ account); Claude Code plugins/MCPs from
  docs/13 §2; pre-pull Docker images (`postgres:16`, `python:3.12-slim`, `node:22-alpine`) so setup isn't on venue Wi-Fi.
- Collect public reference datasets and weather caches you may need (Kaggle solar data, Open-Meteo/PVGIS for a site),
  with licences noted — data is not code, but confirm on the day if unsure.
- Write the prompts you will give Claude Code per track (plain text, no code).
- Design references: 5–10 screenshots per lens (docs/13 §4).
- Model training/fine-tuning (allowed from 26 Oct) happens in a separate chat; it must run locally (e.g. Ollama) and
  must never compute a metric — only phrase what the API returns.

## 5. Readiness for surprises
- **New dataset**: the column-mapping ingest + real-data mode expected model is the answer; keep the pipeline
  dataset-driven, never hard-code plant ids in engines.
- **Judges' endpoint**: fetch → map → run pipeline → open the lens views. Rehearse with a mock endpoint (JSON and CSV).
- **Changed problem**: the lens layer is config (YAML allowlists + omissions), so a new role or a changed rule is a
  config edit plus a page.
- **Model adjustment**: keep model parameters in config with a version; re-run writes new rows, old ones stay.
- **Questions during the day**: each owner keeps a 3-line explanation of their module ready.

## 6. Risks and mitigations
| Risk | Mitigation |
|---|---|
| Endpoint format unknown | Generic mapping step; accept CSV and JSON; show a clear validation report |
| Time overrun | 13:00 freeze of Musts; cut list agreed in advance (§1 Could/Won't) |
| Venue network slow | Pre-pulled images; cached weather; everything offline after ingest |
| ngrok/proxy issues | Test the tunnel at 12:00 and 17:15; same-origin proxy for the API |
| Merge conflicts between sessions | One owner per folder; merge at 10:30 / 13:00 / 16:00 |
| "Explain the code" questions | Owners review AI-generated code as it lands; keep invariants list in CLAUDE.md |
| Local model too slow | Narrative is a Could; the product works without it |

## 7. Definition of done for 18:00
- Fresh clone runs with one command; demo data seeded; ngrok link works from another laptop.
- Login → each role sees only its lens (server-enforced), and every page shows what was left out and why.
- All 11 layers have a working, simple implementation; each of the six questions can be answered on screen
  (checklist in docs/15 §1–§2).
- The plan-vs-actual table shows baseline, actual, variance and several named causes; the bridge closes with an explicit
  residual; the revenue split separates volume from tariff/indexation and contract effects.
- Settlement is computed from accountable output and the contract only, and a badge proves it ignores the baseline.
- One event is visible three ways; a recurrence escalates to the CFO.
- The judges' endpoint data can be loaded through the UI or one command.
- Every team member can explain their module.

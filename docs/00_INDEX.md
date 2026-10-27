# 00 — Doc Pack Index (v2.1, 17 Oct 2026)

Supersedes "PS4 Final Plan v2.0". The v2.0 review corrections are recorded in `10_DECISIONS.md` (C01–C12).

| File | For | Read when |
|---|---|---|
| `../CLAUDE.md` | Claude Code (auto-loaded) | Every session |
| `01_PRODUCT_SPEC.md` | Everyone | What we build, for whom, features F1–F16, screens |
| `02_DOMAIN_REFERENCE.md` | Engines (authoritative) | Any formula, contract or attribution work |
| `03_ARCHITECTURE.md` | Engineers | Module boundaries, pipeline, API layer, frontend structure |
| `04_DATA_MODEL.md` | Engineers | Schema and DB-enforced rules |
| `05_API_CONTRACT.md` | Backend + frontend | Payload shapes; frontend fixtures |
| `06_DATA_STRATEGY.md` | Track A + deck | Dataset choice, synthesis basis and algorithm, data checklist |
| `07_MVP_PLAN.md` | Everyone | Milestones, owners, schedule, cut lines, Claude Code prompts |
| `08_TEST_PLAN.md` | Engineers | Test ids referenced by milestones |
| `09_DEMO_SCRIPT.md` | Product + presenter | The 5-minute and 2-minute demo |
| `10_DECISIONS.md` | Everyone | Locked decisions and corrections |
| `11_USP_REVIEW.md` | Product + deck | USP verdicts, new USPs, ranking, pitch lines |
| `12_MARKET_RESEARCH.md` | Product + business | Sourced India/global market numbers, competitors, business model |
| `13_UI_RESOURCES.md` | UI/UX track | Free Claude Code plugins/MCPs, libraries, design brief and review checklist |
| `14_FINALE_BUILD_PLAN.md` | Everyone | 31 Oct thin-but-complete-thread scope and hour-by-hour plan under the finale rules |
| `15_PS_ALIGNMENT_REVIEW.md` | Everyone (read first) | Organizer requirements vs our prototype: 11 layers, six questions, gaps and decisions |

**Grand Finale (31 Oct 2026):** application code and the PPT are written on the day only; the earlier prototype is not
reused. Before the event these docs are planning material.

Configs (`../configs/`): `plant/thar1.yaml`, `baseline/baseline_v1.yaml`, `contracts/{ppa_v1,om_v1,loan_v1}.yaml`,
`lenses/{engineer,operations,cfo}.yaml`, `metrics/metrics.yaml`, `scenarios/thar1_demo_2024.yaml`.

Everything marked illustrative, assumed or synthetic must appear on the deck's assumptions slide.
Still to verify by a human: Kaggle licence. Resolved: PVGIS database = PVGIS-ERA5 (D24); AI-assisted coding is allowed
(finale briefing), provided the team can explain the code.

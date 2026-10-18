# 08 — Test Plan

Tests are the proof shown on stage. `make recon` runs the reconciliation suite and writes `recon_result` rows that the UI
shows as badges — badges must come from real runs, never from constants.

| ID | File | Asserts |
|---|---|---|
| **Data** | | |
| T-DATA-01 | `tests/integration/test_ingest_idempotent.py` | Ingesting the same file twice leaves row counts and values unchanged |
| T-DATA-02 | `tests/unit/test_kaggle_parsing.py` | Explicit date formats per file; 15-min monotonic index; irradiance unit detection; AC/DC ratio check flags Plant 1 |
| T-DATA-03 | `tests/integration/test_provenance_separation.py` | No `synthetic_*` source_kind in a measured dataset and no `measured` in a synthetic one |
| T-DATA-04 | `tests/unit/test_quality_flags.py` | Night output, over-rating, gaps, duplicates get the right flags; raw rows untouched |
| **Physics** | | |
| T-PHYS-01 | `tests/unit/test_expected_output.py` | Night E_potential = 0; never > 2,500 kW per inverter; clipping flagged; POA > GHI at solar noon in winter for 25° tilt |
| T-PHYS-02 | same | Azimuth conversion: Open-Meteo/PVGIS 0° south ↔ pvlib 180°; a 0° pvlib azimuth (north) run yields clearly lower annual energy |
| T-PHYS-03 | same | Midpoint timestamp shift applied to hourly-mean radiation |
| **Baseline** | | |
| T-BASE-01 | `tests/integration/test_baseline_immutable.py` | UPDATE/DELETE on an approved row raises; PATCH returns 409 |
| T-BASE-02 | same | Approving v2 leaves v1 rows byte-identical and visible in history |
| **Settlement & O&M** | | |
| T-SET-01 | `tests/unit/test_settlement_clauses.py` | Each worked example in docs/02 §6.4 reproduces to the paisa |
| T-SET-02 | same | Excess and shortfall are mutually exclusive; relaxation uses deemed kWh (interpretation A) |
| T-SET-03 | `tests/reconciliation/test_settlement_ignores_baseline.py` | Mutating the baseline (new version with ×1.5 energy) leaves every settlement line identical |
| T-SET-04 | `lint: import-linter` | settlement-firewall, om-separate, lenses-read-registry-only, engines-never-read-ground-truth contracts |
| T-SET-05 | `tests/unit/test_money_rounding.py` | Decimal only; quantize per line; totals = sum of lines |
| T-OM-01 | `tests/unit/test_om_ld.py` | A_E excludes grid/curtailment/no_data; LD example docs/02 §4.4 = ₹10.80 lakh; cap applies |
| **Reconciliation (shown on stage)** | | |
| T-REC-01 | `tests/reconciliation/test_energy_bridge_closes.py` | For every month and YTD: Σ steps = accountable within 1 kWh |
| T-REC-02 | `tests/reconciliation/test_revenue_bridge_closes.py` | Σ steps = settled revenue exactly (₹0.00 residual) |
| T-REC-03 | `tests/reconciliation/test_same_metric_same_number.py` | A metric at the same grain/period returns the same value and lineage_hash in every lens that may see it |
| T-REC-04 | `tests/reconciliation/test_settlement_firewall.py` | (= T-SET-03, surfaced as a badge) |
| T-REC-05 | `tests/reconciliation/test_nothing_silent.py` | Every inverter-interval gap is assigned to exactly one bucket or residual; Σ buckets + residual = Σ gaps |
| T-LIA-01 | `tests/reconciliation/test_liability_sums.py` | For each bucket, Σ bearer allocations = gross bucket loss |
| **Security / lenses** | | |
| T-SEC-01 | `tests/security/test_lens_allowlist.py` | For each role, every key and metric id in the serialized payload is in that lens allowlist (recursive walk + string search for forbidden ids, "tariff", "₹" in engineer/ops) |
| T-SEC-02 | same | Forged role in query/body is ignored; role comes from token only |
| T-SEC-03 | same | Cross-plant request → 403 |
| T-SEC-04 | `tests/security/test_lineage_redaction.py` | Lineage nodes outside the lens are redacted with reason, no values |
| **Lens behaviour** | | |
| T-ESC-01 | `tests/integration/test_escalation.py` | E01 alone (April) is below materiality → absent from CFO payload |
| T-ESC-02 | same | IGBT_OVERTEMP escalates at the July close (Apr, Jun, Jul) with bearer `warranty_candidate` |
| T-ROS-01 | `tests/integration/test_rosetta.py` | Each Rosetta panel hash equals the hash of that role's `/view` event section |
| T-DIV-01 | `tests/integration/test_divergence.py` | At least one month yields Ops ✓ / CFO ✗; its note names that month's largest negative uncontrollable bridge step (expected: October, curtailment — if real 2024 weather masks it, record the month that does diverge in docs/09) |
| **Detection & scorecard** | | |
| T-DET-01 | `tests/scorecard/test_detection.py` | All injected outages (E01–E07) detected with confirmed status; start/end within one interval |
| T-DET-02 | same | INV-17 silent derate found as `suspected` within 5 days of 2024-09-01 |
| T-DET-03 | same | E10 comms loss produces `no_data` flags, zero event loss |
| T-SCO-01 | same | Per-event lost-kWh error ≤ 5 %; soiling bucket error ≤ 15 %; reports precision/recall to `/scorecard` |
| T-ACT-01 | `tests/integration/test_actions.py` | Missed-cleaning action quotes lost MWh and claim-candidate ₹ that match the liability map |
| **Reproducibility** | | |
| T-REPRO-01 | `tests/integration/test_reproducible.py` | Same seed + same inputs → identical metric values and lineage hashes across two full pipeline runs |

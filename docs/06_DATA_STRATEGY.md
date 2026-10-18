# 06 — Data Strategy: which datasets, and on what basis we synthesise

**Decision.** Run the platform on two datasets with the same pipeline:
1. **`kaggle_p2_2020` — real measured slice.** Kaggle "Solar Power Generation Data", **Plant 2** (Indian plant, inverter-level
   AC/DC power and yield + plant weather sensor, 15-min, ~34 days, May–June 2020). Proves the engines work on real, messy data.
   Explanations here are honest: detected symptoms are "suspected", everything else is residual. No money (no real contract).
2. **`thar1_demo_2024` — synthetic scenario year.** A fictional 60 MWp plant at an assumed Rajasthan site, built from **real 2024
   reanalysis weather + pvlib physics + injected, recorded events**. Carries the full three-lens story, contracts and money,
   and is **scored against its own ground truth**.

Never mix them: separate `dataset_id`, separate mode badge, no synthetic event overlaid on real data.

## 1. Candidate review

| Source | What it gives | Fit for PS4 | Use |
|---|---|---|---|
| **Kaggle Plant 2** | Inverter AC/DC power, daily/total yield; irradiation, module & ambient temperature; 15-min; ~34 days; Indian plant | Real inverter-level texture, real underperformers and real data gaps (reported: several inverters missing ~25 % of data over ~9 days) | **Real slice + calibration** |
| Kaggle Plant 1 | Same structure | DC_POWER ≈ 10× AC_POWER (reported AC/DC ≈ 9.8 % vs 97.8 % for Plant 2) — DC channel unusable without a fix; long weather gaps | Not used (mention as a data-quality catch in the deck) |
| NREL PVDAQ (OEDI) | Long time series for many US systems, metadata, some with irradiance/temperature; CC BY 4.0; `s3://oedi-data-lake/pvdaq/` | Excellent for multi-year degradation/soiling, but US plants: wrong currency, grid and contract context; channel set varies by system (unverified for 9068) | Optional stretch: validate the soiling/degradation estimators on a long real series |
| **Open-Meteo archive (ERA5)** | Hourly GHI, DNI, DHI, temperature, wind, precipitation; global; 1940→; radiation = mean of preceding hour | Real weather for any Indian site and year | **Primary weather for the synthetic year** |
| NASA POWER hourly | Hourly all-sky irradiance, temperature, etc.; global; 1984→ | Same role, independent source | Fallback weather; cross-check |
| **PVGIS TMY (SARAH3)** | Typical meteorological year; SARAH3 covers Europe, Africa, Asia | What a real energy-yield assessment uses for P50 | **Baseline P50/P90** |
| OPSD / plant registries | Plant lists, capacities | No telemetry | Not used |

Weather-source licences: Open-Meteo data is CC BY 4.0 with Copernicus attribution (free non-commercial API); NASA POWER and PVGIS are free with citation. Record every source in `data/manifests/*.json`.

## 2. Why this split (the basis)
- **Real where it exists:** weather is real reanalysis for the site and year; the real slice is real plant telemetry.
- **Physics where it must be calculated:** expected output comes from the same pvlib chain used for the baseline, so weather is the only difference between P50 and E_bl_aw.
- **Labelled synthesis for what no public dataset contains:** contracts, invoices, debt, work orders and confirmed causes do not exist in any public dataset for one plant. They are synthesised from documented clause patterns and a scenario file.
- **Ground truth makes synthesis a strength:** because every injected loss is recorded, the scorecard proves the engines recover it ("found 6/6 outages, 1/1 silent derate, soiling error 4 %"). That is evidence a real-data-only team cannot show.
- **Indian context is consistent:** ₹, SECI-style PPA clauses, CUF on AC capacity, IST, Rajasthan-style curtailment (≈ 4 GW of wind-solar was curtailed in Rajasthan from March 2025 amid transmission delays — Mercom, Down To Earth).

## 3. Synthesis rules (enforced by review and tests)
1. Start from physics on real weather; inject deviations on top. Never draw "actual" from a free random walk.
2. Every injected deviation comes from `configs/scenarios/*.yaml` and is written to `ground_truth.json`.
3. Engines never read the scenario file or ground truth (import-linter contract). They see only telemetry, status codes, the operator log and contracts — like a real platform.
4. Texture parameters (noise, inverter spread) are **calibrated on Kaggle Plant 2**, not invented (§4).
5. Seeded and reproducible: same seed → identical rows and identical lineage hashes.
6. Every synthetic row: `source_kind = synthetic_scenario` (telemetry, events, operator log) or `synthetic_reference/contract` (baseline, contracts); `weather_estimated` for reanalysis weather.
7. Faults are injected as **status codes and power**, the way a SCADA system would report them (e.g. INV-07 power → 0 and status `FAULT_OVERTEMP`); silent faults (INV-17) get **no** status code.
8. Weather events are not invented: rain-washing uses real 2024 precipitation; the weather bucket is whatever 2024 actually did vs the TMY.

## 4. Calibration on Kaggle Plant 2 (M1/M2)
1. Parse both files with explicit formats; build a 15-min UTC index; assert monotonic, report gaps per inverter.
2. Check irradiance units (max ≈ 1–1.3 → kW/m² → × 1000) and that AC/DC ≈ 0.97–0.98.
3. Energy: `AC_POWER × 0.25 h` vs `ΔDAILY_YIELD`; report disagreement.
4. Fit per-inverter `k_i` on the first 7 clean days (docs/02 §3.1 real-data mode); evaluate on the rest → holdout MAPE.
5. From healthy daylight intervals: `interval_noise_sigma` = std of `actual / expected` residual after removing the per-inverter
   factor; `inverter_efficiency_spread_sigma` = std of `k_i / median k`. Write both into the scenario YAML (replace the defaults) with a note.
6. Run detection: report which Plant 2 inverters are flagged as suspected underperformers and the residual. These are the real-data screenshots.

## 5. Synthetic year generation algorithm (M2, `app/scenarios`)
1. Fetch (once) Open-Meteo hourly 2024 for (27.54, 71.91); cache raw JSON + sha256 manifest.
2. Shift radiation timestamps to the hour midpoint; compute hourly clear-sky (Ineichen) and clear-sky index `k = GHI / GHI_cs`
   (guard low-sun hours); 15-min `GHI = k × GHI_cs,15`; split DNI/DHI by the hourly ratios; interpolate temperature and wind linearly.
3. Run the docs/02 §3.1 chain → `E_potential` per inverter (this is also what `performance` will recompute independently).
4. Draw fixed inverter factors `N(1, spread)` and per-interval noise `N(1, σ)` from the seed.
5. Apply soiling day by day (rates by month, cleanings every 15 days, the missed 2024-05-04 cleaning, rain reset ≥ 5 mm/day removes 80 %).
6. Apply events in order: grid unavailability (all inverters 0, plant status `OFFLINE`), outages (inverter 0, status code),
   curtailment (scale inverter outputs so plant AC ≤ setpoint, status `CURTAILED`, setpoint register), silent derate (× 0.92, no status), comms loss (rows `no_data` but the meter keeps counting).
7. Delivery meter = `Σ inverter AC × (1 − 0.015) × N(1, 0.002)`.
8. Operator log: for each outage, ack/onsite/restore times (docs/02 §8.3); cleaning log with the missed date absent.
9. Write measurements (status, power, weather, meter, setpoint, heartbeat), operator log, and `ground_truth.json`
   (per event: true lost kWh at delivery point; per day: true soiling fraction).

## 6. Checklist before locking (human, first hour)
- [ ] Download Kaggle dataset; record URL, licence text, sha256 of all four CSVs.
- [ ] Confirm Plant 2 inverter count, date range, irradiance units, AC/DC ratio; note gaps.
- [ ] Fetch Open-Meteo 2024 for the site; record request URL and attribution.
- [ ] Fetch PVGIS TMY for the site via `pvlib.iotools.get_pvgis_tmy`; record database used (SARAH3 or ERA5) and years.
- [ ] Run `make baseline`; P50 within 95–115 GWh. If not, stop and check azimuth/tz/units.
- [ ] Put every source in `data/manifests/` and the deck's assumptions slide.

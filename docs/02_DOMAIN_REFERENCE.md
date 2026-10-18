# 02 — Domain Reference (authoritative for every number)

All formulas here are implemented exactly once, in the module named in brackets. Parameters come from `configs/`.
Numbers marked *illustrative* are for checking intuition; the engines compute the real values.

---

## 1. The vocabulary that prevents most bugs

| Term | Definition | Module |
|---|---|---|
| **Baseline (P50/P90)** | Frozen investment case: model run on a typical meteorological year (TMY) with the full loss register, including *assumed* soiling and availability. Versioned, immutable once approved. | `baseline` |
| **E_potential** | What each inverter should have produced given the real weather, if it were available, clean and unconstrained. Includes structural losses, clipping and assumed degradation. Excludes soiling, outages, curtailment and grid loss. | `performance` |
| **E_bl_aw** | "Baseline on actual weather": E_potential at delivery point × (1 − Σ assumed attributable losses). The baseline the plant *would* have had if the TMY had been this year's weather. | `attribution` |
| **Actual** | Validated inverter AC energy (per inverter) | `quality` |
| **Accountable** | Energy recognised at the delivery-point meter for payment | `accounting` |
| **Settled** | PPA money owed, from accountable energy + PPA clauses only | `settlement` |

Energy levels: inverter AC → (× (1 − export loss 1.5 %)) → delivery point. **All bridges are at delivery point.**
Inverter-level losses are converted with the same export factor before they enter a bridge.

Comparisons:
- Baseline P50 vs E_bl_aw = **weather** (same model, same assumptions, different weather).
- E_bl_aw vs accountable = **the plant and the grid** (variance against assumed losses, named buckets + residual).
- Operations is always judged against **E_potential**, never against the baseline.

---

## 2. Data handling

### 2.1 Conventions
- 15-minute intervals, stored by **interval start** in UTC (`timestamptz`). Display in Asia/Kolkata.
- Energy in kWh (float64) for time series; money in INR as `Decimal` (`NUMERIC(18,2)`).
- Every row: `dataset_id`, `source_kind`, `batch_id` (ingest) or `model_version`/`contract_id` (engines).

### 2.2 Energy from power
`E_kWh = Σ P_kW × Δt_h` over valid intervals (Δt = 0.25 h). Never sum cumulative yield channels.
For Kaggle: cross-check `AC_POWER × 0.25` against `ΔDAILY_YIELD` per inverter-day; flag days with |diff| > 2 %.

### 2.3 Quality flags and score  [`quality`]
Per measurement: `ok | estimated | no_data | suspect`. Rules:

| Check | Flag |
|---|---|
| Missing interval or stalled heartbeat | `no_data` |
| Duplicate timestamp | keep first, `suspect` on others |
| Night output > 1 % of rated | `suspect` |
| Output > 1.02 × rated AC | `suspect` |
| Irradiance < 0 or > 1,500 W/m² | `suspect` |
| Σ inverters × (1 − export) vs delivery meter, monthly, > 1 % apart | plant-level `suspect` + reconciliation warning |
| Value filled from peers | `estimated` |

`data_quality_score(day) = ok_intervals / expected_daylight_intervals` across inverters + weather station. Raw rows are never deleted or overwritten.

---

## 3. Expected output and baseline  [`performance`, `baseline`]

### 3.1 Model chain (pvlib)
Per inverter, per interval (weather at interval **midpoint**):
1. `solpos = Location(lat, lon).get_solarposition(t_mid)`
2. Irradiance: use GHI, DNI, DHI from the source (Open-Meteo gives all three). If only GHI exists, decompose with `pvlib.irradiance.erbs`.
3. `poa = pvlib.irradiance.get_total_irradiance(tilt=25, azimuth=180, solar_zenith, solar_azimuth, dni, ghi, dhi, dni_extra, airmass, model="perez", albedo=0.25)`
4. `t_cell = pvlib.temperature.sapm_cell(poa_global, temp_air, wind_speed, **SAPM["open_rack_glass_polymer"])`
5. `p_dc = pvlib.pvsystem.pvwatts_dc(poa_global, t_cell, pdc0=3000 kW, gamma_pdc=-0.0035)`
6. Structural DC losses (multiplicative): `p_dc × (1−0.015)(1−0.015)(1−0.010)`; degradation: `× (1 − 0.005 × years_since_cod)`.
7. `p_ac = pvlib.inverter.pvwatts(p_dc, pdc0=2500/0.98, eta_inv_nom=0.98)` → clipped at 2,500 kW.
8. `E_potential_inv = p_ac × 0.25 h`.
9. Delivery point: `E_potential_dp = Σ_inv E_potential_inv × (1 − 0.015)`.

Real-data mode (Kaggle Plant 2, no orientation metadata): use the measured irradiance as plane-of-array (label the
assumption) and module temperature directly: `p_dc = k_i × G × [1 + γ(T_mod − 25)]`, with `k_i` fitted per inverter on the
first 7 clean days (calibration window) and evaluated on the rest (holdout error reported).

### 3.2 E_potential versioning
Each `expected_output` row stores `model_version` (e.g. `perf-1.0`) and `inputs_hash` = sha256 of (weather batch id,
plant config hash, model version). Changing any input creates new rows; old rows remain.

### 3.3 Baseline P50/P90
- Weather: PVGIS TMY (SARAH3 database covers Asia) for the site; hourly; run the same chain at Δt = 1 h.
- `P50_month = Σ_TMY-month E_potential_dp × (1 − assumed_soiling − assumed_availability − assumed_curtailment − assumed_grid)`
  = `× (1 − 0.020 − 0.010 − 0 − 0) = × 0.970` (additive convention — keeps the bridge exactly closing, §7.1).
- `P90 = P50 × (1 − 1.2816 × 0.065) = P50 × 0.9167`.
- Revenue case = `P50 × 2.50`. Opex, tax and debt service come from `baseline_v1.yaml` / `loan_v1.yaml`.
- Sanity: annual P50 within 95–115 GWh (≈ 1,580–1,920 kWh/kWp). Outside → check azimuth convention, units, timezone shift.
- Declared CUF for the PPA = `P50_annual / (50,000 × 8,760)` rounded to 0.1 % (*illustrative*: 105 GWh → 24.0 %).

### 3.4 Uncertainty band
`σ_rel` = standard deviation of `actual / E_potential` on healthy, clean, unclipped, unconstrained daylight intervals in the
calibration window. Band = `E_potential × (1 ± 1.96 σ_rel)`. Alarms use the band (§8.1), so normal noise never pages anyone.

---

## 4. Performance KPIs  [`performance.kpi`, `om`]

### 4.1 Performance ratio (IEC 61724-1)
`PR = (E_AC / P_STC) / (H_POA / G_STC)` with `G_STC = 1,000 W/m²`, `H_POA` in kWh/m² (plane-of-array, **not** horizontal),
`E_AC` = inverter AC energy, `P_STC` = DC kWp. Ratio of sums over the period; never the mean of interval ratios.

### 4.2 Temperature-corrected PR (25 °C)
`PR_25 = Σ E_AC,k / Σ [ P_STC × (G_POA,k / 1000) × (1 + γ (T_mod,k − 25)) ]`, `γ = −0.0035 /°C`. Removes the seasonal heat effect.

### 4.3 Energy-based availability (O&M basis)
`A_E = 1 − L_outage_eligible / E_potential_eligible`
- `L_outage_eligible` = energy lost in intervals where an inverter is in an outage whose cause is **not** excluded
  (`grid_unavailability, curtailment, force_majeure, owner_instructed, no_data` are excluded).
- `E_potential_eligible` = E_potential over the same eligible intervals (excluded intervals removed from both).
- Report monthly (provisional) and annual (contractual).

### 4.4 O&M liquidated damages (owner ← contractor; NOT PPA settlement)
`LD_kWh = max(0, 0.990 − A_E,annual) × E_potential_eligible,annual`
`LD_INR = min(LD_kWh × ₹2.50, 0.20 × ₹1.80 cr = ₹36 lakh)`
*Illustrative:* A_E = 98.6 %, E_potential_eligible = 108 GWh → 0.004 × 108,000,000 = 432,000 kWh → ₹10.8 lakh (below cap).

---

## 5. Accounting  [`accounting`]

### 5.1 Accountable energy
`accountable_kWh(interval) = MTR-DP export kWh` (the delivery-point meter is the settlement boundary; losses before it are
the generator's). If the meter interval is `no_data`: estimate as `Σ inverter actual × (1 − 0.015)`, mark `estimated`,
and record the rule in `rule_refs`.

### 5.2 Meter reconciliation
Monthly `recon_delta = (meter − Σ inv × (1 − 0.015)) / meter`. |delta| ≤ 1 % passes; otherwise warning on the Engineer
view and the delta appears as its own line inside the residual evidence.

---

## 6. PPA settlement  [`settlement` — reads accounting + PPA only]

### 6.1 Lines (each stores `clause_ref`, `qty_kwh`, `rate`, `amount_inr`, `inputs`, `provisional`)
| Line | Clause | When | Sign |
|---|---|---|---|
| Energy charge | C4.1 | monthly | + accountable × tariff |
| Backdown compensation | C4.4 | monthly | + 0.50 × avg_gen_per_hour(month) × backdown_hours × tariff |
| Excess re-pricing | C4.2 | annual true-up | − excess_kWh × tariff × (1 − 0.75) |
| Grid-unavailability compensation | C4.5 | annual true-up | + avg_gen_per_hour(year) × max(0, counted_hours − 175.2) × tariff |
| Shortfall compensation | C4.3 | annual true-up | − shortfall_kWh × tariff × 0.25 |

`avg_gen_per_hour = accountable_kWh / hours_with_generation` (hours with accountable export > 0 in that month/year).
Grid-unavailability hours count only inside 08:00–18:00 local. Backdown hours = hours with an SLDC backdown instruction.

### 6.2 CUF and the energy band
- `declared_energy = 0.240 × 50,000 kW × hours_in_year` (2024 has 8,784 h → 105.408 GWh; on 8,760 h it would be 105.12 GWh).
- `max_energy = 1.10 × declared`, `min_energy = 0.90 × declared`.
- `relaxed_min = min_energy − deemed_backdown_kWh − deemed_grid_kWh` (interpretation A, §6.6), where
  deemed_backdown_kWh = Σ_month avg_gen_per_hour × backdown_hours (the full deemed energy, not the 50 % paid) and
  deemed_grid_kWh = avg_gen_per_hour(year) × counted grid hours (all counted hours, threshold not applied).
- `excess_kWh = max(0, accountable − max_energy)`; `shortfall_kWh = max(0, relaxed_min − accountable)`.
- `cuf_actual = accountable_kWh / (50,000 × hours_in_period)`.

### 6.3 Monthly vs annual
Monthly lines are `provisional = true` until the December true-up. The CFO view labels period-to-date money
"provisional until year close". Never present provisional numbers as settled.

### 6.4 Worked examples (*illustrative*)
- **Shortfall:** declared 105.12 GWh (8,760 h basis), min 94.608 GWh, no relaxation, accountable 92.0 GWh →
  shortfall 2,608,000 kWh × ₹2.50 × 0.25 = **₹16.30 lakh** payable by the generator.
- **Backdown (October):** accountable 8.0 GWh over 340 generating hours → 23,529.4 kWh/h; 40 backdown hours →
  deemed 941,176 kWh; paid 0.50 × 941,176 × ₹2.50 = **₹11.76 lakh**. If the model says the plant actually lost
  ≈ 720 MWh to the cap, the offtaker paid for ≈ 470.6 MWh-equivalent and **the owner bears the other ≈ 249 MWh** (§7.6).
- **Grid unavailability:** 14 counted hours ≪ 175.2 h threshold → compensation ₹0; the hours still relax the minimum-energy test.

### 6.5 Rounding
Quantize each line to ₹0.01 (ROUND_HALF_UP); totals are sums of quantized lines. Store the unrounded inputs in `inputs`.

### 6.6 Interpretation (dispute mode = stretch)
Interpretation **A** (implemented): deemed kWh relax the minimum-energy test; deemed kWh are **not** added to accountable
energy, so they never earn the energy charge twice. Interpretation **B** (stretch): deemed kWh are added to accountable
energy for the CUF test instead. Dispute mode runs both and shows the ₹ difference and the clause that causes it.

---

## 7. Attribution  [`attribution`]

### 7.1 Energy bridge (per month and YTD, delivery point)
Let `Ep = Σ E_potential_dp`, assumed fractions `a_av = 0.010, a_so = 0.020, a_cu = 0, a_gr = 0`, measured gross losses
`L_av, L_so, L_cu, L_gr, L_up` (availability, soiling, curtailment, grid, suspected underperformance) from §7.2, converted to
delivery point.

| Step | Value | Controllable |
|---|---|---|
| A. Baseline P50 | `P50` | — |
| B. Weather | `E_bl_aw − P50`, where `E_bl_aw = Ep × (1 − a_av − a_so − a_cu − a_gr)` | No |
| C. Availability vs assumed | `−(L_av − a_av × Ep)` | Yes (O&M) |
| D. Soiling vs assumed | `−(L_so − a_so × Ep)` | Yes (cleaning) |
| E. Curtailment vs assumed | `−(L_cu − a_cu × Ep)` | No (offtaker/grid) |
| F. Grid unavailability vs assumed | `−(L_gr − a_gr × Ep)` | No |
| G. Underperformance (suspected) | `−L_up` | Yes, pending inspection |
| H. Degradation beyond assumed | `0` + flag `not_estimable_lt_24_months` | — |
| I. **Residual** | `accountable − (E_bl_aw + C + D + E + F + G)` | Shown openly |
| J. Accountable | `accountable` | — |

**Closure proof:** `E_bl_aw + C + D + E + F = Ep − L_av − L_so − L_cu − L_gr` (the assumed terms cancel), so
`I = accountable − (Ep − ΣL)`, i.e. exactly the unexplained part. `A + B + … + I = J` holds by construction; the test
asserts it to < 1 kWh per month. The residual carries two evidence sub-lines: unassigned interval gap, and meter delta (§5.2).

### 7.2 Interval loss assignment (precedence — shown on screen)
For each inverter-interval: `gap = E_potential_inv − actual_inv`.
1. `actual` is `no_data` → actual estimated from peers (`E_potential × median peer ratio`), flagged; gap → residual.
2. Inverter outage active (status `FAULT_*`/`OFFLINE`, inverter scope) → whole gap → **availability**.
3. Plant grid unavailability active → whole gap → **grid_unavailability**.
4. Otherwise soiling portion `s = E_potential × (1 − SR_day)` → **soiling**; remainder `r = gap − s`.
5. Curtailment active → `max(0, r)` → **curtailment**, any negative remainder → residual.
6. Suspected-underperformance event active on that inverter → `r` → **underperformance (suspected)**.
7. Else `r` → **residual**.
Every lost kWh therefore lands on exactly one bucket or the residual (invariant 4).

### 7.3 Soiling ratio estimate
Daily performance index on clean-window intervals (POA > 600 W/m², no events, not curtailed, **not clipped**:
`p_ac < 0.97 × 2,500 kW`): `PI_d = median over inverters of Σ actual / Σ E_potential`.
Reference `PI_ref` = mean PI of the 3 days following each detected cleaning (step-up in PI > 1 %) or scheduled cleaning.
`SR_d = min(1, PI_d / PI_ref)`, smoothed with a 3-day rolling median. Soiling loss fraction = `1 − SR_d`.
(Clipped intervals hide soiling, which is why they are excluded.)

### 7.4 Degradation
Both models already apply the assumed 0.5 %/year. Excess degradation cannot be separated from soiling and noise within
12 months, so step H is 0 with an explicit "requires ≥ 24 months" flag. Never hide the bar.

### 7.5 Revenue bridge (Q4)
`R_b = P50 × P_b` (P_b = ₹2.50). Steps:
1. **Volume by cause:** each energy-bridge step B…I × P_b (sums exactly to `(accountable − P50) × P_b`).
2. **Price effect:** `(P_a − P_b) × (Q_a + Q_b)/2`, with volume using `(P_a + P_b)/2` when the tariff differs (symmetric
   Shapley split: closes with no interaction term). With the fixed tariff it is ₹0 — show it anyway.
3. **Contract adjustments:** + backdown compensation, + grid compensation, − excess re-pricing, − shortfall compensation.
4. **Residual** = `R_settled − (R_b + 1 + 2 + 3)`; must be ₹0.00 (deterministic). Shown as a zero bar.

Verdict: if `|Σ volume| ≥ 2 × |price + adjustments|` → "Mostly a generation problem", else if the reverse →
"Mostly a tariff/settlement problem", else "Mixed". Show the two magnitudes beside the sentence.

### 7.6 Liability map — who bears each lost kWh (Q5)
Allocate **gross** losses (not variances) per bucket to bearers; allocations within a bucket sum to the bucket:

| Bucket | Bearer allocation (in order) |
|---|---|
| Availability | `om_contractor` = LD_kWh (§4.4, recovered as LD ₹) → `warranty_candidate` = kWh of cause codes escalated as recurring → `owner` = remainder |
| Soiling | `om_contractor_claim_candidate` = soiling loss on days inside a missed-cleaning window (scheduled date passed, not done) → `owner` = remainder |
| Curtailment | `offtaker` = backdown compensation ₹ / tariff (kWh-equivalent, **recovered** in settlement) → `owner` = remainder |
| Grid unavailability | `offtaker` = grid compensation ₹ / tariff → `owner` = remainder |
| Underperformance (suspected) | `owner_investigate` |
| Residual | `unexplained` |
| Weather | not a loss; resource risk carried by equity (and by lenders through P90 sizing) |

`recoverable_inr` distinguishes **recovered** (already in settlement or LDs) from **claim candidates** (not yet cash).

### 7.7 Residual policy
The residual is always drawn, even when ≈ 0, with its evidence sub-lines. |residual| > 2 % of `Ep` in a month →
Engineer-view warning "model or data issue — investigate before trusting buckets".

---

## 8. Detection and operations  [`detection`, `om`]

### 8.1 Rules (run per interval; events are merged runs of flagged intervals)
| Rule | Logic | Output |
|---|---|---|
| Status fault | status ∈ `FAULT_*`/`OFFLINE` (inverter) | outage, `confirmed` |
| Zero in daylight | POA > 100 W/m², p_ac < 1 % rated for ≥ 2 intervals, not curtailed, plant not offline, data present | outage, `suspected` |
| Peer deviation | daily `peer_ratio` = inverter energy / median peer energy on eligible intervals < 0.95 for ≥ 3 consecutive days | underperformance, `suspected` |
| Expected shortfall | `actual < E_potential × (1 − SR_day) × (1 − max(0.10, 2σ_rel))` for ≥ 4 consecutive daylight intervals | underperformance, `suspected` |
| Comms loss | missing actual + stalled heartbeat, meter complete | **quality flag `no_data`, not an event loss** |
Wording rule: "symptom detected — inspect", never a diagnosis. Detection is scored against ground truth (precision, recall,
and lost-kWh error per event) in the scorecard.

### 8.2 Event fields
`id, dataset_id, asset_id, category, cause_code, start, end, controllable, confidence, evidence(json: rule ids, metrics),
source_kind, work_order_id`. Synthetic scenario events are inputs to the generator; **engines re-detect** events from the
telemetry (status codes, power) — they never read the scenario file or ground truth.

### 8.3 Work orders, SLA, priority
- Auto-created for every confirmed outage (critical) and suspected underperformance (major).
- Lifecycle `open → acknowledged → onsite → restored → verified`. In the synthetic year: ack = start + 0.5 h,
  onsite = start + 3 h, restored = event end (generator writes these as operator records, labelled synthetic).
- `sla_age_ratio = elapsed_h / restore_h(severity)`; breach when restore > 96 h (critical) or 168 h (major). E05 (110 h) breaches.
- `loss_rate_kwh_per_h` = current E_potential rate − actual rate for the asset.
- `priority = loss_rate × severity_weight × (1 + 0.5 × sla_age_ratio)`; weights displayed on screen.
- `MTTR = mean(restored − start)` over closed work orders in the period.

---

## 9. Finance  [`finance`]

### 9.1 CFADS
`CFADS_month = revenue_settled_month + om_ld_received − opex/12 − tax/12 − maintenance_capex/12`
(working-capital and reserve movements = 0 in MVP, stated on screen). O&M LDs are booked at the annual assessment (December).
Do **not** call this EBITDA: it is after tax and capex.

### 9.2 DSCR
`DSCR_YTD = Σ CFADS / Σ debt_service` (provisional until December). Annual covenant test at year end.
*Illustrative case:* (26.25 − 3.30 − 0.70) / 17.0 = 22.25 / 17.0 = **1.31x** at P50. At P90 revenue (24.06 cr): 20.06 / 17.0 = 1.18x.

### 9.3 Covenant lines
Sizing 1.30x, lock-up 1.15x (equity distributions stop), default 1.05x — contract parameters from `loan_v1.yaml`.

---

## 10. Lens rules  [`lenses`]

- **Materiality (CFO):** a cause_code escalates when its annualised ₹ impact (trailing-6-month run-rate × 2, priced at the
  contract tariff) ≥ 0.5 % of baseline annual revenue (*illustrative* ₹13.1 lakh).
- **Recurrence (CFO):** same cause_code in ≥ 3 of the trailing 6 monthly periods → "Structural issue" escalation,
  bearer = `warranty_candidate`, recommended action "Review warranty / root cause with OEM".
- **Covenant watch (CFO):** DSCR_YTD < lock-up + 0.05.
- **Truth divergence (all lenses):** per month compute three verdicts — Engineer: PR_25 vs expected band (PI ≥ 0.98 =
  healthy); Ops: A_E ≥ 0.990; CFO: settled revenue ≥ P50 revenue. If verdicts disagree, emit a divergence note naming
  the largest bridge steps that explain it (e.g. "Ops ✓ availability met; CFO ✗ revenue −x %: weather −y, curtailment −z").
  Each lens sees only its own verdict plus the sentence, phrased with its own units.
- **Event-level money in CFO view** uses the contract tariff (`MWh × ₹/kWh`); the plan-vs-actual bridge prices volume at the
  baseline price. Both are allowed for the CFO; only settlement is forbidden from reading the baseline.

---

## 11. The demo event, three truths (*illustrative*; replace with engine output)

INV-07 IGBT over-temperature trip, 9–12 April 2024, 72 h (E01).

| Lens | The same event | Verdict |
|---|---|---|
| Engineer | ≈ 3,000 kWp × ~5.5 kWh/kWp/day × 3 d ≈ **49.5 MWh**; month PR_25 dips ≈ 0.4 pt; one dead column in the heatmap; fault code IGBT_OVERTEMP | Inspect cooling path |
| Operations | Critical work order, restored at 72 h < 96 h SLA; month A_E ≈ 99.5 % vs 99.0 % guarantee; ranked #1 at ≈ 2 MWh/h while producing | Expedite spare; **no LD — owner bears the loss** |
| CFO | ≈ 49.5 MWh × ₹2.50 = **₹1.24 lakh**, ≈ 0.05 % of annual revenue; DSCR unchanged | Below materiality → hidden |
| CFO, end of July | IGBT_OVERTEMP in Apr, Jun, Jul (≥ 3 of 6 months) | **Escalated: structural, warranty candidate** |

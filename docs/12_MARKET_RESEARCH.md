# 12 — Market Research & Business Numbers (India first, global context, all plant types)

Prepared 27 Oct 2026 for the Globathon Grand Finale (product/business perspective). Planning material only.
Scope: the platform is plant-type independent (the organizers' guide defines the digital twin as one representation for
solar, gas, battery, water or hybrid plants), so the market is every financed power asset — solar is one segment, with
wind, storage, round-the-clock hybrids and thermal covered in §2A and §4.5.

**How to read this:** every figure has a source link in §9. Figures marked **[derived]** are our own arithmetic from
cited inputs; figures marked **[assumption]** are team assumptions that must be labelled as such on any slide.
Where sources disagree, the range is shown. Nothing here is invented data.

---

## 1. The numbers to lead with (one-glance table)

| # | Fact | Value | Source |
|---|---|---|---|
| 1 | India installed solar (end Aug 2026) | **~168 GW** | MNRE via SolarQuarter [S1] |
| 2 | …of which ground-mounted (utility-scale), end Jul 2026 | **122.6 GW** | MNRE via SolarQuarter [S2] |
| 3 | India solar added in FY2026 (Apr 2025–Mar 2026) | **~44.6 GW** (record) | JMK Research [S3] |
| 4 | India target | **500 GW non-fossil by 2030** | pv magazine / Govt [S4] |
| 5 | World solar in operation (end 2025) | **2,391 GW** (IRENA, AC); 2.96 TW (IEA-PVPS, DC) | IRENA via pv-tech [S5]; pv magazine [S6] |
| 6 | Average power loss from equipment underperformance | **5.08 %** (2025 inspections), **~$5,070 per MW per year** | Raptor Maps Global Solar Report 2026 via pv magazine [S7] |
| 7 | Rajasthan renewable curtailment | **11.5 GW curtailed Jan–Apr 2026**, 8.3 GW in March alone | Mercom, 23 Apr 2026 [S8] |
| 8 | Rajasthan curtailment rate, 2025 | rose from **8.5 % (Mar) to 51.5 % (Aug)** | Mercom [S9] |
| 9 | Third-party solar O&M market, India | **₹17 bn (FY25) → ₹34 bn (FY30)**; 48 → 98 GW under third-party O&M | PwC via Renewable Watch [S10] |
| 10 | Utility-scale O&M cost | **~₹0.35 M/MW/yr (FY25) → ₹0.30 M/MW/yr (FY30)** | Renewable Watch [S10] |
| 11 | IREDA renewable loan book | **₹93,075 cr (31 Mar 2026), +22 % YoY** | Free Press Journal (IREDA provisional) [S11] |
| 12 | Rated Indian RE portfolios vs forecast (FY25) | ~**4 % below P90** overall; solar tracked P90 | Fitch via GreenTechLead [S12] |
| 13 | Lowest pure-solar SECI tariff found | **₹2.44/kWh** (Bhadla Phase-III); solar+storage ₹2.86/kWh (Oct 2025) | IEA [S13]; SolarQuarter [S14] |
| 14 | Global solar asset-management software market (2025) | **$1.5 bn – $4.2 bn** (definitions differ) | market reports [S15] |
| 15 | India total installed power capacity (31 Aug 2026) | **554.5 GW**; non-fossil **54.9 %**; coal 224.4 GW; gas 19.1 GW | CEA [S30] |
| 16 | India wind (31 Aug 2026) | **58.5 GW**; record **6.05 GW** added in FY26 | MNRE via EI News / Enerdata [S31] |
| 17 | India renewable capacity (30 Jun 2026) | **288.6 GW** (non-fossil 297.4 GW) | MoS MNRE in Rajya Sabha [S31] |
| 18 | India energy-storage tenders | **102 GWh tendered in 2025**; 224 GWh cumulative (92 GWh BESS + 132 GWh pumped hydro) | IESA via pv magazine India [S32] |
| 19 | Standalone BESS tariffs (2025) | **₹1.48 lakh/MW/month (2 h)**, ₹2.85 lakh/MW/month (4 h) — paid for *availability*, not kWh | IESA / Renewable Watch [S32][S33] |
| 20 | Round-the-clock / FDRE renewables | ~**10 GW** bid; tariffs **₹4–5/kWh** (ICRA); 1 GW at **₹5.25/kWh** (Aug 2026); availability 75–85 % with penalties **1.5×–4×** | ICRA [S34]; pv magazine [S35]; Mercom / Renewable Watch [S36] |
| 21 | Thermal norm | Normative annual plant availability factor **85 %** for capacity-charge recovery (CEA recommendation, 2024–29) | CEA / CERC drafts [S37] |
| 22 | World wind | **165 GW added in 2025** (record, +40 %); ~1,299 GW installed | GWEC via Mercom [S38] |

**One-line story for judges:** India runs ~555 GW of power plants, and more than half is now non-fossil. Each plant
type is paid differently: solar and wind per kWh, batteries per MW of *availability*, round-the-clock hybrids against
delivery ratios with 1.5–4× penalties, and thermal plants against an 85 % availability norm. In every case the same three
people (engineer, operations manager, CFO) read the same plant differently, and today they read it from different
spreadsheets. At ₹2.4–5/kWh tariffs, a few percent of lost or undelivered energy decides whether debt covenants hold,
and the arguments over *who pays* are already in front of CERC.

---

## 2. Market size — India

| Metric | Value | Note |
|---|---|---|
| Installed solar | ~168 GW (Aug 2026); 164 GW (Jul); 162 GW (Jun) | MNRE monthly via SolarQuarter [S1][S2] |
| Segment split (end Jul 2026) | Ground-mounted 122.57 GW · rooftop 30.74 GW · hybrid (solar part) 4.77 GW · off-grid 6.51 GW | [S2] |
| Additions | FY2026 ≈ 44.6 GW; H1 2026 ≈ 26 GW (+43 % vs H1 2025); Jan–Aug 2026 ≈ 34.45 GW | JMK [S3][S16]; [S1] |
| Policy target | 500 GW non-fossil by 2030 | [S4] |
| Third-party O&M | 48 GW (FY25, ~45 % of fleet) → 98 GW (FY30, ~35 %) | PwC via Renewable Watch [S10] |

Caveat: the two SolarQuarter monthly articles repeat one monthly-addition figure; check the MNRE dashboard for the
official number before quoting a monthly delta.

**Our beachhead = utility-scale renewables: ground-mounted solar (≈122.6 GW) + wind (≈58.5 GW) ≈ 181 GW**, plus the
storage and round-the-clock pipeline — the plants with PPAs, O&M contracts and lenders, i.e. where three different
truths actually exist. Thermal (≈244 GW coal + gas) is a later segment with a different buyer (regulated two-part tariffs).

---

## 2A. Beyond solar — each plant type has its own "truth" (why the model must be type-independent)

| Plant type | India installed / pipeline | How it gets paid | What "underperformance" means | Expected-output driver |
|---|---|---|---|---|
| Solar PV | ~168 GW (122.6 GW utility-scale) [S1][S2] | ₹/kWh PPA, CUF band, deemed generation for curtailment/grid [S13] | PR below expected, soiling, inverter outages, curtailment | Irradiance + temperature (physics: pvlib) |
| Wind | 58.5 GW [S31] | ₹/kWh PPA | Power-curve deviation, derates, icing/yaw, availability; separating weak wind from turbine faults is the hard part [S39] | Wind speed through the turbine power curve |
| Battery storage (BESS) | 92 GWh tendered by end-2025; 102 GWh of storage tendered in 2025 [S32] | **₹/MW/month for availability** (₹1.48–2.85 lakh) [S32][S33] | Unavailability, round-trip efficiency loss, capacity fade | Dispatch schedule, efficiency, capacity |
| Round-the-clock / FDRE hybrid | ~10 GW bid [S34] | ₹4–5.25/kWh, **demand-fulfilment ratios** (80 % annual / 75 % monthly / 90 % peak in one SECI auction) with 1.5×–2.5× penalties; MoP rules up to 400 % [S36] | Delivery shortfall in specific hours, not just total energy | Combined solar + wind + storage schedule |
| Gas / coal | 19.1 GW gas, 224.4 GW coal [S30] | Two-part tariff: capacity charge recovered against **85 % normative availability**, energy charge per kWh [S37] | Forced outages, ambient derating, heat-rate degradation, backdown | Ambient-corrected capacity and heat rate |

What this means for the product (and the pitch): the *three truths* hold for every row, but the contract mechanics
differ — energy-based for solar and wind, **availability-based for storage and thermal**, and **time-block delivery** for
round-the-clock hybrids. That is why settlement must be driven by contract configuration (tariff, escalation/indexation,
availability and penalty clauses) rather than hard-coded solar CUF rules.

## 3. Market size — global context

| Metric | Value | Source |
|---|---|---|
| Solar in operation, end 2025 | 2,391 GW (IRENA) / 2.96 TW DC (IEA-PVPS) | [S5][S6] |
| Added in 2025 | ~510 GW (IRENA) / ~690 GW (IEA-PVPS) | [S5][S6] |
| Solar asset-management / APM software | $1.49 bn (2025 → $4.43 bn by 2032); fleet-mgmt software $2.1 bn (14.8 % CAGR); broader PV asset-management platform $4.2 bn (→ $14.7 bn by 2034) | market reports [S15] |
| Renewable energy asset management (solar + wind + hydro + storage, incl. services) | $9.8 bn (2025) → $23.1 bn (2032) | P&S Intelligence [S15] |
| Wind | 165 GW added in 2025 (+40 %), ~1,299 GW installed; GWEC expects ~969 GW more by 2030 | GWEC via Mercom [S38] |

Use the software-market range carefully: methodologies are not public and the scopes differ. Say "independent estimates
range from $1.5 bn to $4.2 bn" rather than picking one.

---

## 4. The problem in money terms

### 4.1 Equipment underperformance
- Raptor Maps (2026 report, 2025 data): average power loss **5.08 %**, revenue at risk **up to $5,070 per MW per year**
  [S7]. Prior edition: 5.77 % / $5,720 per MWdc for 2024 (methodology changed, not directly comparable) [S17].
- These are mostly US assets; treat as "global benchmark", not an India number.
- Indian trade press cites **10–15 % annual energy loss from poor O&M** (unattributed claim) [S10] — quote only as
  "industry commentary".

### 4.2 Curtailment and transmission delay (India-specific, very current)
- Rajasthan: **11.5 GW curtailed since January 2026**, peak **8.3 GW in March** (Mercom, 23 Apr 2026) [S8].
- 2025: curtailment rose from **8.5 % in March to 51.5 % by August**; cause: delayed Phase-II transmission (8.1 GW
  evacuation scheme due Nov 2023) and weak demand [S9][S18].
- **4.3 GW** of Rajasthan solar faced complete daytime curtailment (Dec 2025) [S19].
- Developers (ACME, AMPIN, Juniper, NTPC Green and others) have petitioned **CERC for compensation**; final orders not
  found yet [S20][S21]. → Evidence of *who caused which lost kWh* is commercially valuable right now.

### 4.3 Thin tariffs, real debt
- Tariffs: **₹2.44/kWh** lowest pure-solar SECI bid (Bhadla Phase-III); **₹2.86/kWh** for solar + storage (Oct 2025)
  [S13][S14].
- Debt: IREDA alone — loan book **₹93,075 cr** (Mar 2026, +22 %), FY26 sanctions **₹51,883 cr** [S11].
- Forecast risk: Fitch-rated portfolios **~4 % below one-year P90** in FY25 (driven by wind; solar tracked P90) [S12];
  S&P (Mar 2024) found repeated portfolio-level P90 misses and warned of aggressive resource estimates [S22].
- Cash risk (date to confirm): ~₹109–111 bn overdue to renewable generators on the PRAAPTI portal in recent Mercom
  reports [S23] — year not stated in the snippets; verify before use.

### 4.4 Worked illustration **[derived]**
For a 50 MW AC / 60 MWp plant like our Thar-1 design, P50 ≈ 117.7 GWh/yr (our PVGIS-ERA5 baseline) at ₹2.50/kWh:

| Loss | Energy | Revenue |
|---|---|---|
| 1 % | 1.18 GWh | **₹29.4 lakh/yr** |
| 5.08 % (Raptor Maps average) | 5.98 GWh | **₹1.50 cr/yr** |

Fleet view **[derived, rough]**: 122.6 GW ground-mounted × an assumed ~1,600 kWh/kWp/yr **[assumption]** ≈ 196 TWh/yr.
1 % of that at ₹2.5/kWh ≈ **₹490 cr per year** across India. Present as an order of magnitude, with the assumption shown.

Other plant types **[derived from cited tariffs]**:
- **Storage:** a 100 MW / 2 h BESS at ₹1.48 lakh/MW/month earns ₹1.48 cr per month (≈₹17.8 cr per year) — for being
  *available*. Every hour of unavailability puts that payment at risk, so availability evidence is the money.
- **Round-the-clock:** at ₹5.25/kWh with a 1.5× shortfall penalty, each undelivered MWh costs ≈₹7,900; at a 4× penalty
  on a ₹5/kWh contract ≈₹20,000 per MWh. Hour-level delivery evidence is worth more here than anywhere else.

## 4.5 Non-solar loss drivers (what the platform must explain for other types)
- **Wind:** the core analytical problem is separating weak wind (resource, nobody's fault) from turbine underperformance
  (owner/OEM) — the same "weather vs plant" split our energy bridge does for solar [S39].
- **Storage:** unavailability and efficiency/capacity fade against an availability-based payment [S32][S33].
- **Round-the-clock hybrids:** shortfalls in specific time blocks and peak hours drive penalties of 1.5×–4× the tariff
  [S36]; attribution must work per time block, not only per month.
- **Thermal:** availability below the 85 % normative factor reduces capacity-charge recovery [S37]; backdown by the
  grid operator is the deemed-generation analogue.

---

## 5. Who buys, and what each buyer decides

| Buyer | Their question | Today's tools | What we give them |
|---|---|---|---|
| IPP asset owner (CFO / investor) | Is the investment case holding? Is debt safe? | SCADA exports, monthly O&M PDF, Excel models | Revenue vs frozen P50, DSCR vs covenants, escalations by rule, liability map |
| Performance engineer (owner or O&M) | Which component is underperforming? | Vendor SCADA/monitoring portals | Physics-based expected output with uncertainty band, heatmap, evidence per event |
| O&M contractor / ops manager | What do I fix first; am I meeting SLA? | CMMS, WhatsApp, spreadsheets | Ranked work queue (loss × severity × SLA age), energy availability vs guarantee |
| Lender / lenders' engineer (IREDA, banks) | Is P90 holding; are covenants at risk? | Quarterly reports from the borrower | Same numbers as the owner, from one evidence chain, with provisional flags |
| Developer in a CERC/curtailment dispute | How much did curtailment / grid cost us, provably? | Ad-hoc analyses | Interval-level loss assignment with precedence and a lineage trail |
| Storage / round-the-clock developer | Did we meet availability and time-block delivery; what penalty is coming? | Spreadsheets against tender terms | Same thread with availability-based settlement and time-block attribution |

Named market participants seen in sources: ACME Solar, AMPIN, Juniper Green, NTPC Green (CERC petitions) [S20];
CleanMax, Azure Power, Radiance (Prescinto clients) [S24]; Macquarie (chose Prescinto in 2020) [S25].

---

## 6. Competitors and alternatives

| Player | What they are | Scale / signal | Source |
|---|---|---|---|
| **Power Factors** (Unity APM, REMI AI; formerly also Greenbyte) | Global renewable APM: unified data model, analytics, event management, **energy loss allocation** | ~310 GW, 600+ customers, 18,000+ sites; Mubadala minority stake (May 2026) | [S26] |
| **Prescinto** (now IBM) | Indian-origin monitoring + analytics for solar/wind/storage | 16 GW, 14 countries; acquired by IBM (Oct 2024); clients CleanMax, Azure, Radiance | [S24][S27] |
| **SenseHawk** (Reliance) | Solar lifecycle management software (construction → O&M) | Reliance bought 79.4 % for $32 M (2022); 140+ customers, 15 countries | [S28] |
| **Raptor Maps** | Aerial/thermal inspection analytics; publishes the Global Solar Report | Benchmark source on underperformance | [S7] |
| **meteocontrol** (VCOM) | Monitoring, strong in European utility-scale | Founded 1998, Germany | [S29] |
| **QOS Energy** (Qantum) | Renewable performance SaaS | France; acquired Jul 2022 | [S29] |
| **AMMP** | Monitoring for C&I / emerging markets | — | [S29] |
| **Clir Renewables** | Wind performance analytics: loss classification against IEC categories, per-turbine derates, resource vs underperformance | Vendor-claimed up to +5 % annual energy; 6 GW on platform (2019) | [S39] |
| **GE Vernova APM** and industrial APM leaders (ABB, AVEVA, C3 AI, Emerson/AspenTech, Honeywell, IBM, SymphonyAI) | Equipment-health and reliability software across thermal and renewable fleets | Named leaders in Verdantix Green Quadrant APM 2026 | [S40] |
| **Status quo** | Inverter/turbine-vendor SCADA portals + Excel + O&M contractor monthly reports | Most common in practice | industry commentary |

Reading the landscape: **industrial APM** (GE Vernova, AVEVA, ABB…) focuses on equipment health; **renewable monitoring**
(Power Factors, Prescinto, meteocontrol, Clir…) focuses on operators and loss detection. Our wedge is the thread
*between* them: one evidence chain from the frozen investment case through contracts to the engineer's fault, across
plant types, with each role's view enforced on the server.

**Where we are different (claims to make carefully):**
1. **Three server-enforced role lenses from one evidence chain.** Competitors' public material emphasises dashboards and
   analytics for operators; we make *what each role must not see* an explicit, enforced contract.
2. **Contract-aware money.** PPA settlement (SECI-style CUF band, deemed generation for backdown/grid) and the O&M
   availability guarantee are modelled as two separate cash flows, so lost kWh become "who pays". Power Factors also
   does loss allocation, so the claim is *India-PPA and O&M-contract specific liability*, not loss allocation alone.
3. **Frozen, versioned baseline** — nobody can quietly move the P50 target; weather vs plant vs grid is separated.
4. **Deterministic and local** — no cloud AI; numbers are reproducible and auditable (fits the finale's privacy rule).
5. **Curtailment/dispute evidence** — timely given the CERC petitions above.

Do not claim competitors "can't" do something unless we have checked it; say "our focus is…".

---

## 7. Business model (proposals — all **[assumption]**, to validate)

- **Per-MW SaaS** for owners, tiered by lens (Engineer / Ops / Finance). Anchor against O&M spend: ₹0.35 M/MW/yr
  [S10]; software priced as a small fraction of that.
- **Lender / investor seat** sold to the owner (covenant and P90 reporting from the same chain).
- **Dispute evidence pack** (curtailment, grid unavailability) per event or per petition.
- **O&M contractor edition**: SLA clock and availability-guarantee proof.

Illustrative TAM sensitivity **[derived from an assumed price]** — utility-scale solar (122,600 MW) and solar + wind
(181,100 MW); storage and thermal excluded because they are priced differently:

| Assumed price per MW per year | Utility solar only / yr | Utility solar + wind / yr |
|---|---|---|
| ₹10,000 (~3 % of O&M cost) | ₹123 cr | ₹181 cr |
| ₹25,000 (~7 %) | ₹307 cr | ₹453 cr |
| ₹50,000 (~14 %) | ₹613 cr | ₹906 cr |

Payback framing **[derived]**: on a 60 MWp plant, recovering 0.5 % of energy (≈0.59 GWh ≈ ₹14.7 lakh/yr) roughly covers
₹25,000/MW/yr × 60 MW = ₹15 lakh/yr; anything above ~0.5 % is net gain. Show the inputs on the slide.

---

## 8. Open items to verify before the finale
- Official MNRE figure for Sep/Oct 2026 installed solar.
- Year of the PRAAPTI overdue figures [S23].
- Final CERC orders on curtailment compensation (petitions 782/MP/2025 and related) [S21].
- Any India-specific underperformance benchmark (NISE or rating-agency solar data) to complement Raptor Maps.
- A sanity check of the price assumptions with someone who buys O&M or monitoring in India.
- Final notified CERC tariff regulations 2024–29 (the 85 % norm above is from a CEA recommendation at draft stage) [S37].
- An independent wind underperformance benchmark (Clir's "+5 %" is a vendor claim) [S39].

---

## 9. Sources
- [S1] SolarQuarter, "India's solar capacity crosses 168 GW…", 11 Sep 2026 — https://solarquarter.com/2026/09/11/indias-solar-capacity-crosses-168-gw-as-2026-installations-near-34-45-gw-by-august-2026/
- [S2] SolarQuarter, "India's solar capacity surpasses 164 GW…", 12 Aug 2026 — https://solarquarter.com/2026/08/12/indias-solar-capacity-surpasses-164-gw-as-2026-installations-approach-29-gw-by-july-end/amp/
- [S3] JMK Research, "India Installs Record 44 GW Solar and 6 GW Wind Capacity in FY2026" — https://jmkresearch.com/india-installs-record-44-gw-solar-and-6-gw-wind-capacity-in-fy2026/
- [S4] pv magazine, "India hits 100 GW solar milestone", Feb 2025 — https://www.pv-magazine.com/2025/02/07/india-hits-100-gw-solar-milestone/
- [S5] pv-tech, "IRENA: World adds 510GW of new solar PV capacity in 2025" — https://pv-tech.org/irena-world-adds-510gw-of-new-solar-pv-capacity-in-2025
- [S6] pv magazine Australia, "Global solar additions hit 690 GW in 2025", 29 Sep 2026 — https://www.pv-magazine-australia.com/2026/09/29/global-solar-additions-hit-690-gw-in-2025/
- [S7] pv magazine, "US solar assets lose average $5,070 per MW from power losses", 25 Feb 2026 — https://www.pv-magazine.com/2026/02/25/us-solar-assets-lose-average-5070-per-mw-from-power-losses/
- [S8] Mercom, "Rajasthan Sees Nearly 12 GW of Solar, Wind Curtailment Since January", 23 Apr 2026 — https://www.mercomindia.com/rajasthan-sees-nearly-12-gw-of-solar-wind-curtailment-since-january
- [S9] Mercom, "Rajasthan curtails 4 GW of renewables as transmission delays mount" — https://www.mercomindia.com/rajasthan-curtails-4-gw-of-renewables-as-transmission-delays-mount
- [S10] Renewable Watch, "Improving Asset Performance…", 15 Dec 2025 (PwC projections) — https://renewablewatch.in/2025/12/15/improving-asset-performance-automation-analytics-and-digitalisation-define-solar-om-strategies/
- [S11] Free Press Journal, "IREDA Reports ₹51,883 Crore Loan Sanctions Growth in FY26" — https://www.freepressjournal.in/business/ireda-reports-51883-crore-loan-sanctions-growth-in-fy26-expands-renewable-financing-book
- [S12] GreenTechLead, "India Wind and Solar Project Performance Dips in FY25…, Fitch Ratings" — https://greentechlead.com/renewable-energy/india-wind-and-solar-project-performance-dips-in-fy25-solar-remains-stable-fitch-ratings-reports-50715
- [S13] IEA, "Auction of Solar Corporation of India (SECI)" — https://www.iea.org/policies/6373-auction-of-solar-corporation-of-india-seci
- [S14] SolarQuarter, "SECI concludes 2000 MW solar and 1000 MW/4000 MWh storage auction at ₹2.86/kWh", 16 Oct 2025 — https://solarquarter.com/2025/10/16/seci-concludes-2000-mw-solar-and-1000-mw-4000-mwh-energy-storage-auction-at-%E2%82%B92-86-per-kwh/
- [S15] Market reports: P&S Intelligence — https://www.psmarketresearch.com/market-analysis/renewable-energy-asset-management-market-report ; Market Intelo (fleet mgmt) — https://marketintelo.com/report/solar-fleet-management-software-market ; Market Intelo (PV asset mgmt platform) — https://marketintelo.com/report/pv-asset-management-platform-market
- [S16] JMK Research, "India Installs Record 26 GW Solar and 3 GW Wind Capacity in H1 2026" — https://jmkresearch.com/india-installs-record-26-gw-solar-and-3-gw-wind-capacity-in-h12026/
- [S17] Solar Builder, "Raptor Maps finds $4.6 billion annual revenue loss in Global Solar Report" — https://solarbuildermag.com/projects/raptor-maps-finds-4-6-billion-annual-revenue-loss-in-global-solar-report/
- [S18] Mercom, "Transmission System Delay Stalls Evacuation of 8.1 GW Renewables in Rajasthan" — https://mercomindia.com/transmission-system-delay-stalls-evacuation-of-8-1-gw-renewables-in-rajasthan
- [S19] SolarQuarter, "Rajasthan's 4.3 GW Solar Capacity Faces Daytime Curtailment…", 15 Dec 2025 — https://solarquarter.com/2025/12/15/rajasthans-4-3-gw-solar-capacity-faces-daytime-curtailment-amid-transmission-shortages/amp/
- [S20] Mercom, "CERC Admits Solar Developers' Plea for Compensation Due to Power Curtailment" — https://www.mercomindia.com/cerc-admits-solar-developers-plea-for-compensation-due-to-power-curtailment
- [S21] CERC record of proceedings 782/MP/2025, 29 Apr 2026 — https://cercind.gov.in/2026/ROP/782-MP-2025_290426.pdf
- [S22] S&P Global Ratings research (Mar 2024) — https://spglobal.com/_assets/documents/ratings/research/101594164.pdf
- [S23] Mercom, "Discoms' dues to renewable generators keep rising" — https://www.mercomindia.com/discoms-dues-to-renewable-generators-keep-rising
- [S24] YourStory, "IBM acquires Bengaluru-based SaaS startup Prescinto", Oct 2024 — https://yourstory.com/2024/10/ibm-acquires-bengaluru-saas-startup-prescinto-renewable-energy
- [S25] Renewable Watch, "Macquarie selects Prescinto Monitoring & Analytics platform", Sep 2020 — https://renewablewatch.in/2020/09/04/macquarie-selects-prescinto-monitoring-analytics-platform-for-clean-energy-portfolio/
- [S26] AlternativesWatch, "Mubadala takes minority stake in renewables software provider Power Factors", 6 May 2026 — https://www.alternativeswatch.com/2026/05/06/mubadala-takes-minority-stake-in-renewables-software-provider-power-factors/ ; Gartner profile — https://www.gartner.com/reviews/product/unity
- [S27] Mercom, "Solar Monitoring and Analytics Company Prescinto Raises $6.5 Million" — https://mercomindia.com/solar-monitoring-company-prescinto-raises-6-5-million
- [S28] pv-tech, "Reliance Industries buys 80% stake in US solar software company SenseHawk" — https://pv-tech.org/reliance-industries-buys-80-stake-in-us-solar-software-company-sensehawk
- [S29] CB Insights (QOS Energy, meteocontrol profiles) — https://www.cbinsights.com/company/qos-energy/alternatives-competitors ; AMMP comparison page (vendor-authored) — https://www.ammp.io/compare/meteocontrol
- [S30] CEA, Installed capacity report, Aug 2026 — https://cea.nic.in/wp-content/uploads/installed/2026/08/IC_Aug_2026.pdf
- [S31] Energetica India, "India adds 6.05 GW wind power capacity in FY26…" — https://www.energetica-india.net/news/india-adds-6-05-gw-wind-power-capacity-in-fy26-total-installed-capacity-crosses-56-gw ; Enerdata — https://www.enerdata.net/publications/daily-energy-news/india-achieves-highest-annual-wind-capacity-addition-605-gw-fy25-26.html ; WindInsider (57.44 GW, Jun 2026) — https://windinsider.com/2026/07/15/indias-wind-capacity-climbs-to-57-44-gw-with-gujarat-capturing-over-43-of-new-installations-in-h1-2026/
- [S32] pv magazine India, "India's energy storage market poised for breakout year: IESA" — https://www.pv-magazine-india.com/?p=14011 ; IEEFA/JMK storage tracker (Aug–Sep 2026) — https://ieefa.org/sites/default/files/2026-09/ESSjmk-0926.pdf
- [S33] Renewable Watch, "Growing Pipeline: Battery storage market moves towards larger-scale deployment", Jun 2026 — https://renewablewatch.in/2026/06/30/growing-pipeline-battery-storage-market-moves-towards-larger-scale-deployment/ ; ESS News (GUVNL 335 MW/670 MWh at ₹2.10 lakh/MW/month) — https://www.ess-news.com/2026/02/12/indias-670-mwh-battery-storage-tender-under-vgf-scheme-yields-2500-mw-month-tariff/
- [S34] ICRA research on RTC/FDRE tenders — https://www.icra.in/Media/GetNewsFile/22779
- [S35] pv magazine, "SECI's 1 GW FDRE RTC power tender discovers INR 5.25/kWh tariff", 10 Aug 2026 — https://www.pv-magazine.com/2026/08/10/secis-1-gw-fdre-rtc-power-tender-discovers-inr-5-25-kwh-tariff/
- [S36] Renewable Watch, "SECI announces auction results for 1.2 GW RTC renewable projects", May 2025 — https://renewablewatch.in/2025/05/28/seci-announces-auction-results-for-1-2-gw-rtc-renewable-projects/ ; Mercom, "Shortfall in Supply of Bundled Renewable Power to Attract Penalty of 400%" — https://mercomindia.com/shortfall-supply-bundled-renewable-power
- [S37] CEA recommendation on operation norms for CERC tariff regulations 2024–29 — https://cercind.gov.in/2024/draft_reg/TTF2024/CEA-Recommendation%20on%20Operation%20Norms.pdf (draft-stage; confirm against the final notified regulations)
- [S38] Mercom, "Global wind energy installations hit 165 GW in 2025, up 40% YoY" — https://mercomindia.com/global-wind-energy-installations-hit-165-gw-in-2025-up-40-yoy
- [S39] Clir Renewables, wind portfolio intelligence — https://www.clir.eco/wind ; "Clir hits 6 GW milestone" — https://www.clir.eco/news/clir-hits-6-gw-milestone-tripling-its-global-asset-portfolio-in-a-year/
- [S40] Verdantix, "Green Quadrant: Asset Performance Management (APM) Solutions (2026)" — https://www.verdantix.com/insights/report/green-quadrant--asset-performance-management-apm-solutions-2026 ; GE Vernova, "APM for renewables" — https://gevernova.com/software/blog/apm-for-renewables-ge-vernova-leads-the-way

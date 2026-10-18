# 05 — API Contract (FastAPI, JSON)

Base path `/v1`. All endpoints need `Authorization: Bearer <demo JWT>`; role and plant scope come from the token only.
The frontend builds against `data/fixtures/*.json` that match these shapes, so web work can start in hour 1.

## 1. Auth
`POST /v1/auth/demo-login` `{ "user": "engineer" | "operations" | "cfo" | "presenter" }`
→ `{ "token": "...", "role": "cfo", "plants": ["THAR1","KGL-P2"] }`
Demo users only; the secret is in `.env`. No external identity provider (runs offline).

## 2. Lens view (the core endpoint)
`GET /v1/view?plant_id=THAR1&dataset_id=thar1_demo_2024&period=2024-04[&event_id=...]`
→ `LensPayload` for the token's role. 403 if the plant is outside the token's scope.

```jsonc
{
  "meta": {
    "plant_id": "THAR1", "dataset_id": "thar1_demo_2024", "period": "2024-04", "tz": "Asia/Kolkata",
    "mode": { "kind": "synthetic_scenario", "label": "SYNTHETIC SCENARIO · thar1_demo_2024" },
    "lens": { "id": "cfo", "version": 1, "spec_hash": "sha256:…" },
    "baseline_version": 1,                       // absent for engineer/operations (omitted, see `omitted`)
    "data_quality_score": 0.996,
    "payload_hash": "sha256:…",                  // used by /rosetta to prove byte-identity
    "generated_at": "2026-10-18T09:00:00Z"
  },
  "decision": "Is the investment case holding, and is the debt safe?",
  "tiles": [ MetricCard, … ],
  "sections": { "<section_id>": { … section-specific shape (below) … } },
  "events": [ EventRow, … ],                     // only lens-allowed fields; CFO gets escalations instead
  "escalations": [ Escalation, … ],              // CFO only
  "divergence": { "verdict": "red", "note": "Ops ✓ availability met; revenue −4.1 %: weather −2.9 %, curtailment −0.9 %" },
  "actions": [ { "text": "…", "value": "…", "lineage_id": "…" } ],
  "omitted": [ { "kind": "metric", "id": "peer_ratio", "reason": "Inverter-level diagnostics would make the CFO a part-time engineer." } ],
  "stripped": { "count": 5, "kinds": { "metric": 4, "field": 1 } }   // receipt only: names of stripped items are in `omitted`
}
```

### MetricCard
```jsonc
{
  "metric_id": "revenue_settled_inr", "label": "Settled PPA revenue",
  "value": "21340000.00", "unit": "INR", "display": "₹2.13 cr",
  "provisional": true, "source_kind": "derived", "quality": "ok",
  "compare": { "against": "revenue_baseline_inr", "value": "22250000.00", "delta_pct": -4.1 },
  "lineage_id": "uuid", "lineage_hash": "sha256:…",
  "chip": "= 8.54 GWh accountable × ₹2.50 (PPA-THAR1-v1 C4.1) + adjustments"   // built server-side from lens-allowed parts only
}
```
Chip rule: the chip may reference only units and parameters the lens allows. Engineer chips never contain ₹ or tariff;
CFO chips never contain inverter ids.

### Section shapes
- `loss_waterfall_kwh` / `energy_bridge` / `revenue_bridge`: `{ "steps": [ { "order": 1, "bucket": "baseline", "value": "…", "unit": "kWh|INR", "controllable": null, "confidence": null, "lineage_id": "…" } ], "closes": true, "residual": "…", "precedence": ["outage","grid","soiling","curtailment","underperformance","residual"] }`
- `inverter_heatmap`: `{ "assets": ["INV-01",…], "days": ["2024-04-01",…], "ratio": [[…]], "metric_id": "peer_ratio" }`
- `pr_trend`: `{ "months": […], "pr": […], "pr_25": […], "band_low": […], "band_high": […] }`
- `work_queue`: `{ "weights": { "critical": 1.0, "major": 0.6, "minor": 0.3, "sla_factor": 0.5 }, "items": [ WorkItem ] }`
- `availability_vs_guarantee`: `{ "a_e": 0.9951, "guarantee": 0.99, "trend": […] }`
- `dscr_vs_covenants`: `{ "dscr_ytd": "1.29", "sizing": "1.30", "lockup": "1.15", "default": "1.05", "provisional": true }`
- `liability_map`: `{ "rows": [ { "bucket": "curtailment", "bearer": "offtaker", "kwh": "…", "inr": "…", "status": "recovered|claim_candidate|borne" } ] }`

### Escalation (CFO)
```jsonc
{ "cause_code": "IGBT_OVERTEMP", "rule": "recurrence", "label": "Structural issue",
  "periods_hit": ["2024-04","2024-06","2024-07"], "assets_count": 2,
  "annualised_impact_inr": "…", "bearer": "warranty_candidate",
  "recommended_action": "Review warranty / root cause with OEM", "lineage_id": "…" }
```

## 3. Rosetta (presenter only)
`GET /v1/rosetta/{event_id}?dataset_id=…`
→ `{ "event_id": "…", "panels": { "engineer": LensEventView, "operations": LensEventView, "cfo": LensEventView | {"hidden": true, "reason": "below materiality", "threshold_inr": "…"} }, "hashes": { "engineer": "sha256:…", … }, "reconciliation": [ "49.5 MWh (engineer) = 49.5 MWh (operations work order) → ₹1.24 lakh (cfo, tariff C4.1)" ] }`
Each panel is produced by calling the same projection function the lens endpoint uses; the hashes must equal what each
role's `/view` returns for that event.

## 4. Lineage
`GET /v1/lineage/{metric_value_id}` → tree of inputs (`metric_value` → engine rows → measurements/contracts/baseline).
Nodes outside the caller's lens come back as `{ "redacted": true, "reason": "<omission reason>" }` — never their values.

## 5. Supporting endpoints
| Method & path | Role | Purpose |
|---|---|---|
| `GET /v1/reconciliation?dataset_id=` | all | latest `recon_result` rows (green badges) |
| `GET /v1/scorecard?dataset_id=thar1_demo_2024` | presenter, engineer | detection precision/recall, per-event lost-kWh error, per-bucket true vs attributed |
| `GET /v1/baseline/versions?plant_id=` | cfo, presenter | version list with approver, time, reason |
| `POST /v1/baseline/{id}/approve` | presenter (admin) | draft → approved (then immutable) |
| `PATCH /v1/baseline/{id}` | — | always `409 baseline_immutable` once approved |
| `GET /v1/workorders?status=open` | operations | work queue |
| `POST /v1/workorders/{id}/transition` | operations | `{ "to": "acknowledged" }` etc.; writes `audit_event` |
| `GET /v1/datasets` | all | available datasets with kind and mode label |
| `WS /v1/live` | all (stretch) | replay stream of lens-filtered deltas |

## 6. Errors
`401 unauthenticated`, `403 plant_out_of_scope`, `404 not_found`, `409 baseline_immutable`,
`422 validation`, `500 lens_guard_violation` (payload would have leaked a forbidden field — logged, never returned).

"""Role views (D31): server-side enforcement — forbidden metric ids, money words and inverter ids never ship;
role from the token only; plant scope; presenter may view any lens; work-order transitions are role-gated."""

import json
import re

import pytest
from fastapi import HTTPException

from app.api.views import common
from app.core.auth import issue_token

pytestmark = pytest.mark.db
DS, PERIOD = "thar1_demo_2024", "2024-04"


def _h(user, **kw):
    return {"Authorization": f"Bearer {issue_token(user, **kw)}"}


def _view(api, user, **params):
    r = api.get("/v1/view", params={"dataset_id": DS, "period": PERIOD, **params}, headers=_h(user))
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize("lens", ["engineer", "operations", "cfo"])
def test_payload_has_only_lens_metrics(api, lens):
    payload = _view(api, lens)
    assert payload["meta"]["lens"]["id"] == lens
    body = json.dumps({k: v for k, v in payload.items() if k != "omitted"}, ensure_ascii=False)
    leaked = [m for m in common.forbidden_ids(lens) if re.search(rf"\b{m}\b", body)]
    assert leaked == []
    if lens in ("engineer", "operations"):
        assert not any(t in body for t in ("₹", "tariff", "INR", "lakh", "crore"))
    else:
        assert not re.search(r"\bINV-\d+", body)
    assert payload["stripped"]["count"] == sum(payload["stripped"]["kinds"].values())
    assert {o["id"] for o in payload["omitted"]} == {
        o.get("metric") or o.get("field") for o in common.lens_spec(lens)["omit"]
    }


def test_role_from_token_not_query(api):
    assert _view(api, "engineer", lens="cfo")["meta"]["lens"]["id"] == "engineer"


def test_presenter_gets_exactly_the_role_payload(api):
    as_cfo = _view(api, "cfo")
    as_presenter = _view(api, "presenter", lens="cfo")
    assert as_presenter["meta"]["payload_hash"] == as_cfo["meta"]["payload_hash"]


def test_cross_plant_is_403(api):
    r = api.get(
        "/v1/view", params={"dataset_id": DS, "period": PERIOD}, headers=_h("someone", role="cfo", plants=["KGL-P2"])
    )
    assert r.status_code == 403


def test_guard_refuses_a_leak(demo_engine):
    with demo_engine.begin() as conn, pytest.raises(HTTPException) as exc:
        common.guard(conn, "engineer", {"tiles": [{"metric_id": "revenue_settled_inr", "display": "₹2 cr"}]}, "t")
    assert exc.value.status_code == 500


def test_cfo_april_hides_single_outage(api):
    esc = _view(api, "cfo")["escalations"]
    assert all(e["cause_code"] != "IGBT_OVERTEMP" for e in esc["items"])
    assert any(e["cause_code"] == "IGBT_OVERTEMP" for e in esc["below_threshold"])


def test_engineer_trace_allowed_cfo_forbidden(api):
    ev = _view(api, "engineer")["events"]
    e01 = next(e for e in ev if e["cause_code"] == "IGBT_OVERTEMP")
    assert e01["lost_kwh"] > 0 and e01["duration_h"] == 72.0
    ok = api.get(f"/v1/events/{e01['id']}/trace", params={"dataset_id": DS}, headers=_h("engineer"))
    assert ok.status_code == 200 and len(ok.json()["ts"]) > 0
    assert api.get(f"/v1/events/{e01['id']}/trace", params={"dataset_id": DS}, headers=_h("cfo")).status_code == 403


def test_workorder_transitions(api):
    items = _view(api, "operations")["sections"]["work_queue"]["items"]
    wo = next(i for i in items if i["status"] == "restored")
    url = f"/v1/workorders/{wo['id']}/transition"
    assert api.post(url, json={"to": "verified"}, headers=_h("cfo")).status_code == 403
    assert api.post(url, json={"to": "onsite"}, headers=_h("operations")).status_code == 409
    r = api.post(url, json={"to": "verified"}, headers=_h("operations"))
    assert r.status_code == 200 and r.json()["to"] == "verified"

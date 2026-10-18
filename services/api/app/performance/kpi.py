"""Performance KPIs from stored rows (docs/02 §4.1–4.2). Ratio of sums, never the mean of interval ratios.

PR    = Σ E_AC / Σ (P_STC × G_POA / 1000 × Δt)
PR_25 = Σ E_AC / Σ (P_STC × G_POA / 1000 × Δt × (1 + γ (T_mod − 25)))
The expected PR_25 uses E_potential in the numerator, with the model's ± band.
"""

import pandas as pd
from sqlalchemy import Connection, text

MONTHLY_SQL = """
WITH x AS (SELECT ts_start, sum(e_potential_kwh) AS ep, max(poa_wm2) AS poa, max(band_rel) AS band
           FROM expected_output WHERE dataset_id = :d GROUP BY ts_start),
     a AS (SELECT ts_start, sum(e_kwh) AS ea FROM actual_output WHERE dataset_id = :d GROUP BY ts_start),
     t AS (SELECT ts_start, value AS t_mod FROM measurement WHERE dataset_id = :d AND quantity = 't_mod_c')
SELECT date_trunc('month', x.ts_start AT TIME ZONE 'Asia/Kolkata')::date AS month,
       sum(a.ea) AS e_ac, sum(x.ep) AS e_pot, sum(x.poa * 0.25 / 1000.0) AS h_poa,
       sum(x.poa * 0.25 / 1000.0 * (1 + :g * (coalesce(t.t_mod, 25) - 25))) AS h_poa_25, max(x.band) AS band
FROM x LEFT JOIN a USING (ts_start) LEFT JOIN t USING (ts_start)
GROUP BY 1 ORDER BY 1
"""


def monthly_pr(conn: Connection, dataset_id: str, p_stc_kwp: float, gamma: float) -> pd.DataFrame:
    """Plant-level PR, PR_25 and expected PR_25 ± band per local month."""
    df = pd.read_sql(text(MONTHLY_SQL), conn, params={"d": dataset_id, "g": gamma})
    if df.empty:
        return df
    df["pr"] = df["e_ac"] / (p_stc_kwp * df["h_poa"])
    df["pr_25"] = df["e_ac"] / (p_stc_kwp * df["h_poa_25"])
    df["pr_25_expected"] = df["e_pot"] / (p_stc_kwp * df["h_poa_25"])
    df["pr_25_low"] = df["pr_25_expected"] * (1 - df["band"])
    df["pr_25_high"] = df["pr_25_expected"] * (1 + df["band"])
    df["performance_index"] = df["pr_25"] / df["pr_25_expected"]
    return df

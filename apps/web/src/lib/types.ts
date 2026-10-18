// Shapes returned by /v1 (docs/05, D31). Values arrive pre-computed with server-built `display` strings.

export type Dataset = {
  id: string;
  plant_id: string;
  kind: "synthetic" | "measured";
  mode: { kind: string; label: string };
  periods: string[];
  default_period: string;
};

export type MetricCard = {
  metric_id: string;
  label: string;
  value: string | null;
  unit: string;
  display: string;
  source_kind: string;
  provisional: boolean;
  compare: { against: string; value?: string; delta_pct?: number | null } | null;
  chip: string | null;
  status: "ok" | "warn" | "alert" | "info";
  hint: string | null;
};

export type Omitted = { kind: "metric" | "field"; id: string; reason: string; scope?: string };

export type LensPayload = {
  meta: {
    plant_id: string;
    dataset_id: string;
    period: string;
    periods: string[];
    mode: { kind: string; label: string };
    lens: { id: "engineer" | "operations" | "cfo"; version: number; spec_hash: string };
    payload_hash: string;
    generated_at: string;
    data_quality_score?: number | null;
    baseline_version?: number;
    provisional?: boolean;
  };
  decision: string;
  tiles: MetricCard[];
  sections: Record<string, any>;
  events: any[];
  escalations?: any;
  omitted: Omitted[];
  stripped: { count: number; kinds: Record<string, number> };
};

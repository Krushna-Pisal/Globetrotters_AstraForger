import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CircleAlert, Cpu, Search } from "lucide-react";
import { AppShell, PageFooter } from "../components/AppShell";
import { DailyEnergyChart, LossWaterfall, PeerHeatmap, PrTrendChart, TraceChart } from "../components/charts/charts";
import { EmptyState, Loading, Notice, Panel, StatusPill, TileRow } from "../components/ui";
import { api, qs } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useLensView, useScope } from "../lib/hooks";
import { monthLabel, titleCase } from "../lib/format";

const CATEGORY_TONE: Record<string, "alert" | "warn" | "info"> = {
  equipment_outage: "alert",
  underperformance: "warn",
  grid_unavailability: "info",
  curtailment: "info",
};

function EventTrace({ eventId, datasetId }: { eventId: string; datasetId: string }) {
  const { session } = useAuth();
  const { data, isLoading } = useQuery({
    queryKey: ["trace", eventId, datasetId],
    queryFn: () => api<any>(`/v1/events/${eventId}/trace?${qs({ dataset_id: datasetId })}`, { token: session?.token }),
  });
  if (isLoading || !data) return <Loading label="Loading 15-min trace" />;
  return <TraceChart t={data} />;
}

export default function EngineerPage() {
  const { data, isLoading, error } = useLensView("engineer");
  const { dataset, period } = useScope();
  const [selected, setSelected] = useState<string | null>(null);
  const events = data?.events ?? [];
  useEffect(() => {
    setSelected(events[0]?.id ?? null);
  }, [data?.meta.period, data?.meta.dataset_id]); // eslint-disable-line react-hooks/exhaustive-deps
  const sel = events.find((e: any) => e.id === selected);
  const s = data?.sections;

  return (
    <AppShell title="Engineering" decision={data?.decision ?? "Is the plant physically healthy, and which component is underperforming?"}>
      {isLoading && <Loading />}
      {error && <Notice tone="warn">{String((error as Error).message)}</Notice>}
      {data && s && (
        <div className="space-y-4">
          <TileRow tiles={data.tiles} />

          <div className="grid gap-4 xl:grid-cols-12">
            <Panel
              className="xl:col-span-8"
              title="Daily energy vs expected"
              subtitle={`Plant total per day, MWh · ${monthLabel(data.meta.period)} · expected from ${s.daily_energy.model_note}, ±95 % band`}
            >
              <DailyEnergyChart s={s.daily_energy} />
            </Panel>
            <Panel className="xl:col-span-4" title="Temperature-corrected PR" subtitle="IEC 61724 · ratio of sums">
              {s.pr_trend.unavailable ? (
                <EmptyState title="PR not computable">{s.pr_trend.unavailable}</EmptyState>
              ) : (
                <PrTrendChart s={s.pr_trend} current={data.meta.period} />
              )}
            </Panel>
          </div>

          <div className="grid gap-4 xl:grid-cols-12">
            <Panel
              className="xl:col-span-7"
              title="Inverter × day — output vs peer median"
              subtitle={`Red = below peers. The detection rule flags a sustained drop below ${s.inverter_heatmap.threshold} of each inverter's own reference.`}
            >
              {s.inverter_heatmap.assets.length ? <PeerHeatmap s={s.inverter_heatmap} /> : <EmptyState title="No eligible intervals" />}
            </Panel>
            <Panel className="xl:col-span-5" title="Where the energy went" subtitle="Expected → actual for the month, MWh · precedence: outage → grid → curtailment → underperformance">
              <LossWaterfall steps={s.loss_waterfall_kwh.steps} />
              <div className="mt-2 flex flex-wrap gap-3 text-[11.5px] text-ink-3">
                <Legend color="#eb6834" label="Controllable" />
                <Legend color="#6250d6" label="Uncontrollable" />
                <Legend color="#898781" label="Not yet attributed" hatched />
              </div>
              <p className="mt-2 text-[11.5px] leading-snug text-ink-4">{s.loss_waterfall_kwh.note}</p>
            </Panel>
          </div>

          <div className="grid items-start gap-4 xl:grid-cols-12">
            <Panel
              className="xl:col-span-7"
              title="Events with evidence"
              subtitle="Detected from SCADA status codes and peer comparison — never read from the scenario file"
              bodyClass="p-0"
            >
              {events.length === 0 ? (
                <EmptyState title="No events in this period" />
              ) : (
                <div className="max-h-[420px] overflow-auto">
                  <table className="tbl">
                    <thead className="sticky top-0">
                      <tr>
                        <th>Asset</th>
                        <th>Cause</th>
                        <th>Start (IST)</th>
                        <th className="text-right">Duration</th>
                        <th className="text-right">Energy gap</th>
                        <th>Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {events.map((e: any) => (
                        <tr
                          key={e.id}
                          onClick={() => setSelected(e.id)}
                          className={`cursor-pointer ${selected === e.id ? "[&>td]:bg-brand-50" : ""}`}
                        >
                          <td className="font-mono text-[12.5px] font-medium text-ink">{e.asset}</td>
                          <td>
                            <div className="flex flex-col">
                              <span className="font-medium text-ink-2">{e.cause_code}</span>
                              <span className="text-[11px] text-ink-4">{titleCase(e.category)}</span>
                            </div>
                          </td>
                          <td className="num">{e.start}</td>
                          <td className="num text-right">{e.duration_h === null ? "ongoing" : `${e.duration_h} h`}</td>
                          <td className="num text-right font-medium text-ink">{e.lost_display}</td>
                          <td>
                            <StatusPill status={e.confidence === "confirmed" ? CATEGORY_TONE[e.category] ?? "info" : "warn"}>
                              {e.confidence}
                            </StatusPill>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Panel>
            <Panel
              className="xl:col-span-5"
              title={sel ? `${sel.asset} · ${sel.cause_code}` : "Event trace"}
              subtitle={sel ? `${sel.start} → ${sel.end ?? "ongoing"} · kWh per 15 min, expected vs actual` : "Select an event"}
            >
              {sel && dataset ? (
                <>
                  <EventTrace eventId={sel.id} datasetId={dataset.id} />
                  <div className="mt-3 grid grid-cols-2 gap-2 text-[12px]">
                    <Fact icon={<Search size={13} />} label="Rule" value={sel.evidence.rules.join(", ")} />
                    <Fact icon={<CircleAlert size={13} />} label="Wording" value={sel.wording} />
                    {Object.entries(sel.evidence.detail ?? {})
                      .slice(0, 4)
                      .map(([k, v]) => (
                        <Fact key={k} icon={<Cpu size={13} />} label={titleCase(k)} value={String(v)} />
                      ))}
                  </div>
                </>
              ) : (
                <EmptyState title="No event selected" />
              )}
            </Panel>
          </div>

          <PageFooter
            items={[
              `Plant ${data.meta.plant_id}`,
              data.meta.mode.label,
              `Period ${period}`,
              `Lens engineer v${data.meta.lens.version}`,
              `Payload ${data.meta.payload_hash.slice(7, 19)}`,
            ]}
          />
        </div>
      )}
    </AppShell>
  );
}

function Legend({ color, label, hatched }: { color: string; label: string; hatched?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className="h-2.5 w-2.5 rounded-sm"
        style={{
          background: hatched ? `repeating-linear-gradient(45deg, ${color}, ${color} 2px, #d8d7d2 2px, #d8d7d2 4px)` : color,
        }}
      />
      {label}
    </span>
  );
}

export function Fact({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-steel-50 px-2.5 py-1.5">
      <p className="flex items-center gap-1 text-[10.5px] font-medium uppercase tracking-wider text-ink-4">
        {icon}
        {label}
      </p>
      <p className="mt-0.5 truncate text-ink-2" title={value}>
        {value}
      </p>
    </div>
  );
}

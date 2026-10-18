import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CalendarCheck2, CalendarX2, Check, Timer } from "lucide-react";
import { AppShell, PageFooter } from "../components/AppShell";
import { AvailabilityTrend, PerformanceIndexChart } from "../components/charts/charts";
import { EmptyState, Loading, Notice, Panel, StatusPill, TileRow } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useLensView, useScope } from "../lib/hooks";
import { monthLabel, titleCase } from "../lib/format";

const SEV: Record<string, string> = {
  critical: "bg-critical-bg text-critical-ink border-critical/30",
  major: "bg-serious-bg text-serious-ink border-serious/40",
  minor: "bg-steel-100 text-ink-2 border-line",
};
const ACTION: Record<string, string> = { acknowledged: "Acknowledge", onsite: "Mark on site", restored: "Mark restored", verified: "Verify" };

function SlaClock({ c }: { c: any }) {
  // Width is the server-computed age ratio (elapsed ÷ contractual restore time).
  const pct = Math.min(1, c.age_ratio ?? 0) * 100;
  const tone = c.breached ? "bg-critical" : (c.age_ratio ?? 0) > 0.75 ? "bg-warning" : "bg-good";
  return (
    <div className="min-w-[120px]">
      <div className="flex justify-between text-[11px] text-ink-3">
        <span className="num">{c.elapsed_h} h</span>
        <span className="num">SLA {c.restore_h} h</span>
      </div>
      <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-steel-100">
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
      {c.breached && <p className="mt-0.5 text-[10.5px] font-semibold text-critical-ink">SLA breached</p>}
    </div>
  );
}

export default function OperationsPage() {
  const { data, isLoading, error } = useLensView("operations");
  const { period } = useScope();
  const { session } = useAuth();
  const qc = useQueryClient();
  const move = useMutation({
    mutationFn: ({ id, to }: { id: string; to: string }) =>
      api(`/v1/workorders/${id}/transition`, { method: "POST", body: JSON.stringify({ to }), token: session?.token }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["view", "operations"] }),
  });
  const s = data?.sections;

  return (
    <AppShell title="Operations" decision={data?.decision ?? "What do I fix first today, and is the O&M contractor meeting its SLA?"}>
      {isLoading && <Loading />}
      {error && <Notice tone="warn">{String((error as Error).message)}</Notice>}
      {data && s && s.unavailable && (
        <div className="space-y-4">
          <div className="card">
            <EmptyState title="No O&M contract for this dataset">{s.unavailable}</EmptyState>
          </div>
        </div>
      )}
      {data && s && !s.unavailable && (
        <div className="space-y-4">
          <TileRow tiles={data.tiles} />
          <div className="grid gap-4 xl:grid-cols-12">
            <Panel
              className="xl:col-span-8"
              title="Work queue"
              subtitle={<>Ranked by priority = {s.work_queue.formula} · weights critical 1.0 · major 0.6 · minor 0.3</>}
              bodyClass="p-0"
            >
              {s.work_queue.items.length === 0 ? (
                <EmptyState title="Nothing in the queue this month" />
              ) : (
                <div className="max-h-[460px] overflow-auto">
                  <table className="tbl">
                    <thead className="sticky top-0 z-10">
                      <tr>
                        <th className="w-8">#</th>
                        <th>Asset · cause</th>
                        <th>SLA clock</th>
                        <th className="text-right">Energy lost</th>
                        <th className="text-right">Priority</th>
                        <th className="text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {s.work_queue.items.map((w: any, i: number) => (
                        <tr key={w.id}>
                          <td className="num text-ink-4">{i + 1}</td>
                          <td>
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-[12.5px] font-semibold text-ink">{w.asset}</span>
                              <span className={`rounded border px-1.5 py-px text-[10px] font-semibold uppercase ${SEV[w.severity]}`}>{w.severity}</span>
                            </div>
                            <p className="mt-0.5 text-[11.5px] text-ink-3">
                              {w.cause_code} · {w.opened}
                            </p>
                          </td>
                          <td>
                            <SlaClock c={w.sla_clock} />
                          </td>
                          <td className="num whitespace-nowrap text-right">
                            <p className="font-medium text-ink">{w.lost_display}</p>
                            <p className="text-[11px] text-ink-4">{w.loss_rate_display} at start</p>
                          </td>
                          <td className="num text-right font-semibold text-ink" title={JSON.stringify(w.priority_inputs, null, 1)}>
                            {w.priority_score.toLocaleString("en-IN")}
                          </td>
                          <td className="text-right">
                            <div className="flex flex-col items-end gap-1">
                              <StatusPill status={w.status === "verified" || w.status === "restored" ? "ok" : "warn"}>{titleCase(w.status)}</StatusPill>
                              {w.next_status && (
                                <button
                                  className="btn-ghost whitespace-nowrap px-2 py-0.5 text-[11.5px]"
                                  disabled={move.isPending}
                                  onClick={() => move.mutate({ id: w.id, to: w.next_status })}
                                >
                                  <Check size={12} /> {ACTION[w.next_status]}
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {move.isError && <p className="px-4 py-2 text-[12px] text-critical-ink">Transition refused: {String((move.error as Error).message)}</p>}
            </Panel>
            <Panel className="xl:col-span-4" title="Availability vs guarantee" subtitle="Energy-based, excludes grid, curtailment and comms gaps">
              <AvailabilityTrend s={s.availability_vs_guarantee} current={data.meta.period} />
              <p className="mt-2 text-[12px] leading-snug text-ink-3">
                Below 99.0 % for the year triggers liquidated damages from the O&amp;M contractor. Above it, the owner bears outage losses.
              </p>
            </Panel>
          </div>

          <div className="grid gap-4 xl:grid-cols-12">
            <Panel className="xl:col-span-7" title="Soiling & cleaning" subtitle={`Contract cleaning every ${s.soiling_and_cleaning.interval_days} days`}>
              <PerformanceIndexChart
                s={s.soiling_and_cleaning.performance_index}
                cleanings={s.soiling_and_cleaning.cleanings_in_period}
                missed={s.soiling_and_cleaning.missed}
              />
              <div className="mt-3 grid gap-2 sm:grid-cols-3">
                <Stat icon={<CalendarCheck2 size={14} />} label="Last cleaning" value={s.soiling_and_cleaning.last_cleaning} />
                <Stat icon={<Timer size={14} />} label="Next scheduled" value={s.soiling_and_cleaning.next_scheduled} />
                <Stat
                  icon={<CalendarX2 size={14} />}
                  label="Missed cleanings"
                  value={s.soiling_and_cleaning.missed.length ? s.soiling_and_cleaning.missed.map((m: any) => m.scheduled).join(", ") : "none"}
                  alert={s.soiling_and_cleaning.missed.length > 0}
                />
              </div>
              <p className="mt-2 text-[11.5px] text-ink-4">{s.soiling_and_cleaning.note}</p>
            </Panel>
            <Panel className="xl:col-span-5" title="Curtailment log" subtitle="SLDC backdown instructions — uncontrollable, compensated under the PPA" bodyClass="p-0">
              {s.curtailment_log.items.length === 0 ? (
                <EmptyState title="No curtailment this month" />
              ) : (
                <table className="tbl">
                  <thead>
                    <tr>
                      <th>Window (IST)</th>
                      <th className="text-right">Setpoint</th>
                      <th className="text-right">Lost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {s.curtailment_log.items.map((c: any) => (
                      <tr key={c.id}>
                        <td className="num">
                          {c.start} → {c.end?.slice(11)}
                        </td>
                        <td className="num text-right">{c.setpoint_mw} MW</td>
                        <td className="num text-right font-medium text-ink">{c.lost_display}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Panel>
          </div>
          <PageFooter items={[`Plant ${data.meta.plant_id}`, data.meta.mode.label, `Period ${monthLabel(period ?? data.meta.period)}`, "Availability provisional until the annual assessment"]} />
        </div>
      )}
    </AppShell>
  );
}

function Stat({ icon, label, value, alert }: { icon: React.ReactNode; label: string; value: string; alert?: boolean }) {
  return (
    <div className={`rounded-md border px-3 py-2 ${alert ? "border-critical/30 bg-critical-bg" : "border-line bg-steel-50"}`}>
      <p className={`flex items-center gap-1.5 text-[10.5px] font-medium uppercase tracking-wider ${alert ? "text-critical-ink" : "text-ink-4"}`}>
        {icon}
        {label}
      </p>
      <p className={`num mt-0.5 text-[13px] font-medium ${alert ? "text-critical-ink" : "text-ink-2"}`}>{value}</p>
    </div>
  );
}

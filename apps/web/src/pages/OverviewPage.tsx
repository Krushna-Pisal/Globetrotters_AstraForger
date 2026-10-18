import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Activity, ArrowRight, Check, Database, Landmark, Wrench, X, Zap } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { NAV } from "../components/AppShell";
import { Loading, ModeBadge, Notice, Panel, SourceBadge } from "../components/ui";
import { api, qs } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useScope } from "../lib/hooks";
import { monthLabel, titleCase } from "../lib/format";

const LENS_CARDS = [
  { to: "/engineer", lens: "engineer", title: "Engineering", icon: Activity, q: "Is the plant physically healthy? Which component underperforms?", against: "Weather-adjusted expected output", unit: "kWh" },
  { to: "/operations", lens: "operations", title: "Operations", icon: Wrench, q: "What do I fix first today? Is the contractor meeting its SLA?", against: "Expected output + O&M guarantee", unit: "MWh" },
  { to: "/cfo", lens: "cfo", title: "Finance", icon: Landmark, q: "Is the investment case holding? Is the debt safe?", against: "Frozen P50 / P90 and covenants", unit: "GWh · ₹" },
] as const;

export default function OverviewPage() {
  const { session, can } = useAuth();
  const { dataset, search, set } = useScope();
  const { data, isLoading } = useQuery({
    queryKey: ["overview", dataset?.id, session?.username],
    queryFn: () => api<any>(`/v1/overview?${qs({ dataset_id: dataset!.id })}`, { token: session?.token }),
    enabled: !!session && !!dataset,
  });
  const allowed = new Set(NAV.filter((n) => can(...n.roles)).map((n) => n.to));

  return (
    <AppShell title="Plant overview" decision="One asset, one evidence chain — each role reads the truth it needs.">
      {isLoading || !data ? (
        <Loading />
      ) : (
        <div className="space-y-4">
          <section className="card overflow-hidden">
            <div className="grid lg:grid-cols-[1.25fr_1fr]">
              <div className="p-5">
                <div className="flex flex-wrap items-center gap-2">
                  <ModeBadge kind={data.dataset.mode.kind} label={data.dataset.mode.label} />
                  <span className="text-[12px] text-ink-3">
                    {data.dataset.periods.length} months · {monthLabel(data.dataset.periods[0])} – {monthLabel(data.dataset.periods.at(-1))}
                  </span>
                </div>
                <h2 className="mt-3 text-[20px] font-semibold tracking-tight">{data.plant.name}</h2>
                <p className="mt-1 max-w-xl text-[13px] leading-relaxed text-ink-3">
                  {data.plant.synthetic
                    ? "Fictional plant on real 2024 reanalysis weather. Faults, soiling, curtailment and contracts are injected from a seeded, labelled scenario; the engines re-detect them from telemetry and are scored against ground truth."
                    : "Real inverter-level telemetry from an Indian plant. Detected symptoms are reported as suspected; nothing is invented, and there is no contract or money for this slice."}
                </p>
                <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
                  {data.plant.facts.map((f: any) => (
                    <div key={f.label}>
                      <dt className="label">{f.label}</dt>
                      <dd className="mt-0.5 text-[13.5px] font-medium text-ink">{f.value}</dd>
                    </div>
                  ))}
                </dl>
              </div>
              <div className="border-t border-line bg-steel-50 p-5 lg:border-l lg:border-t-0">
                <p className="label">Detected events in dataset</p>
                <div className="mt-3 grid grid-cols-2 gap-2">
                  {Object.entries(data.events_by_category).map(([k, v]) => (
                    <div key={k} className="rounded-lg border border-line bg-surface px-3 py-2">
                      <p className="text-[22px] font-semibold leading-tight text-ink">{String(v)}</p>
                      <p className="text-[12px] text-ink-3">{titleCase(k)}</p>
                    </div>
                  ))}
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {(session?.role === "presenter" ? ["thar1_demo_2024", "kaggle_p2_2020"] : []).map((d) => (
                    <button key={d} className={d === dataset?.id ? "btn-primary" : "btn-ghost"} onClick={() => set({ dataset: d })}>
                      <Database size={13} /> {d === "thar1_demo_2024" ? "Synthetic year" : "Real Kaggle slice"}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <div className="grid gap-4 md:grid-cols-3">
            {LENS_CARDS.map((c) => {
              const ok = allowed.has(c.to);
              const body = (
                <>
                  <div className="flex items-center justify-between">
                    <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
                      <c.icon size={18} />
                    </span>
                    {ok ? <ArrowRight size={16} className="text-ink-4 transition group-hover:translate-x-0.5 group-hover:text-brand-600" /> : <span className="text-[11px] text-ink-4">other role</span>}
                  </div>
                  <p className="mt-3 text-[15px] font-semibold text-ink">{c.title}</p>
                  <p className="mt-1 text-[13px] text-ink-3">{c.q}</p>
                  <p className="mt-3 text-[11.5px] text-ink-4">
                    Compares against <span className="text-ink-2">{c.against}</span> · units {c.unit}
                  </p>
                </>
              );
              return ok ? (
                <Link key={c.to} to={`${c.to}?${search}`} className="card group p-4 transition hover:border-brand-500">
                  {body}
                </Link>
              ) : (
                <div key={c.to} className="card p-4 opacity-60">
                  {body}
                </div>
              );
            })}
          </div>

          {data.lens_verdicts && (
            <Panel
              title="Three truths, month by month"
              subtitle={data.lens_verdicts.rule}
              actions={<span className="text-[11.5px] text-ink-4">Presenter only</span>}
              bodyClass="p-0"
            >
              <div className="overflow-x-auto">
                <table className="tbl">
                  <thead>
                    <tr>
                      <th>Month</th>
                      <th>Engineer · physics</th>
                      <th>Operations · availability</th>
                      <th>CFO · revenue vs P50</th>
                      <th>Lenses</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.lens_verdicts.months.map((m: any) => (
                      <tr key={m.month}>
                        <td className="font-medium text-ink">
                          <button className="hover:text-brand-600 hover:underline" onClick={() => set({ period: m.month })}>
                            {monthLabel(m.month)}
                          </button>
                        </td>
                        {(["engineer", "operations", "cfo"] as const).map((l) => (
                          <td key={l}>
                            <span className="inline-flex items-center gap-1.5">
                              {m[l].ok ? <Check size={15} className="text-good" /> : <X size={15} className="text-critical" />}
                              <span className="num text-ink-2">{m[l].display}</span>
                            </span>
                          </td>
                        ))}
                        <td>
                          {m.diverge ? (
                            <span className="rounded bg-warning-bg px-1.5 py-0.5 text-[11px] font-semibold text-warning-ink">Diverge</span>
                          ) : (
                            <span className="text-[11px] text-ink-4">agree</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="border-t border-line px-4 py-2 text-[11.5px] text-ink-4">{data.lens_verdicts.note}</p>
            </Panel>
          )}

          <Panel title="Data provenance" subtitle="Every source recorded with its hash; synthetic and measured data never share a dataset" bodyClass="p-0">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Kind</th>
                  <th>SHA-256</th>
                  <th>Licence</th>
                </tr>
              </thead>
              <tbody>
                {data.sources.map((s: any) => (
                  <tr key={s.name}>
                    <td className="font-medium text-ink">
                      <span className="inline-flex items-center gap-1.5">
                        <Zap size={13} className="text-ink-4" />
                        {s.name}
                      </span>
                    </td>
                    <td>
                      <SourceBadge kind={s.source_kind} />
                    </td>
                    <td className="font-mono text-[12px]">{s.sha256}…</td>
                    <td className="text-ink-3">{s.license || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
          {!data.plant.synthetic && (
            <Notice>The Kaggle licence text is still to be verified by a human (docs/00); the manifest records it as unverified.</Notice>
          )}
        </div>
      )}
    </AppShell>
  );
}

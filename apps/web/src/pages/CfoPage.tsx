import { ArrowUpRight, Layers, Lock, Repeat2, Scale, TriangleAlert } from "lucide-react";
import { Link } from "react-router-dom";
import { AppShell, PageFooter } from "../components/AppShell";
import { DscrChart, EnergyVsP50Chart, RevenueChart } from "../components/charts/charts";
import { EmptyState, Loading, Notice, OmissionsPanel, Panel, ProvisionalBadge, TileRow } from "../components/ui";
import { useLensView, useScope } from "../lib/hooks";
import { monthLabel, titleCase } from "../lib/format";

const RULE_ICON: Record<string, typeof Repeat2> = { recurrence: Repeat2, materiality: Scale, covenant: TriangleAlert };

export default function CfoPage() {
  const { data, isLoading, error } = useLensView("cfo");
  const { search } = useScope();
  const s = data?.sections;
  const esc = data?.escalations;

  return (
    <AppShell title="Finance" decision={data?.decision ?? "Is the investment case holding, and is the debt safe?"}>
      {isLoading && <Loading />}
      {error && <Notice tone="warn">{String((error as Error).message)}</Notice>}
      {data && s?.unavailable && (
        <div className="space-y-4">
          <div className="card">
            <EmptyState title="No investment case for this dataset">{s.unavailable}</EmptyState>
          </div>
          <OmissionsPanel omitted={data.omitted} stripped={data.stripped} lens="cfo" />
        </div>
      )}
      {data && s && !s.unavailable && (
        <div className="space-y-4">
          {data.meta.provisional && (
            <Notice>
              Period-to-date money is <b>provisional until year close</b>: excess, shortfall and grid compensation are settled in the
              December true-up.
            </Notice>
          )}
          <TileRow tiles={data.tiles} />

          <div className="grid gap-4 xl:grid-cols-2">
            <Panel title="Delivered energy vs the investment case" subtitle="GWh per month · accountable energy at the delivery-point meter vs frozen P50 / P90">
              <EnergyVsP50Chart s={s.energy_vs_p50_p90} current={data.meta.period} />
            </Panel>
            <Panel title="Settled revenue vs P50 case" subtitle="₹ crore per month · PPA settlement never reads the baseline; the comparison is made here">
              <RevenueChart s={s.revenue_vs_baseline} current={data.meta.period} />
            </Panel>
          </div>

          <div className="grid gap-4 xl:grid-cols-12">
            <Panel
              className="xl:col-span-5"
              title="Escalations"
              subtitle={`As of ${monthLabel(esc.as_of)} · materiality threshold ${esc.threshold_display} annualised`}
            >
              {esc.items.length === 0 ? (
                <EmptyState title="Nothing material this period">
                  Individual events stay below the CFO view until they recur or cross materiality.
                </EmptyState>
              ) : (
                <ul className="space-y-2.5">
                  {esc.items.map((e: any) => {
                    const Icon = RULE_ICON[e.rule] ?? Layers;
                    return (
                      <li key={e.cause_code + e.rule} className="rounded-lg border border-serious/40 bg-serious-bg/60 p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-start gap-2.5">
                            <span className="mt-0.5 flex h-7 w-7 items-center justify-center rounded-md bg-white text-serious-ink shadow-card">
                              <Icon size={15} />
                            </span>
                            <div>
                              <p className="text-[13.5px] font-semibold text-ink">
                                {e.label} · <span className="font-mono">{e.cause_code}</span>
                              </p>
                              <p className="text-[12px] text-ink-3">{e.why}</p>
                            </div>
                          </div>
                          <span className="whitespace-nowrap text-[15px] font-semibold text-ink">{e.annualised_display}</span>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 pl-9 text-[12px] text-ink-2">
                          <span>
                            Months: <b className="num">{e.periods_hit.map(monthLabel).join(", ")}</b>
                          </span>
                          <span>
                            Assets: <b>{e.assets_count}</b>
                          </span>
                          <span>
                            Bearer: <b>{titleCase(e.bearer)}</b>
                          </span>
                        </div>
                        <p className="mt-1.5 flex items-center gap-1 pl-9 text-[12.5px] font-medium text-serious-ink">
                          <ArrowUpRight size={13} /> {e.recommended_action}
                        </p>
                      </li>
                    );
                  })}
                </ul>
              )}
              {esc.below_threshold.length > 0 && (
                <details className="mt-3 rounded-md border border-line bg-steel-50 px-3 py-2 text-[12px] text-ink-3">
                  <summary className="cursor-pointer font-medium text-ink-2">
                    {esc.below_threshold.length} cause{esc.below_threshold.length > 1 ? "s" : ""} below the threshold (not escalated)
                  </summary>
                  <ul className="mt-2 space-y-1">
                    {esc.below_threshold.map((b: any) => (
                      <li key={b.cause_code} className="flex justify-between gap-2">
                        <span className="font-mono">{b.cause_code}</span>
                        <span>{b.why}</span>
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </Panel>
            <Panel
              className="xl:col-span-7"
              title="Debt service coverage vs covenants"
              subtitle="Year-to-date DSCR = Σ CFADS ÷ Σ debt service · annual test at year end"
              actions={s.dscr_vs_covenants.provisional ? <ProvisionalBadge /> : undefined}
            >
              <DscrChart s={s.dscr_vs_covenants} current={data.meta.period} />
            </Panel>
          </div>

          <div className="grid items-start gap-4 xl:grid-cols-12">
            <Panel className="xl:col-span-7" title="PPA settlement lines" subtitle={s.settlement_lines.note} bodyClass="p-0">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Clause</th>
                    <th>Line</th>
                    <th>Period</th>
                    <th className="text-right">Quantity</th>
                    <th className="text-right">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {s.settlement_lines.items.map((l: any) => (
                    <tr key={l.clause + l.period}>
                      <td className="font-mono text-[12.5px] font-medium text-ink">{l.clause}</td>
                      <td>
                        {l.label} {l.provisional && <ProvisionalBadge />}
                      </td>
                      <td className="text-ink-3">{l.period === "year" ? "Annual true-up" : "Monthly"}</td>
                      <td className="num text-right">{l.qty_display}</td>
                      <td className="num text-right font-semibold text-ink">{l.amount_display}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Panel>
            <Panel className="xl:col-span-5" title={`Cash flow available for debt service · ${monthLabel(s.cashflow.month)}`} subtitle="After tax and capex — not EBITDA" bodyClass="p-0">
              <table className="tbl">
                <tbody>
                  {s.cashflow.rows.map((r: any) => (
                    <tr key={r.label} className={r.total ? "[&>td]:bg-steel-50 [&>td]:font-semibold [&>td]:text-ink" : ""}>
                      <td>{r.label}</td>
                      <td className="num text-right">{r.display}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Panel>
          </div>

          <div className="card flex flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 text-[12.5px] text-ink-2">
            <span className="flex items-center gap-2 font-semibold text-ink">
              <Lock size={14} className="text-brand-600" /> Baseline v{s.baseline.version} · frozen
            </span>
            <span>P50 {s.baseline.p50_annual_display}</span>
            <span>P90 {s.baseline.p90_annual_display}</span>
            <span>Revenue case {s.baseline.revenue_p50_display}</span>
            <span>Weather basis {s.baseline.weather_basis}</span>
            <span>
              Approved by {s.baseline.approved_by} on {s.baseline.approved_at}
            </span>
            <Link to={`/baseline?${search}`} className="ml-auto font-medium text-brand-600 hover:underline">
              Version history →
            </Link>
          </div>

          <OmissionsPanel omitted={data.omitted} stripped={data.stripped} lens="cfo" />
          <PageFooter
            items={[
              `Plant ${data.meta.plant_id}`,
              data.meta.mode.label,
              `Period ${monthLabel(data.meta.period)}`,
              `Baseline v${data.meta.baseline_version}`,
              data.meta.provisional ? "Provisional until year close" : "Year closed",
            ]}
          />
        </div>
      )}
    </AppShell>
  );
}

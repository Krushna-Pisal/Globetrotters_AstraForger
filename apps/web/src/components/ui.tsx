import type { ReactNode } from "react";
import {
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  CircleDot,
  Info,
  Loader2,
} from "lucide-react";
import type { MetricCard } from "../lib/types";

/* ------------------------------------------------------------------ brand */
export function BrandMark({ size = 28 }: { size?: number }) {
  // Sun over a fixed-tilt array: a plain signifier, drawn in the control-room blue.
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="#0d366b" />
      <circle cx="22" cy="9.5" r="3.6" fill="#fab219" />
      <path d="M5 25 L11 14 H27 L21 25 Z" fill="#2a78d6" />
      <path d="M8 19.5 H24 M13.2 14 L8.6 25 M18.6 14 L14 25" stroke="#cde2fb" strokeWidth="1.1" fill="none" />
    </svg>
  );
}

/* ------------------------------------------------------------------ status */
const STATUS = {
  ok: { icon: CheckCircle2, ring: "border-l-good", ink: "text-good-ink", bg: "bg-good-bg", label: "On target" },
  warn: { icon: AlertTriangle, ring: "border-l-warning", ink: "text-warning-ink", bg: "bg-warning-bg", label: "Watch" },
  alert: { icon: AlertOctagon, ring: "border-l-critical", ink: "text-critical-ink", bg: "bg-critical-bg", label: "Off target" },
  info: { icon: CircleDot, ring: "border-l-steel-300", ink: "text-ink-3", bg: "bg-steel-100", label: "" },
} as const;

export function StatusPill({ status, children }: { status: keyof typeof STATUS; children?: ReactNode }) {
  const s = STATUS[status];
  const Icon = s.icon;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${s.bg} ${s.ink}`}>
      <Icon size={12} strokeWidth={2.2} />
      {children ?? s.label}
    </span>
  );
}

const SOURCE: Record<string, string> = {
  measured: "Measured",
  modeled: "Modeled",
  derived: "Derived",
  synthetic_scenario: "Synthetic",
  weather_estimated: "Reanalysis",
  synthetic_reference: "Baseline",
  synthetic_contract: "Contract",
  operator: "Operator",
};

export function SourceBadge({ kind }: { kind: string }) {
  return (
    <span className="rounded border border-line px-1.5 py-px text-[10px] font-medium uppercase tracking-wider text-ink-3">
      {SOURCE[kind] ?? kind}
    </span>
  );
}

export function ProvisionalBadge() {
  return (
    <span
      title="Provisional until the December true-up"
      className="rounded border border-warning/60 bg-warning-bg px-1.5 py-px text-[10px] font-semibold uppercase tracking-wider text-warning-ink"
    >
      Provisional
    </span>
  );
}

export function ModeBadge({ kind, label }: { kind: string; label: string }) {
  const synthetic = kind.startsWith("synthetic");
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] font-semibold tracking-wide ${
        synthetic ? "border-warning/70 bg-warning-bg text-warning-ink" : "border-good/50 bg-good-bg text-good-ink"
      }`}
      title={synthetic ? "Synthetic scenario on real 2024 weather — labelled, seeded, scored" : "Real measured telemetry"}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${synthetic ? "bg-warning" : "bg-good"}`} />
      {label}
    </span>
  );
}

/* ------------------------------------------------------------------ KPI tile */
export function KpiTile({ m }: { m: MetricCard }) {
  const s = STATUS[m.status];
  const delta = m.compare?.delta_pct;
  const long = m.display.length > 10;
  return (
    <div className={`card flex min-h-[124px] flex-col border-l-[3px] ${s.ring} px-4 py-3`}>
      <span className="label leading-snug">{m.label}</span>
      <span className={`mt-1.5 whitespace-nowrap font-semibold leading-tight tracking-tight text-ink ${long ? "text-[19px]" : "text-[26px]"}`}>{m.display}</span>
      <div className="mt-1 flex flex-wrap items-center gap-x-2 text-[12px] leading-snug text-ink-3">
        {delta !== undefined && delta !== null && (
          <span className={`num font-medium ${delta >= 0 ? "text-good-ink" : "text-critical-ink"}`}>
            {delta >= 0 ? "▲" : "▼"} {Math.abs(delta).toFixed(1)} %
          </span>
        )}
        {m.hint && <span>{m.hint}</span>}
      </div>
      <div className="mt-auto flex flex-wrap items-center gap-1.5 pt-2">
        {m.status !== "info" && <StatusPill status={m.status} />}
        <SourceBadge kind={m.source_kind} />
        {m.provisional && <ProvisionalBadge />}
      </div>
      {m.chip && <p className="mt-1.5 truncate text-[11px] text-ink-4" title={m.chip}>{m.chip}</p>}
    </div>
  );
}

export function TileRow({ tiles }: { tiles: MetricCard[] }) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      {tiles.map((t, i) => (
        <KpiTile key={`${t.metric_id}-${i}`} m={t} />
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ panels */
export function Panel({
  title,
  subtitle,
  actions,
  children,
  className = "",
  bodyClass = "p-4",
}: {
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClass?: string;
}) {
  return (
    <section className={`card flex flex-col ${className}`}>
      <header className="card-head">
        <div className="min-w-0">
          <h2 className="card-title">{title}</h2>
          {subtitle && <p className="mt-0.5 text-[12px] text-ink-3">{subtitle}</p>}
        </div>
        {actions}
      </header>
      <div className={`min-h-0 flex-1 ${bodyClass}`}>{children}</div>
    </section>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-10 text-center">
      <Info size={22} className="text-ink-4" />
      <p className="font-medium text-ink-2">{title}</p>
      {children && <p className="max-w-md text-[13px] text-ink-3">{children}</p>}
    </div>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-ink-3">
      <Loader2 className="animate-spin" size={18} /> {label}…
    </div>
  );
}

export function Notice({ tone = "info", children }: { tone?: "info" | "warn"; children: ReactNode }) {
  return (
    <div
      className={`flex items-start gap-2 rounded-lg border px-3 py-2 text-[12.5px] ${
        tone === "warn" ? "border-warning/60 bg-warning-bg text-warning-ink" : "border-brand-100 bg-brand-50 text-brand-800"
      }`}
    >
      <Info size={14} className="mt-0.5 shrink-0" />
      <div>{children}</div>
    </div>
  );
}

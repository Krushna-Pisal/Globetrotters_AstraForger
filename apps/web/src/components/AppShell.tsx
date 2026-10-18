import { useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import {
  Activity,
  ChevronLeft,
  ChevronRight,
  Factory,
  Gauge,
  Landmark,
  LayoutDashboard,
  Lock,
  LogOut,
  Wrench,
} from "lucide-react";
import { ROLE_LABEL, useAuth } from "../lib/auth";
import { useScope } from "../lib/hooks";
import { monthLabel } from "../lib/format";
import type { Role } from "../lib/api";
import { BrandMark, ModeBadge } from "./ui";

type NavItem = { to: string; label: string; icon: typeof Gauge; roles: Role[]; caption: string };
export const NAV: NavItem[] = [
  { to: "/overview", label: "Plant overview", icon: LayoutDashboard, roles: ["engineer", "operations", "cfo"], caption: "Asset & data" },
  { to: "/engineer", label: "Engineering", icon: Activity, roles: ["engineer"], caption: "Physics vs expected" },
  { to: "/operations", label: "Operations", icon: Wrench, roles: ["operations"], caption: "Work queue & SLA" },
  { to: "/cfo", label: "Finance", icon: Landmark, roles: ["cfo"], caption: "Investment case & debt" },
  { to: "/baseline", label: "Baseline history", icon: Lock, roles: ["cfo"], caption: "Frozen P50 / P90" },
];

export function AppShell({ title, decision, children }: { title: string; decision?: string; children: ReactNode }) {
  const { session, logout, can } = useAuth();
  const { datasets, dataset, period, set, search } = useScope();
  const loc = useLocation();
  const [menu, setMenu] = useState(false);
  const periods = dataset?.periods ?? [];
  const idx = period ? periods.indexOf(period) : -1;

  return (
    <div className="flex h-full">
      <aside className="hidden w-[248px] shrink-0 flex-col border-r border-line bg-surface lg:flex">
        <div className="flex items-center gap-2.5 border-b border-line px-5 py-4">
          <BrandMark />
          <div className="leading-tight">
            <p className="text-[14px] font-semibold text-ink">Three Truths</p>
            <p className="text-[11px] text-ink-3">Performance assurance</p>
          </div>
        </div>
        <nav className="flex-1 space-y-0.5 px-3 py-4">
          <p className="label px-2 pb-2">Views</p>
          {NAV.filter((n) => can(...n.roles)).map((n) => (
            <NavLink
              key={n.to}
              to={`${n.to}?${search}`}
              className={({ isActive }) =>
                `group flex items-center gap-3 rounded-lg px-2.5 py-2 transition ${
                  isActive ? "bg-brand-50 text-brand-700" : "text-ink-2 hover:bg-steel-50"
                }`
              }
            >
              <n.icon size={17} strokeWidth={1.9} />
              <span className="flex flex-col leading-tight">
                <span className="text-[13.5px] font-medium">{n.label}</span>
                <span className="text-[11px] text-ink-4">{n.caption}</span>
              </span>
            </NavLink>
          ))}
        </nav>
        <div className="m-3 rounded-lg border border-line bg-steel-50 p-3">
          <div className="flex items-center gap-2 text-ink-2">
            <Factory size={15} />
            <span className="text-[12.5px] font-semibold">{dataset?.plant_id === "KGL-P2" ? "Kaggle Plant 2" : "Thar-1"}</span>
          </div>
          <p className="mt-1 text-[11.5px] leading-snug text-ink-3">
            {dataset?.plant_id === "KGL-P2"
              ? "Real inverter telemetry · 22 inverters · India · May–Jun 2020"
              : "60 MWp / 50 MW AC · 20 inverters · Bhadla, Rajasthan (fictional)"}
          </p>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 border-b border-line bg-surface/95 backdrop-blur">
          <div className="flex flex-wrap items-center gap-3 px-5 py-2.5 lg:px-7">
            <div className="flex items-center gap-2 lg:hidden">
              <BrandMark size={24} />
            </div>
            <div className="flex items-center gap-2">
              <span className="label hidden sm:inline">Dataset</span>
              <select
                className="select"
                value={dataset?.id ?? ""}
                onChange={(e) => set({ dataset: e.target.value })}
                aria-label="Dataset"
              >
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.plant_id === "THAR1" ? "Thar-1 · 2024 scenario" : "Kaggle Plant 2 · 2020 measured"}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-1">
              <span className="label mr-1 hidden sm:inline">Period</span>
              <button
                className="btn-ghost px-1.5"
                aria-label="Previous month"
                disabled={idx <= 0}
                onClick={() => set({ period: periods[idx - 1] })}
              >
                <ChevronLeft size={15} />
              </button>
              <select className="select" value={period ?? ""} onChange={(e) => set({ period: e.target.value })} aria-label="Period">
                {periods.map((p) => (
                  <option key={p} value={p}>
                    {monthLabel(p)}
                  </option>
                ))}
              </select>
              <button
                className="btn-ghost px-1.5"
                aria-label="Next month"
                disabled={idx < 0 || idx >= periods.length - 1}
                onClick={() => set({ period: periods[idx + 1] })}
              >
                <ChevronRight size={15} />
              </button>
            </div>
            {dataset && <ModeBadge kind={dataset.mode.kind} label={dataset.mode.label} />}
            <div className="relative ml-auto">
              <button className="flex items-center gap-2.5 rounded-lg px-2 py-1 hover:bg-steel-50" onClick={() => setMenu((v) => !v)}>
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-steel-800 text-[12px] font-semibold uppercase text-white">
                  {session?.username.slice(0, 2)}
                </span>
                <span className="hidden text-left leading-tight sm:block">
                  <span className="block text-[13px] font-medium text-ink">{session?.display_name}</span>
                  <span className="block text-[11px] text-ink-3">{session && ROLE_LABEL[session.role]} lens</span>
                </span>
              </button>
              {menu && (
                <div className="absolute right-0 mt-1 w-56 rounded-lg border border-line bg-surface p-1 shadow-pop" onMouseLeave={() => setMenu(false)}>
                  <div className="px-3 py-2 text-[12px] text-ink-3">
                    Signed in as <span className="font-medium text-ink-2">{session?.username}</span>
                    <br />
                    Plants: {session?.plants.join(", ")}
                  </div>
                  <button className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-[13px] text-ink-2 hover:bg-steel-50" onClick={logout}>
                    <LogOut size={14} /> Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
          <nav className="flex gap-1 overflow-x-auto border-t border-line px-3 py-1.5 lg:hidden">
            {NAV.filter((n) => can(...n.roles)).map((n) => (
              <Link
                key={n.to}
                to={`${n.to}?${search}`}
                className={`whitespace-nowrap rounded-md px-2.5 py-1 text-[12.5px] ${loc.pathname === n.to ? "bg-brand-50 text-brand-700" : "text-ink-2"}`}
              >
                {n.label}
              </Link>
            ))}
          </nav>
        </header>

        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-[1480px] px-5 py-5 lg:px-7">
            <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
              <div>
                <h1 className="text-[22px] font-semibold tracking-tight text-ink">{title}</h1>
                {decision && <p className="mt-0.5 text-[13.5px] text-ink-3">{decision}</p>}
              </div>
            </div>
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

export function PageFooter({ items }: { items: (string | null | undefined)[] }) {
  return (
    <footer className="mt-6 flex flex-wrap gap-x-4 gap-y-1 border-t border-line pt-3 text-[11.5px] text-ink-4">
      {items.filter(Boolean).map((i) => (
        <span key={i}>{i}</span>
      ))}
    </footer>
  );
}

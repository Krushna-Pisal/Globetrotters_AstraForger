import { useQuery } from "@tanstack/react-query";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { getJson, type Health } from "./api/client";
import Placeholder from "./pages/Placeholder";

const PAGES = [
  { path: "/engineer", title: "Engineer", milestone: "M6" },
  { path: "/operations", title: "Operations", milestone: "M6" },
  { path: "/cfo", title: "CFO", milestone: "M6" },
  { path: "/rosetta", title: "Rosetta", milestone: "M7" },
  { path: "/scorecard", title: "Scorecard", milestone: "M7" },
  { path: "/baseline", title: "Baseline history", milestone: "M5" },
];

function ApiStatus() {
  const { data, isError } = useQuery({ queryKey: ["health"], queryFn: () => getJson<Health>("/health") });
  const label = isError ? "API down" : !data ? "API …" : data.db ? "API + DB ok" : "API ok, DB down";
  const ok = !isError && data?.db;
  return (
    <span className={`rounded px-2 py-0.5 text-xs ${ok ? "bg-green-100 text-green-800" : "bg-amber-100 text-amber-800"}`}>
      {label}
    </span>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-white text-slate-900">
      <header className="flex items-center gap-6 border-b px-6 py-3">
        <span className="font-semibold">One Asset, Three Truths</span>
        <nav className="flex gap-4 text-sm">
          {PAGES.map((p) => (
            <NavLink
              key={p.path}
              to={p.path}
              className={({ isActive }) => (isActive ? "font-medium text-slate-900" : "text-slate-500")}
            >
              {p.title}
            </NavLink>
          ))}
        </nav>
        <div className="ml-auto">
          <ApiStatus />
        </div>
      </header>
      <main className="px-6 py-6">
        <Routes>
          <Route path="/" element={<Navigate to="/engineer" replace />} />
          {PAGES.map((p) => (
            <Route key={p.path} path={p.path} element={<Placeholder title={p.title} milestone={p.milestone} />} />
          ))}
        </Routes>
      </main>
    </div>
  );
}

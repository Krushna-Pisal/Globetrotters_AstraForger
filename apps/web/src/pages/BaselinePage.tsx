import { useQuery } from "@tanstack/react-query";
import { Lock, ShieldCheck } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { EmptyState, Loading, Panel, StatusPill } from "../components/ui";
import { api, qs } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useScope } from "../lib/hooks";

const gwh = (kwh: string | null) => (kwh ? `${(Number(kwh) / 1e6).toFixed(2)} GWh` : "—");
const cr = (inr: string | null) => (inr ? `₹${(Number(inr) / 1e7).toFixed(2)} cr` : "—");

export default function BaselinePage() {
  const { session } = useAuth();
  const { dataset } = useScope();
  const plant = dataset?.plant_id ?? "THAR1";
  const { data, isLoading } = useQuery({
    queryKey: ["baseline-versions", plant],
    queryFn: () => api<any[]>(`/v1/baseline/versions?${qs({ plant_id: plant })}`, { token: session?.token }),
    enabled: !!session,
  });

  return (
    <AppShell title="Baseline history" decision="The investment case is frozen once approved. A revision is a new version; old versions stay visible.">
      <Panel
        title="Versions"
        subtitle="Approved rows are immutable in the database (trigger) — PATCH answers 409 baseline_immutable"
        actions={
          <span className="inline-flex items-center gap-1.5 text-[12px] font-medium text-good-ink">
            <ShieldCheck size={14} /> Immutability enforced
          </span>
        }
        bodyClass="p-0"
      >
        {isLoading ? (
          <Loading />
        ) : !data?.length ? (
          <EmptyState title="No baseline for this plant">The Kaggle slice has no investment case.</EmptyState>
        ) : (
          <table className="tbl">
            <thead>
              <tr>
                <th>Version</th>
                <th>Status</th>
                <th className="text-right">P50 energy</th>
                <th className="text-right">P90 energy</th>
                <th className="text-right">Revenue case</th>
                <th>Approved by</th>
                <th>Approved at</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {data.map((v) => (
                <tr key={v.version}>
                  <td className="font-semibold text-ink">
                    <span className="inline-flex items-center gap-1.5">
                      {v.status === "approved" && <Lock size={13} className="text-brand-600" />}v{v.version}
                    </span>
                  </td>
                  <td>
                    <StatusPill status={v.status === "approved" ? "ok" : "warn"}>{v.status}</StatusPill>
                  </td>
                  <td className="num text-right">{gwh(v.p50_kwh)}</td>
                  <td className="num text-right">{gwh(v.p90_kwh)}</td>
                  <td className="num text-right">{cr(v.revenue_p50_inr)}</td>
                  <td>{v.approved_by ?? "—"}</td>
                  <td className="num">{v.approved_at?.slice(0, 16).replace("T", " ") ?? "—"}</td>
                  <td className="text-ink-3">{v.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </AppShell>
  );
}

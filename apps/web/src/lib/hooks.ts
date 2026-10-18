import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { api, qs } from "./api";
import { useAuth } from "./auth";
import type { Dataset, LensPayload } from "./types";

export function useDatasets() {
  const { session } = useAuth();
  return useQuery({
    queryKey: ["datasets", session?.username],
    queryFn: () => api<Dataset[]>("/v1/datasets", { token: session?.token }),
    enabled: !!session,
    staleTime: 5 * 60_000,
  });
}

/** Plant, dataset and period live in the URL so a role switch or a shared link keeps the same context. */
export function useScope() {
  const [params, setParams] = useSearchParams();
  const { data: datasets } = useDatasets();
  const dsId = params.get("dataset") ?? datasets?.[0]?.id ?? null;
  const dataset = datasets?.find((d) => d.id === dsId) ?? datasets?.[0] ?? null;
  const period =
    params.get("period") && dataset?.periods.includes(params.get("period")!)
      ? params.get("period")!
      : (dataset?.default_period ?? null);
  const set = (next: { dataset?: string; period?: string }) => {
    const p = new URLSearchParams(params);
    if (next.dataset) {
      p.set("dataset", next.dataset);
      const d = datasets?.find((x) => x.id === next.dataset);
      p.set("period", next.period ?? d?.default_period ?? "");
    } else if (next.period) {
      p.set("period", next.period);
    }
    setParams(p, { replace: true });
  };
  return { datasets: datasets ?? [], dataset, period, set, search: params.toString() };
}

export function useLensView(lens: "engineer" | "operations" | "cfo") {
  const { session } = useAuth();
  const { dataset, period } = useScope();
  return useQuery({
    queryKey: ["view", lens, dataset?.id, period, session?.username],
    queryFn: () =>
      api<LensPayload>(
        `/v1/view?${qs({ dataset_id: dataset!.id, period: period!, lens: session?.role === "presenter" ? lens : undefined })}`,
        { token: session?.token },
      ),
    enabled: !!session && !!dataset && !!period,
    placeholderData: (prev) => (prev?.meta.lens.id === lens ? prev : undefined),
  });
}

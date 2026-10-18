// Display formatting only (unit scaling and labels). No metric arithmetic happens in the web app (invariant 6).

export const fmtMWh = (kwh: number) => `${(kwh / 1e3).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
export const fmtGWh = (kwh: number) => `${(kwh / 1e6).toFixed(1)}`;
export const fmtCr = (inr: number) => `${(inr / 1e7).toFixed(2)}`;
export const fmtPct = (x: number, d = 0) => `${(x * 100).toFixed(d)}%`;
export const fmtRatio = (x: number) => x.toFixed(2);

export const monthLabel = (ym: string) => {
  const [y, m] = ym.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, 1)).toLocaleString("en-GB", { month: "short", year: "numeric", timeZone: "UTC" });
};
export const shortMonth = (ym: string) => monthLabel(ym).split(" ")[0];
export const dayLabel = (d: string) => d.slice(8, 10);

export const titleCase = (s: string) => s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

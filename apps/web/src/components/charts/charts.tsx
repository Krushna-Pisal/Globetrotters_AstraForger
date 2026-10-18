import EChart, { baseOption, INK, LOSS, SERIES, xCategory, yValue } from "./EChart";
import { dayLabel, fmtCr, fmtGWh, fmtMWh, fmtPct, fmtRatio, shortMonth } from "../../lib/format";

const tip = (lines: string[]) => lines.join("<br/>");
const dot = (c: string) => `<span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${c};margin-right:6px"></span>`;

/* ---------------------------------------------------------- engineer */
export function DailyEnergyChart({ s }: { s: any }) {
  return (
    <EChart
      option={baseOption({
        xAxis: xCategory(s.days.map(dayLabel)),
        yAxis: yValue((v) => fmtMWh(v)),
        tooltip: {
          ...baseOption({}).tooltip,
          formatter: (ps: any) => {
            const i = ps[0].dataIndex;
            return tip([
              `<b>${s.days[i]}</b>`,
              `${dot(SERIES.s1)}Actual ${fmtMWh(s.actual_kwh[i])} MWh`,
              `${dot(INK.secondary)}Expected ${fmtMWh(s.expected_kwh[i])} MWh`,
              `<span style="color:${INK.muted}">Band ${fmtMWh(s.band_low_kwh[i])}–${fmtMWh(s.band_high_kwh[i])} MWh</span>`,
            ]);
          },
        },
        series: [
          { name: "band-low", type: "line", data: s.band_low_kwh, stack: "band", lineStyle: { opacity: 0 }, symbol: "none", tooltip: { show: false } },
          {
            name: "Expected band (95 %)",
            type: "line",
            data: s.band_span_kwh,
            stack: "band",
            lineStyle: { opacity: 0 },
            symbol: "none",
            areaStyle: { color: "rgba(42,120,214,0.10)" },
            itemStyle: { color: "rgba(42,120,214,0.25)" },
          },
          { name: "Expected", type: "line", data: s.expected_kwh, symbol: "none", lineStyle: { color: INK.secondary, width: 1.5, type: "dashed" }, itemStyle: { color: INK.secondary } },
          { name: "Actual", type: "bar", data: s.actual_kwh, barMaxWidth: 14, itemStyle: { color: SERIES.s1, borderRadius: [3, 3, 0, 0] } },
        ],
        legend: { ...baseOption({}).legend, data: ["Actual", "Expected", "Expected band (95 %)"] },
      })}
    />
  );
}

export function PrTrendChart({ s, current }: { s: any; current: string }) {
  const months = s.months.map(shortMonth);
  return (
    <EChart
      height={250}
      option={baseOption({
        xAxis: xCategory(months),
        yAxis: yValue((v) => fmtPct(v), { min: (v: any) => Math.floor(v.min * 50) / 50, max: (v: any) => Math.ceil(v.max * 50) / 50 }),
        series: [
          { name: "lo", type: "line", data: s.band_low, stack: "b", lineStyle: { opacity: 0 }, symbol: "none", tooltip: { show: false } },
          {
            name: "Expected band",
            type: "line",
            data: s.band_span,
            stack: "b",
            lineStyle: { opacity: 0 },
            symbol: "none",
            areaStyle: { color: "rgba(42,120,214,0.10)" },
            itemStyle: { color: "rgba(42,120,214,0.25)" },
            tooltip: { show: false },
          },
          { name: "Expected PR₂₅", type: "line", data: s.expected_pr_25, symbol: "none", lineStyle: { color: INK.secondary, type: "dashed", width: 1.5 }, itemStyle: { color: INK.secondary } },
          {
            name: "PR₂₅",
            type: "line",
            data: s.pr_25,
            symbolSize: 8,
            lineStyle: { color: SERIES.s1, width: 2 },
            itemStyle: { color: SERIES.s1, borderColor: "#fff", borderWidth: 2 },
            markLine: { symbol: "none", silent: true, lineStyle: { color: INK.axis, type: "solid" }, label: { show: false }, data: [{ xAxis: s.months.indexOf(current) }] },
          },
        ],
        legend: { ...baseOption({}).legend, data: ["PR₂₅", "Expected PR₂₅", "Expected band"] },
        tooltip: { ...baseOption({}).tooltip, valueFormatter: (v: any) => fmtPct(v, 1) },
      })}
    />
  );
}

export function PeerHeatmap({ s }: { s: any }) {
  const data: [number, number, number | null][] = [];
  s.assets.forEach((_: string, a: number) => s.days.forEach((_d: string, d: number) => data.push([d, a, s.ratio[a][d]])));
  return (
    <EChart
      height={Math.max(260, s.assets.length * 17 + 70)}
      option={baseOption({
        grid: { left: 8, right: 70, top: 8, bottom: 8, containLabel: true },
        legend: { show: false },
        tooltip: {
          trigger: "item",
          ...{ backgroundColor: "#fff", borderColor: INK.grid, textStyle: { color: INK.primary, fontSize: 12 } },
          formatter: (p: any) =>
            `<b>${s.assets[p.value[1]]}</b> · ${s.days[p.value[0]]}<br/>Output vs peer median: ${p.value[2] === null ? "no eligible data" : fmtRatio(p.value[2])}`,
        },
        xAxis: { type: "category", data: s.days.map(dayLabel), axisTick: { show: false }, axisLine: { show: false }, axisLabel: { color: INK.muted, interval: 1 } },
        yAxis: { type: "category", data: s.assets, inverse: true, axisTick: { show: false }, axisLine: { show: false }, axisLabel: { color: INK.secondary, fontFamily: '"IBM Plex Mono"' } },
        visualMap: {
          min: 0.8,
          max: 1.05,
          calculable: false,
          orient: "vertical",
          right: 0,
          top: "middle",
          itemHeight: 140,
          text: ["1.05", "0.80"],
          textStyle: { color: INK.muted },
          inRange: { color: ["#d03b3b", "#e8a1a0", "#f0efec", "#9ec5f4", "#2a78d6"] },
        },
        series: [{ type: "heatmap", data, itemStyle: { borderColor: "#fff", borderWidth: 1.5, borderRadius: 2 }, emphasis: { itemStyle: { borderColor: INK.primary } } }],
      })}
    />
  );
}

export function LossWaterfall({ steps, unit = "kWh" }: { steps: any[]; unit?: "kWh" | "MWh" }) {
  // Bar geometry (base offset, bar height) is computed by the server; the chart only draws it.
  const labels = steps.map((s) => s.label);
  const shorts = steps.map((s) => s.short ?? s.label);
  const color = (s: any) =>
    s.kind === "total"
      ? LOSS.total
      : s.bucket === "not_yet_attributed"
        ? LOSS.residual
        : ["equipment_outage", "underperformance"].includes(s.bucket)
          ? LOSS.controllable
          : LOSS.uncontrollable;
  const base = steps.map((s) => s.base_kwh);
  const vals = steps.map((s) => ({
    value: s.bar_kwh,
    itemStyle: {
      color: color(s),
      borderRadius: s.kind === "total" ? [3, 3, 0, 0] : 2,
      decal:
        s.bucket === "not_yet_attributed"
          ? { symbol: "rect", dashArrayX: [1, 0], dashArrayY: [3, 3], rotation: Math.PI / 4, color: "rgba(255,255,255,0.55)" }
          : undefined,
    },
  }));
  const fmt = (v: number) => (unit === "MWh" ? `${fmtMWh(v)} MWh` : `${Math.round(v).toLocaleString("en-IN")} kWh`);
  return (
    <EChart
      height={290}
      option={baseOption({
        legend: { show: false },
        grid: { left: 8, right: 16, top: 16, bottom: 8, containLabel: true },
        xAxis: xCategory(shorts, { axisLabel: { color: INK.muted, interval: 0, fontSize: 10.5, rotate: 28 } }),
        // Axis floor just under the lowest bar so losses of a few MWh are visible next to GWh totals (scaling only).
        yAxis: yValue((v) => fmtMWh(v), {
          min: Math.floor((Math.min(...steps.map((x) => (x.kind === "total" ? x.bar_kwh : x.base_kwh))) * 0.985) / 1000) * 1000,
        }),
        tooltip: {
          ...baseOption({}).tooltip,
          trigger: "item",
          formatter: (p: any) => `<b>${labels[p.dataIndex]}</b><br/>${fmt(steps[p.dataIndex].value_kwh)}`,
        },
        series: [
          { type: "bar", stack: "w", data: base, itemStyle: { color: "transparent" }, tooltip: { show: false }, silent: true },
          // (base bars are invisible offsets supplied by the server)
          { type: "bar", stack: "w", data: vals, barMaxWidth: 46, label: { show: true, position: "top", color: INK.secondary, fontSize: 10.5, formatter: (p: any) => (steps[p.dataIndex].value_kwh / 1e3).toLocaleString("en-IN", { maximumFractionDigits: 1 }) } },
        ],
      })}
    />
  );
}

export function TraceChart({ t }: { t: any }) {
  const x = t.ts.map((s: string) => s.slice(5));
  return (
    <EChart
      height={250}
      option={baseOption({
        xAxis: xCategory(x, { axisLabel: { color: INK.muted, interval: 47, formatter: (v: string) => v.slice(0, 5) } }),
        yAxis: yValue((v) => `${Math.round(v)}`),
        dataZoom: [{ type: "inside" }],
        series: [
          { name: "lo", type: "line", data: t.band_low_kwh, stack: "b", lineStyle: { opacity: 0 }, symbol: "none", tooltip: { show: false } },
          { name: "Expected band", type: "line", data: t.band_span_kwh, stack: "b", lineStyle: { opacity: 0 }, symbol: "none", areaStyle: { color: "rgba(42,120,214,0.10)" }, itemStyle: { color: "rgba(42,120,214,0.25)" }, tooltip: { show: false } },
          { name: "Expected", type: "line", data: t.expected_kwh, symbol: "none", lineStyle: { color: INK.secondary, type: "dashed", width: 1.5 }, itemStyle: { color: INK.secondary } },
          { name: "Actual", type: "line", data: t.actual_kwh, symbol: "none", connectNulls: false, lineStyle: { color: SERIES.s1, width: 2 }, itemStyle: { color: SERIES.s1 }, areaStyle: { color: "rgba(42,120,214,0.08)" } },
        ],
        legend: { ...baseOption({}).legend, data: ["Actual", "Expected", "Expected band"] },
        tooltip: { ...baseOption({}).tooltip, valueFormatter: (v: any) => (v === null || v === undefined ? "no data" : `${Number(v).toFixed(1)} kWh`) },
      })}
    />
  );
}

/* ---------------------------------------------------------- operations */
export function AvailabilityTrend({ s, current }: { s: any; current: string }) {
  return (
    <EChart
      height={230}
      option={baseOption({
        legend: { show: false },
        grid: { left: 8, right: 16, top: 16, bottom: 8, containLabel: true },
        xAxis: xCategory(s.months.map(shortMonth)),
        yAxis: yValue((v) => fmtPct(v, 1), { min: 0.98, max: 1.0 }),
        tooltip: { ...baseOption({}).tooltip, valueFormatter: (v: any) => fmtPct(v, 2) },
        series: [
          {
            name: "Energy availability",
            type: "bar",
            data: s.trend.map((v: number, i: number) => ({
              value: v,
              itemStyle: { color: v >= s.guarantee ? SERIES.s1 : "#d03b3b", opacity: s.months[i] === current ? 1 : 0.55, borderRadius: [3, 3, 0, 0] },
            })),
            barMaxWidth: 22,
            markLine: {
              symbol: "none",
              data: [{ yAxis: s.guarantee }],
              lineStyle: { color: INK.primary, type: "dashed" },
              label: { formatter: "Guarantee 99.0 %", color: INK.secondary, position: "insideEndTop" },
            },
          },
        ],
      })}
    />
  );
}

export function PerformanceIndexChart({ s, cleanings, missed }: { s: any; cleanings: string[]; missed: any[] }) {
  const marks = [
    ...cleanings.filter((c) => s.days.includes(c)).map((c) => ({ name: "cleaned", xAxis: s.days.indexOf(c), lineStyle: { color: "#1baf7a", type: "solid" as const } })),
    ...missed
      .filter((m) => s.days.includes(m.scheduled))
      .map((m) => ({ name: "missed", xAxis: s.days.indexOf(m.scheduled), lineStyle: { color: "#d03b3b", type: "dashed" as const } })),
  ];
  return (
    <EChart
      height={230}
      option={baseOption({
        legend: { show: false },
        grid: { left: 8, right: 16, top: 24, bottom: 8, containLabel: true },
        xAxis: xCategory(s.days.map(dayLabel)),
        yAxis: yValue((v) => v.toFixed(2), { scale: true }),
        tooltip: {
          ...baseOption({}).tooltip,
          formatter: (ps: any) => `<b>${s.days[ps[0].dataIndex]}</b><br/>Actual ÷ expected ${ps[0].value === null ? "—" : Number(ps[0].value).toFixed(3)}`,
        },
        series: [
          {
            name: "Actual ÷ expected",
            type: "line",
            data: s.values,
            symbol: "circle",
            symbolSize: 5,
            lineStyle: { color: SERIES.s1, width: 2 },
            itemStyle: { color: SERIES.s1 },
            markLine: { symbol: "none", silent: true, label: { color: INK.secondary, fontSize: 10, formatter: (p: any) => p.name }, data: marks },
          },
        ],
      })}
    />
  );
}

/* ---------------------------------------------------------- cfo */
export function EnergyVsP50Chart({ s, current }: { s: any; current: string }) {
  return (
    <EChart
      height={270}
      option={baseOption({
        xAxis: xCategory(s.months.map(shortMonth)),
        yAxis: yValue((v) => fmtGWh(v)),
        tooltip: { ...baseOption({}).tooltip, valueFormatter: (v: any) => `${fmtGWh(v)} GWh` },
        series: [
          {
            name: "Delivered (accountable)",
            type: "bar",
            data: s.accountable_kwh.map((v: number, i: number) => ({ value: v, itemStyle: { opacity: s.months[i] === current ? 1 : 0.6 } })),
            barMaxWidth: 22,
            itemStyle: { color: SERIES.s1, borderRadius: [3, 3, 0, 0] },
          },
          { name: "P50 (baseline)", type: "line", data: s.p50_kwh, symbolSize: 7, lineStyle: { color: SERIES.s2, width: 2 }, itemStyle: { color: SERIES.s2, borderColor: "#fff", borderWidth: 1.5 } },
          { name: "P90", type: "line", data: s.p90_kwh, symbol: "none", lineStyle: { color: SERIES.s3, width: 2, type: "dashed" }, itemStyle: { color: SERIES.s3 } },
        ],
      })}
    />
  );
}

export function RevenueChart({ s, current }: { s: any; current: string }) {
  return (
    <EChart
      height={270}
      option={baseOption({
        xAxis: xCategory(s.months.map(shortMonth)),
        yAxis: yValue((v) => fmtCr(v)),
        tooltip: { ...baseOption({}).tooltip, valueFormatter: (v: any) => `₹${fmtCr(v)} cr` },
        series: [
          {
            name: "Settled revenue",
            type: "bar",
            data: s.settled_inr.map((v: number, i: number) => ({ value: v, itemStyle: { opacity: s.months[i] === current ? 1 : 0.6 } })),
            barMaxWidth: 22,
            itemStyle: { color: SERIES.s1, borderRadius: [3, 3, 0, 0] },
          },
          { name: "P50 revenue case", type: "line", data: s.baseline_inr, symbolSize: 7, lineStyle: { color: SERIES.s2, width: 2 }, itemStyle: { color: SERIES.s2, borderColor: "#fff", borderWidth: 1.5 } },
        ],
      })}
    />
  );
}

export function DscrChart({ s, current }: { s: any; current: string }) {
  const line = (y: number, label: string, color: string) => ({ yAxis: y, label: { formatter: `${label} ${y.toFixed(2)}×`, color, position: "insideEndTop" as const }, lineStyle: { color, type: "dashed" as const } });
  return (
    <EChart
      height={250}
      option={baseOption({
        legend: { show: false },
        grid: { left: 8, right: 16, top: 16, bottom: 8, containLabel: true },
        xAxis: xCategory(s.months.map(shortMonth)),
        yAxis: yValue((v) => `${v.toFixed(2)}×`, { min: 1.0, max: (v: any) => Math.max(1.5, Math.ceil(v.max * 10) / 10) }),
        tooltip: { ...baseOption({}).tooltip, valueFormatter: (v: any) => `${Number(v).toFixed(3)}×` },
        series: [
          {
            name: "DSCR (YTD)",
            type: "line",
            data: s.dscr_ytd,
            symbolSize: (_v: any, p: any) => (s.months[p.dataIndex] === current ? 11 : 7),
            lineStyle: { color: SERIES.s1, width: 2 },
            itemStyle: { color: SERIES.s1, borderColor: "#fff", borderWidth: 2 },
            markLine: { symbol: "none", silent: true, data: [line(s.sizing, "Sizing", INK.secondary), line(s.lockup, "Lock-up", "#9a3d14"), line(s.default, "Default", "#9f1f1f")] },
          },
        ],
      })}
    />
  );
}

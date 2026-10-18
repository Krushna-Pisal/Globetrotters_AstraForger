import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";

// Shared chrome: recessive axes and hairline grid, sans labels, tabular tooltips (dataviz marks & anatomy).
export const INK = { primary: "#101826", secondary: "#3b4656", muted: "#6b7686", grid: "#e2e6ec", axis: "#c9d0da" };
export const SERIES = { s1: "#2a78d6", s2: "#eb6834", s3: "#1baf7a" };
export const LOSS = { controllable: "#eb6834", uncontrollable: "#6250d6", residual: "#898781", total: "#4a5668" };

const FONT = '"IBM Plex Sans", system-ui, sans-serif';

export function baseOption(extra: EChartsOption): EChartsOption {
  return {
    animationDuration: 300,
    textStyle: { fontFamily: FONT, color: INK.secondary, fontSize: 11 },
    grid: { left: 8, right: 16, top: 36, bottom: 8, containLabel: true },
    legend: { top: 0, left: 0, icon: "roundRect", itemWidth: 12, itemHeight: 4, textStyle: { color: INK.secondary } },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#ffffff",
      borderColor: INK.grid,
      textStyle: { color: INK.primary, fontFamily: FONT, fontSize: 12 },
      extraCssText: "box-shadow: 0 8px 24px rgba(16,24,38,.12); border-radius: 8px; font-variant-numeric: tabular-nums;",
      axisPointer: { type: "line", lineStyle: { color: INK.axis } },
    },
    ...extra,
  };
}

export const xCategory = (data: string[], extra: object = {}) => ({
  type: "category" as const,
  data,
  axisLine: { lineStyle: { color: INK.axis } },
  axisTick: { show: false },
  axisLabel: { color: INK.muted },
  ...extra,
});

export const yValue = (formatter: (v: number) => string, extra: object = {}) => ({
  type: "value" as const,
  axisLabel: { color: INK.muted, formatter },
  splitLine: { lineStyle: { color: INK.grid } },
  ...extra,
});

export default function EChart({ option, height = 280, onClick }: { option: EChartsOption; height?: number; onClick?: (p: any) => void }) {
  return (
    <ReactECharts
      option={option}
      style={{ height, width: "100%" }}
      notMerge
      opts={{ renderer: "svg" }}
      onEvents={onClick ? { click: onClick } : undefined}
    />
  );
}

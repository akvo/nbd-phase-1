import * as echarts from "echarts";

export type ChartType = "line" | "bar" | "area";

export interface ChartDataPoint {
  date: string;
  value: number;
}

/**
 * Generates reusable, customizable ECharts options based on the specified type.
 * Supports line, bar, and area formats natively with default styling guidelines.
 *
 * @param type The visual type of chart: 'line' | 'bar' | 'area'
 * @param label The name of the metric being measured
 * @param data Historical timeseries dataset
 * @param color Theme color override (defaults to sky-500)
 */
export function getHistoricalChartOptions(
  type: ChartType,
  label: string,
  data: ChartDataPoint[],
  color: string = "#0ea5e9"
): echarts.EChartsOption {
  const isArea = type === "area";
  const actualType = isArea ? "line" : type;

  return {
    tooltip: {
      trigger: "axis",
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      formatter: (params: any) => {
        if (!Array.isArray(params) || params.length === 0) return "";
        const item = params[0];
        return `<div class="font-sans p-1 text-xs">
          <div class="font-bold text-slate-700 mb-0.5">${item.name}</div>
          <div class="flex items-center gap-1.5 text-slate-600">
            <span class="w-2 h-2 rounded-full" style="background-color: ${item.color}"></span>
            <span>${label}: <strong>${item.value}</strong></span>
          </div>
        </div>`;
      },
      backgroundColor: "rgba(255, 255, 255, 0.98)",
      borderColor: "#e2e8f0",
      borderWidth: 1,
      textStyle: { color: "#334155" },
    },
    grid: { left: "10%", right: "10%", top: "15%", bottom: "15%" },
    xAxis: {
      type: "category",
      data: data.map((d) =>
        new Date(d.date).toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        })
      ),
      axisLine: { lineStyle: { color: "#cbd5e1" } },
      axisLabel: { color: "#64748b", fontSize: 10 },
    },
    yAxis: {
      type: "value",
      axisLine: { show: false },
      splitLine: { lineStyle: { color: "#f1f5f9" } },
      axisLabel: { color: "#64748b", fontSize: 10 },
    },
    series: [
      {
        data: data.map((d) => d.value),
        type: actualType,
        smooth: actualType === "line",
        showSymbol: actualType === "line",
        symbolSize: 6,
        color: color,
        lineStyle: { width: 2.5 },
        areaStyle: isArea
          ? {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: `${color}33` }, // ~20% opacity using hex suffix
                { offset: 1, color: `${color}00` }, // ~0% opacity
              ]),
            }
          : undefined,
      },
    ],
  };
}

"use client";

import React, { useState } from "react";
import * as LucideIcons from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "./button";
import { EChartsChart } from "./echarts-chart";
import {
  getHistoricalChartOptions,
  ChartType,
  ChartDataPoint,
} from "@/lib/charts";

export interface CollapsibleChartContainerProps {
  label: string;
  data: ChartDataPoint[];
  type?: ChartType;
  color?: string;
}

export function CollapsibleChartContainer({
  label,
  data,
  type = "area",
  color = "#0ea5e9",
}: CollapsibleChartContainerProps) {
  const t = useTranslations("drawer");
  const [isOpen, setIsOpen] = useState(false);
  const chartOptions = getHistoricalChartOptions(type, label, data, color);

  return (
    <div className="w-full no-print">
      <div className="flex justify-end pr-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsOpen(!isOpen)}
          className="h-7 px-2 text-slate-400 hover:text-[#38B1DD] flex items-center gap-1 text-[10px] font-bold"
        >
          <LucideIcons.TrendingUp className="w-3.5 h-3.5" />
          {isOpen ? t("hideTrend") : t("showTrend")}
        </Button>
      </div>
      {isOpen && (
        <div className="h-36 w-full mt-1 border border-slate-100 rounded-xl bg-slate-50/50 p-2 overflow-hidden">
          {data.length > 0 ? (
            <EChartsChart options={chartOptions} />
          ) : (
            <div className="h-full flex items-center justify-center text-[10px] text-slate-400 italic">
              {t("noHistoricalData")}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

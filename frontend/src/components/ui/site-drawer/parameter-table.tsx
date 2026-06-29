"use client";

import React from "react";
import * as LucideIcons from "lucide-react";
import { CollapsibleChartContainer } from "../collapsible-chart-container";
import { GenericSamplingHistory } from "@/lib/api";
import {
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";

interface MetricEntry {
  value: string | number | boolean | null;
  unit: string | null;
  status: string;
  label: string;
  icon: string | null;
}

interface ParameterTableProps {
  metrics: Record<string, MetricEntry>;
  samplingsHistory: GenericSamplingHistory[];
  t: (key: string) => string;
  tm: (key: string) => string;
}

const DynamicIcon = ({
  name,
  className,
}: {
  name: string | null;
  className?: string;
}) => {
  if (!name) {
    return null
  };
  const IconComponent = LucideIcons[name as keyof typeof LucideIcons] as React.ComponentType<{ className?: string }> | undefined;
  if (!IconComponent) {
    return null
  };
  return <IconComponent className={className} />;
};

const metricKeyToTranslation: Record<string, string> = {
  ph: "ph",
  dissolved_oxygen: "dissolvedOxygen",
  temperature: "temperature",
  water_level: "waterLevel",
  turbidity: "turbidity",
  macroinvertebrate: "macroinvertebrate",
};

const statusToTranslation: Record<string, string> = {
  normal: "normal",
  "flood risk": "floodRisk",
  drought: "drought",
  "abnormal low": "abnormalLow",
  stable: "stable",
};

export function ParameterTable({
  metrics,
  samplingsHistory,
  t,
  tm,
}: ParameterTableProps) {
  return (
    <div className="space-y-3 print-avoid-break">
      <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider">
        {t("parameter")}
      </h3>
      <div className="relative w-full overflow-visible rounded-lg border border-slate-200 bg-white shadow-sm">
        <table className="w-full caption-bottom text-sm">
          <TableHeader>
            <TableRow>
              <TableHead className="text-xs uppercase text-slate-500 font-bold">
                {t("parameter")}
              </TableHead>
              <TableHead className="text-xs uppercase text-slate-500 font-bold">
                {t("value")}
              </TableHead>
              <TableHead className="text-xs uppercase text-slate-500 font-bold text-center">
                {t("flag")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {Object.entries(metrics || {}).map(([key, metric]) => {
              const metricHistory = samplingsHistory
                .filter((h) => h.parameters && h.parameters[key] !== undefined)
                .map((h) => {
                  const rawVal = h.parameters[key];
                  const val =
                    rawVal && typeof rawVal === "object" && "value" in rawVal
                      ? (rawVal as Record<string, unknown>).value
                      : rawVal;
                  let numericVal = 0;
                  if (typeof val === "number") {
                    numericVal = val;
                  } else if (typeof val === "string") {
                    if (val.toUpperCase() === "HIGH") numericVal = 3;
                    else if (val.toUpperCase() === "MEDIUM") numericVal = 2;
                    else if (val.toUpperCase() === "LOW") numericVal = 1;
                    else numericVal = Number(val) || 0;
                  }
                  return {
                    date: h.sampled_at,
                    value: numericVal,
                  };
                });

              // Translate metric label
              const metricTranslationKey = metricKeyToTranslation[key];
              const translatedMetricLabel = metricTranslationKey
                ? tm(metricTranslationKey)
                : metric.label;

              const translatedMetricDesc = metricTranslationKey
                ? tm(`${metricTranslationKey}_desc`)
                : "";

              // Translate status
              const statusLower = (metric.status || "").toLowerCase();
              const statusTranslationKey = statusToTranslation[statusLower];
              const translatedStatus = statusTranslationKey
                ? t(statusTranslationKey)
                : metric.status || t("normal");

              return (
                <React.Fragment key={key}>
                  <TableRow>
                    <TableCell className="text-xs font-semibold text-slate-700 h-11 cursor-help">
                      <div
                        className="relative group flex items-center gap-1.5 h-full w-full focus:outline-none"
                        tabIndex={0}
                      >
                        <DynamicIcon
                          name={metric.icon}
                          className="w-3.5 h-3.5 text-slate-400 shrink-0"
                        />
                        <span className="underline decoration-dotted decoration-slate-300 underline-offset-2">
                          {translatedMetricLabel}
                        </span>
                        {translatedMetricDesc && (
                          <div className="pointer-events-none absolute bottom-full left-0 z-50 mb-1.5 invisible opacity-0 group-hover:visible group-hover:opacity-100 group-focus:visible group-focus:opacity-100 transition-all duration-200 max-w-50 w-max rounded bg-slate-900 p-2 text-[10px] font-normal leading-normal text-white shadow-lg whitespace-normal wrap-break-word">
                            {translatedMetricDesc}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-xs font-mono text-slate-800">
                      {metric.value !== null && metric.value !== undefined ? (
                        <>
                          {metric.value}
                          {metric.unit ? (
                            <span className="text-slate-400 font-normal">
                              {metric.unit.startsWith("°")
                                ? metric.unit
                                : ` ${metric.unit}`}
                            </span>
                          ) : (
                            ""
                          )}
                        </>
                      ) : (
                        "-"
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-center">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border transition-colors ${
                          statusLower === "normal" || statusLower === "stable"
                            ? "bg-green-50 text-green-700 border-green-200"
                            : statusLower === "flood risk" ||
                                statusLower === "drought"
                              ? "bg-red-50 text-red-700 border-red-200"
                              : "bg-amber-50 text-amber-700 border-amber-200"
                        }`}
                      >
                        {translatedStatus}
                      </span>
                    </TableCell>
                  </TableRow>
                  <TableRow className="hover:bg-transparent no-print">
                    <TableCell
                      colSpan={3}
                      className="py-0 px-2 border-b border-slate-100"
                    >
                      <CollapsibleChartContainer
                        label={translatedMetricLabel}
                        data={metricHistory}
                      />
                    </TableCell>
                  </TableRow>
                </React.Fragment>
              );
            })}
          </TableBody>
        </table>
      </div>
    </div>
  );
}

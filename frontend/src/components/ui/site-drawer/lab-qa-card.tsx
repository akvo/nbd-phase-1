"use client";

import React from "react";
import * as LucideIcons from "lucide-react";
import { LabQaReport } from "@/lib/api";
import { CollapsibleChartContainer } from "../collapsible-chart-container";
import {
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";

interface LabQaCardProps {
  report: LabQaReport | null;
  t: (key: string, values?: Record<string, string | number>) => string;
  tm: (key: string) => string;
  locale: string;
  isPrinting?: boolean;
}

const toPascalCase = (str: string): string => {
  return str
    .split(/[-_]/)
    .map((seg) => seg.charAt(0).toUpperCase() + seg.slice(1).toLowerCase())
    .join("");
};

const DynamicIcon = ({
  name,
  className,
}: {
  name: string | null;
  className?: string;
}) => {
  if (!name) {
    return <LucideIcons.FlaskConical className={className} />;
  }
  const pascalName = toPascalCase(name);
  const IconComponent = (LucideIcons[name as keyof typeof LucideIcons] ||
    LucideIcons[pascalName as keyof typeof LucideIcons] ||
    LucideIcons.FlaskConical) as React.ComponentType<{ className?: string }>;

  return <IconComponent className={className} />;
};

const labMetricKeyToTranslation: Record<string, string> = {
  lab_ph: "lab_ph",
  lab_temperature: "lab_temperature",
  lab_dissolved_oxygen: "lab_dissolved_oxygen",
  bod: "bod",
  orthophosphate: "orthophosphate",
  nitrate: "nitrate",
  mercury: "mercury",
  heavy_metals: "heavy_metals",
  total_nitrogen: "total_nitrogen",
  total_phosphorus: "total_phosphorus",
};

const PARAM_ORDER = [
  "lab_ph",
  "lab_temperature",
  "lab_dissolved_oxygen",
  "bod",
  "orthophosphate",
  "nitrate",
  "total_nitrogen",
  "total_phosphorus",
  "mercury",
  "heavy_metals",
];

export function LabQaCard({
  report,
  t,
  tm,
  locale,
  isPrinting = false,
}: LabQaCardProps) {
  if (!report || Object.keys(report.metrics || {}).length === 0) {
    return (
      <div className="space-y-3 print-avoid-break">
        <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider">
          {t("labQaReport")}
        </h3>
        <div className="rounded-lg border border-slate-200 bg-slate-50/50 p-6 text-center text-xs text-slate-500">
          {t("noLabQaData")}
        </div>
      </div>
    );
  }

  const formattedDate = report.created_at
    ? new Date(report.created_at).toLocaleDateString(locale, {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "";

  const metricEntries = Object.entries(report.metrics || {})
    .filter(([key]) => key !== "site_id" && key !== "site")
    .sort(([a], [b]) => {
      const idxA = PARAM_ORDER.indexOf(a);
      const idxB = PARAM_ORDER.indexOf(b);
      if (idxA !== -1 && idxB !== -1) return idxA - idxB;
      if (idxA !== -1) return -1;
      if (idxB !== -1) return 1;
      return a.localeCompare(b);
    });

  const history = report.history || [];

  return (
    <div className="space-y-3 print-avoid-break">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider">
          {t("labQaReport")}
        </h3>
        {formattedDate && (
          <span className="text-xs text-slate-400 font-normal">
            {formattedDate}
          </span>
        )}
      </div>

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
            {metricEntries.map(([key, metric]) => {
              const metricHistory = history
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
                    numericVal = Number(val) || 0;
                  }
                  return {
                    date: h.date,
                    value: numericVal,
                  };
                });

              const metricTranslationKey = labMetricKeyToTranslation[key];
              const translatedMetricLabel = metricTranslationKey
                ? tm(metricTranslationKey)
                : metric.label;

              const translatedMetricDesc = metricTranslationKey
                ? tm(`${metricTranslationKey}_desc`)
                : "";

              const statusLower = (metric.status || "").toLowerCase();
              const isVerified =
                statusLower === "verified" ||
                statusLower === "normal" ||
                statusLower === "approved";
              const translatedStatus = isVerified
                ? t("verified")
                : metric.status || t("normal");

              let displayValue: React.ReactNode = "-";
              if (metric.value !== null && metric.value !== undefined) {
                if (typeof metric.value === "number") {
                  displayValue = Number.isInteger(metric.value)
                    ? metric.value
                    : parseFloat(metric.value.toFixed(2));
                } else {
                  displayValue = String(metric.value);
                }
              }

              // Determine if we should display collapsible history chart
              const isNumeric = typeof metric.value === "number";

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
                      {displayValue !== "-" ? (
                        <>
                          {displayValue}
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
                          isVerified
                            ? "bg-green-50 text-green-700 border-green-200"
                            : "bg-slate-50 text-slate-700 border-slate-200"
                        }`}
                      >
                        {translatedStatus}
                      </span>
                    </TableCell>
                  </TableRow>
                  {isNumeric && (
                    <TableRow className="hover:bg-transparent">
                      <TableCell
                        colSpan={3}
                        className="py-0 px-2 border-b border-slate-100"
                      >
                        <CollapsibleChartContainer
                          label={translatedMetricLabel}
                          data={metricHistory}
                          isPrinting={isPrinting}
                          locale={locale}
                        />
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              );
            })}
          </TableBody>
        </table>
      </div>
    </div>
  );
}

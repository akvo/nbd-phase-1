"use client";

import React, { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import * as LucideIcons from "lucide-react";
import { CollapsibleChartContainer } from "./collapsible-chart-container";
import {
  getSiteSamplings,
  getSiteScores,
  GenericSamplingHistory,
  GenericScoreHistory,
} from "@/lib/api";
import { useTranslations } from "next-intl";

import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";

const DynamicIcon = ({
  name,
  className,
}: {
  name: string | null;
  className?: string;
}) => {
  if (!name) return null;
  const IconComponent = LucideIcons[name as keyof typeof LucideIcons] as
    | React.ComponentType<{ className?: string }>
    | undefined;
  if (!IconComponent) return null;
  return <IconComponent className={className} />;
};

const getStatusColorClasses = (status: string) => {
  const s = status.toLowerCase();
  if (s.includes("flood")) {
    return {
      text: "text-blue-600",
      bg: "bg-blue-500",
    };
  }
  if (s.includes("abnormal") || s.includes("low") || s.includes("drought")) {
    return {
      text: "text-amber-600",
      bg: "bg-amber-500",
    };
  }
  return {
    text: "text-green-600",
    bg: "bg-green-500",
  };
};

interface MetricEntry {
  value: string | number | boolean | null;
  unit: string | null;
  status: string;
  label: string;
  icon: string | null;
}

interface GroupScoreEntry {
  score: number;
  label: string;
  icon: string | null;
}

interface SiteDetails {
  score_breakdown: Record<string, GroupScoreEntry>;
  physico_chemical: {
    group_score: number;
    ph: number;
    dissolved_oxygen: number;
    temperature: number;
    weights: { ph: number; dissolved_oxygen: number };
  };
  catchment_hydrological: { group_score: number };
  ecological: { group_score: number };
  ik_signal: {
    encoded_signal_value: number;
    fish_abundance: string;
    water_clarity: string;
    vegetation_cover: string;
    pollution_events: string;
  };
  management_actions: Array<{ label: string; description: string }>;
  water_level: string;
  metrics: Record<string, MetricEntry>;
}

interface Site {
  site_id: string;
  site_name: string;
  country: string;
  basin: string;
  current_health_class: string;
  current_score: number;
  last_updated: string;
  coordinates: [number, number];
  community_signal: string;
  progress_percent: number;
  is_approved: boolean;
  is_ik_adjusted: boolean;
  details: SiteDetails;
}

interface SiteDrawerProps {
  site: Site | null;
  onClose: () => void;
}

function getTileCoords(lat: number, lon: number, zoom: number) {
  const latRad = (lat * Math.PI) / 180;
  const n = Math.pow(2, zoom);
  const xDouble = ((lon + 180) / 360) * n;
  const yDouble =
    ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n;

  const x = Math.floor(xDouble);
  const y = Math.floor(yDouble);

  const xOffset = (xDouble - x) * 256;
  const yOffset = (yDouble - y) * 256;

  return { x, y, xOffset, yOffset };
}

// Map score breakdown keys to translation keys
const scoreKeyToTranslation: Record<string, string> = {
  physico_chemical: "physicoChemical",
  catchment_hydrological: "catchmentHydrological",
  ecological: "ecological",
  governance: "governance",
};

// Map metric keys to translation keys
const metricKeyToTranslation: Record<string, string> = {
  ph: "ph",
  dissolved_oxygen: "dissolvedOxygen",
  temperature: "temperature",
  water_level: "waterLevel",
  turbidity: "turbidity",
  macroinvertebrate: "macroinvertebrate",
};

// Map status values to translation keys (case-insensitive matching)
const statusToTranslation: Record<string, string> = {
  normal: "normal",
  "flood risk": "floodRisk",
  drought: "drought",
  "abnormal low": "abnormalLow",
  stable: "stable",
};

// Map FGD indicator values to translation keys
const fgdValueToTranslation: Record<string, string> = {
  same: "same",
  none: "none",
};

export function SiteDrawer({ site, onClose }: SiteDrawerProps) {
  // Hooks must be called unconditionally — before any early returns
  const t = useTranslations("drawer");
  const tc = useTranslations("common");
  const ts = useTranslations("scores");
  const tm = useTranslations("metrics");
  const [isPrinting, setIsPrinting] = useState(false);
  const [samplingsHistory, setSamplingsHistory] = useState<
    GenericSamplingHistory[]
  >([]);
  const [scoresHistory, setScoresHistory] = useState<GenericScoreHistory[]>([]);
  const [scoresError, setScoresError] = useState<string | null>(null);

  useEffect(() => {
    if (!site?.site_id) {
      setSamplingsHistory([]);
      setScoresHistory([]);
      setScoresError(null);
      return;
    }

    const dateFrom = new Date();
    dateFrom.setDate(dateFrom.getDate() - 35);
    const dateFromStr = dateFrom.toISOString();

    getSiteSamplings(site.site_id, { date_from: dateFromStr })
      .then(setSamplingsHistory)
      .catch(console.error);

    getSiteScores(site.site_id, { date_from: dateFromStr })
      .then((data) => {
        setScoresError(null);
        setScoresHistory(data);
      })
      .catch((err) => {
        console.error(err);
        setScoresError("scoreHistoryError");
      });
  }, [site?.site_id]);

  if (!site) return null;

  const handlePrint = () => {
    if (typeof document === "undefined") {
      window.print();
      return;
    }

    setIsPrinting(true);

    const doPrint = () => {
      const originalTitle = document.title;
      document.title = `${site.site_name.replace(/\s+/g, "_")}_Detailed_Report`;
      // Wait 2.5 s after image loads — gives the browser time to paint it into the
      // print-only DOM section before window.print() captures the layout.
      setTimeout(() => {
        window.print();
        setTimeout(() => {
          document.title = originalTitle;
          setIsPrinting(false);
        }, 1000);
      }, 2500);
    };

    // Preload all 3 tiles so they are in the browser cache before print fires
    if (site.coordinates) {
      const { x, y } = getTileCoords(
        site.coordinates[0],
        site.coordinates[1],
        12
      );
      let loadedCount = 0;
      const totalTiles = 15;
      const onTileLoad = () => {
        loadedCount++;
        if (loadedCount === totalTiles) {
          doPrint();
        }
      };

      for (let dx = -2; dx <= 2; dx++) {
        for (let dy = -1; dy <= 1; dy++) {
          const img = new window.Image();
          img.onload = onTileLoad;
          img.onerror = onTileLoad;
          img.src = `https://tile.openstreetmap.org/12/${x + dx}/${y + dy}.png`;
        }
      }
    } else {
      doPrint();
    }
  };

  const isCritical = ["D", "E"].includes(site.current_health_class);
  const isAtRisk = site.current_health_class === "C";

  // Determine severity themes for header grade circle
  let gradeCircleClass = "bg-green-500 text-green-50 border-transparent";
  let gradeTextClass = "text-green-600";
  if (isCritical) {
    gradeCircleClass = "bg-red-500 text-red-50 border-transparent";
    gradeTextClass = "text-red-600";
  } else if (isAtRisk) {
    gradeCircleClass = "bg-amber-500 text-amber-50 border-transparent";
    gradeTextClass = "text-amber-600";
  }

  const getScoreColorClass = (score: number) => {
    if (score >= 0.6) return "bg-green-500";
    if (score >= 0.2) return "bg-amber-500";
    return "bg-red-500";
  };

  // Pre-calculate composites for display matching Figma LLD spec
  const rawComposite = (
    site.current_score + (site.is_ik_adjusted ? 0.05 : 0)
  ).toFixed(2);

  const scoreBreakdownEntries = Object.entries(
    site.details.score_breakdown || {}
  );

  return (
    <div
      id="site-drawer-print-area"
      className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-white shadow-2xl flex flex-col h-full border-l border-slate-200 animate-slide-in"
    >
      {/* Drawer Header */}
      <div className="p-6 border-b border-slate-200 flex items-center justify-between">
        <div className="flex-1 min-w-0 pr-4">
          <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">
            {t("monitoringStation")}
          </span>
          <h2 className="text-lg font-bold text-slate-800 truncate mt-0.5">
            {site.site_name}
          </h2>
          <p className="text-xs text-slate-500 font-mono mt-0.5">
            {site.site_id}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div
            className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg shadow-sm border ${gradeCircleClass}`}
          >
            {site.current_health_class}
          </div>
          <Button
            variant="ghost"
            onClick={onClose}
            className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-400 hover:text-slate-600 transition-colors"
          >
            ✕
          </Button>
        </div>
      </div>

      {/* Badges line */}
      <div className="px-6 py-3 border-b border-slate-100 bg-slate-50/50 flex flex-wrap gap-2 items-center">
        <div className="flex items-center gap-1 text-xs text-slate-700 bg-white border border-slate-200 px-2.5 py-1 rounded-full shadow-sm">
          <svg
            className="w-3.5 h-3.5 text-slate-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
          <span>{site.country}</span>
        </div>
        <Badge variant={site.is_approved ? "success" : "warning"}>
          {site.is_approved ? tc("approved") : tc("pending")}
        </Badge>
        {site.is_ik_adjusted && (
          <Badge variant="primary">{t("ikAdjusted")}</Badge>
        )}
      </div>

      {/* Drawer Body */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Warning Alert Banner */}
        {(isCritical || isAtRisk) && (
          <div className="bg-amber-50/80 border border-amber-200 rounded-xl p-4 flex gap-3 items-start animate-fade-in">
            <svg
              className="w-5 h-5 text-amber-600 shrink-0 mt-0.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="2.5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <p className="text-xs text-amber-700 leading-relaxed font-medium">
              {t("warningMessage", { healthClass: site.current_health_class })}
            </p>
          </div>
        )}

        {/* Community Signal Section */}
        {site.community_signal && (
          <div className="text-sm text-slate-700 leading-relaxed border-l-4 border-teal-500 pl-3.5 py-1 bg-teal-50/30 rounded-r-lg">
            <span className="font-bold text-slate-800">
              {t("communitySignal")}:{" "}
            </span>
            <span className="italic">&quot;{site.community_signal}&quot;</span>
          </div>
        )}

        {/* Location Map – static image shown ONLY in print output */}
        {site.coordinates &&
          (() => {
            const { x, y, xOffset, yOffset } = getTileCoords(
              site.coordinates[0],
              site.coordinates[1],
              12
            );
            const tiles = [];
            for (let dx = -2; dx <= 2; dx++) {
              for (let dy = -1; dy <= 1; dy++) {
                const tileX = x + dx;
                const tileY = y + dy;
                const leftPos = (dx + 2) * 256;
                const topPos = (dy + 1) * 256;
                tiles.push(
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    key={`${tileX}-${tileY}`}
                    src={`https://tile.openstreetmap.org/12/${tileX}/${tileY}.png`}
                    alt=""
                    style={{
                      position: "absolute",
                      left: `${leftPos}px`,
                      top: `${topPos}px`,
                      width: "256px",
                      height: "256px",
                    }}
                  />
                );
              }
            }

            return (
              <div className="space-y-3 hidden print:block print-avoid-break">
                <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider">
                  {t("locationMap")}
                </h3>
                <div className="w-full rounded-xl border border-slate-200 shadow-sm relative map-container-overflow">
                  {/* 5x3 Tile Container centered around coordinate */}
                  <div
                    style={{
                      position: "absolute",
                      width: "1280px",
                      height: "768px",
                      left: `calc(50% - ${512 + xOffset}px)`,
                      top: `calc(50% - ${256 + yOffset}px)`,
                    }}
                  >
                    {tiles}
                  </div>
                  {/* Centered red dot marker representing location */}
                  <div
                    style={{
                      position: "absolute",
                      left: "50%",
                      top: "50%",
                      transform: "translate(-50%, -50%)",
                      zIndex: 10,
                      width: "14px",
                      height: "14px",
                      backgroundColor: "#ef4444",
                      borderRadius: "50%",
                      border: "2px solid white",
                      boxShadow: "0 2px 4px rgba(0,0,0,0.35)",
                    }}
                  />
                </div>
              </div>
            );
          })()}

        {/* Required Interventions */}
        <div className="space-y-3 print-avoid-break">
          <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider">
            {t("requiredInterventions")}
          </h3>
          {site.details.management_actions.length > 0 ? (
            <div className="space-y-3">
              {site.details.management_actions.map((action, i) => (
                <div
                  key={i}
                  className="p-4 border border-slate-100 rounded-xl bg-slate-50/50 shadow-sm"
                >
                  <div className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                    <span className="text-amber-500">⚠️</span> {action.label}
                  </div>
                  <div className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                    {action.description}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-slate-400 italic bg-slate-50 p-4 rounded-xl text-center border border-dashed border-slate-200">
              {t("noInterventions")}
            </div>
          )}
        </div>

        {/* 2x2 Key Metrics Card Small Grid (Figma Node 8237:1345) */}
        <div className="print-avoid-break">
          <div className="border border-slate-200 rounded-2xl overflow-hidden grid grid-cols-2 bg-slate-50/50">
            {Object.entries(site.details.metrics || {}).map(
              ([key, metric], index) => {
                const colors = getStatusColorClasses(metric.status);
                const isValString = typeof metric.value === "string";
                const displayValue = isValString
                  ? (metric.value as string).toLowerCase()
                  : (metric.value ?? "");
                const valueClass = `text-base font-bold text-slate-800 ${isValString ? "capitalize" : ""}`;
                const borderClass = `${index % 2 === 0 ? "border-r" : ""} ${index < 2 ? "border-b" : ""} border-slate-200`;

                // Translate metric label
                const metricTranslationKey = metricKeyToTranslation[key];
                const translatedMetricLabel = metricTranslationKey
                  ? tm(metricTranslationKey)
                  : metric.label;

                // Translate status
                const statusLower = (metric.status || "").toLowerCase();
                const statusTranslationKey = statusToTranslation[statusLower];
                const translatedStatus = statusTranslationKey
                  ? t(statusTranslationKey)
                  : metric.status;

                return (
                  <div
                    key={key}
                    className={`bg-slate-50/60 p-4 flex flex-col justify-between h-24 ${borderClass}`}
                  >
                    <div className="flex justify-between items-start text-xs text-slate-500">
                      <span className="font-medium text-slate-400">
                        {translatedMetricLabel}
                      </span>
                      <DynamicIcon
                        name={metric.icon}
                        className="w-4 h-4 text-slate-400"
                      />
                    </div>
                    <div className={valueClass}>
                      {displayValue}
                      {metric.unit
                        ? metric.unit.startsWith("°")
                          ? metric.unit
                          : ` ${metric.unit}`
                        : ""}
                    </div>
                    <div
                      className={`flex items-center gap-1.5 text-[10px] font-semibold ${colors.text}`}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${colors.bg}`}
                      />
                      <span>{translatedStatus}</span>
                    </div>
                  </div>
                );
              }
            )}
          </div>
        </div>

        {/* Score Breakdown Progress Bars */}
        <div className="print-avoid-break">
          <div className="bg-slate-50 border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
            <div className="bg-white border-b border-slate-200 px-4.5 py-3.5">
              <h4 className="font-bold text-sm text-slate-800">
                {t("scoreBreakdown")}
              </h4>
              <p className="text-xs text-slate-500 mt-0.5">
                {t("parameterGroupScores")}
              </p>
            </div>
            <div className="p-4.5 space-y-4 bg-white">
              {scoresError && (
                <div className="text-[10px] text-red-400 italic px-1">
                  ⚠ {t(scoresError)}
                </div>
              )}
              {scoreBreakdownEntries.map(([key, group]) => {
                const groupHistory = scoresHistory
                  .filter((h) => h.breakdown && h.breakdown[key] !== undefined)
                  .map((h) => ({
                    date: h.calculated_at,
                    value:
                      typeof h.breakdown[key] === "object" &&
                      h.breakdown[key] !== null
                        ? (h.breakdown[key] as Record<string, unknown>)
                            .score !== undefined
                          ? Number(
                              (h.breakdown[key] as Record<string, unknown>)
                                .score
                            )
                          : 0
                        : Number(h.breakdown[key] ?? 0),
                  }));

                // Use translated label based on key, fallback to backend label
                const translationKey = scoreKeyToTranslation[key];
                const translatedLabel = translationKey
                  ? ts(translationKey)
                  : group.label;

                return (
                  <div key={key} className="space-y-2">
                    <div className="flex justify-between text-xs font-semibold text-slate-700">
                      <div className="flex items-center gap-1.5">
                        <DynamicIcon
                          name={group.icon}
                          className="w-3.5 h-3.5 text-slate-400"
                        />
                        <span>{translatedLabel}</span>
                      </div>
                      <span>{group.score.toFixed(2)}</span>
                    </div>
                    <div className="relative h-2 w-full overflow-hidden rounded-full bg-slate-100">
                      <div
                        className={`h-full transition-all duration-300 ease-in-out rounded-full ${getScoreColorClass(group.score)}`}
                        style={{
                          width: `${group.score * 100}%`,
                        }}
                      />
                    </div>
                    <CollapsibleChartContainer
                      label={translatedLabel}
                      data={groupHistory}
                    />
                  </div>
                );
              })}
            </div>

            {/* Bottom adjustment score panel */}
            <div className="bg-slate-50 p-4 border-t border-slate-200 space-y-2 text-xs font-medium text-slate-700">
              <div className="flex justify-between">
                <span>{t("compositePreAdjustment")}</span>
                <span className="font-semibold text-slate-800">
                  {rawComposite}
                </span>
              </div>
              {site.is_ik_adjusted && (
                <div className="flex justify-between">
                  <span>{t("ikHealthSignal")}</span>
                  <span className="font-semibold text-slate-800">
                    {site.details.ik_signal.encoded_signal_value.toFixed(2)}
                  </span>
                </div>
              )}
              <div
                className={`flex justify-between font-bold border-t border-slate-200/60 pt-2 mt-1 ${gradeTextClass}`}
              >
                <span>
                  {t("adjustedScore", {
                    healthClass: site.current_health_class,
                  })}
                </span>
                <span className="text-sm font-extrabold">
                  {site.current_score.toFixed(2)}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Raw Sampling Method Table */}
        <div className="space-y-3 print-avoid-break">
          <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider">
            {t("rawSamplingMethod")}
          </h3>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs uppercase text-slate-500 font-bold">
                  {t("parameter")}
                </TableHead>
                <TableHead className="text-xs uppercase text-slate-500 font-bold text-center">
                  {t("value")}
                </TableHead>
                <TableHead className="text-xs uppercase text-slate-500 font-bold text-center">
                  {t("unit")}
                </TableHead>
                <TableHead className="text-xs uppercase text-slate-500 font-bold text-center">
                  {t("flag")}
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.entries(site.details.metrics || {}).map(
                ([key, metric]) => {
                  const metricHistory = samplingsHistory
                    .filter(
                      (h) => h.parameters && h.parameters[key] !== undefined
                    )
                    .map((h) => {
                      const rawVal = h.parameters[key];
                      const val =
                        rawVal &&
                        typeof rawVal === "object" &&
                        "value" in rawVal
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

                  // Translate status
                  const statusLower = (metric.status || "").toLowerCase();
                  const statusTranslationKey = statusToTranslation[statusLower];
                  const translatedStatus = statusTranslationKey
                    ? t(statusTranslationKey)
                    : metric.status || t("normal");

                  return (
                    <React.Fragment key={key}>
                      <TableRow>
                        <TableCell className="text-xs font-semibold text-slate-700">
                          {translatedMetricLabel}
                        </TableCell>
                        <TableCell className="text-xs font-mono text-slate-800 text-center">
                          {typeof metric.value === "string"
                            ? metric.value
                            : (metric.value ?? "-")}
                        </TableCell>
                        <TableCell className="text-xs text-slate-500 text-center">
                          {metric.unit || "-"}
                        </TableCell>
                        <TableCell className="text-center">
                          <span
                            className={`inline-block px-1.5 py-0.5 rounded-full text-[9px] font-bold ${
                              statusLower.includes("normal") ||
                              statusLower.includes("stable")
                                ? "bg-green-100 text-green-700"
                                : "bg-amber-100 text-amber-700"
                            }`}
                          >
                            {translatedStatus}
                          </span>
                        </TableCell>
                      </TableRow>
                      <TableRow className="hover:bg-transparent no-print">
                        <TableCell
                          colSpan={4}
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
                }
              )}
            </TableBody>
          </Table>
        </div>

        {/* FGD Session Context */}
        <div className="space-y-3 print-avoid-break">
          <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider">
            {t("fgdSession")}
          </h3>
          <div className="bg-blue-50/30 border border-blue-100 rounded-xl p-4.5 space-y-3.5">
            <div className="space-y-2">
              <div className="flex justify-between text-xs text-slate-500">
                <span>{t("ikSignalStrength")}:</span>
                <span className="font-semibold text-blue-700">
                  {(site.details.ik_signal.encoded_signal_value * 100).toFixed(
                    0
                  )}
                  %
                </span>
              </div>
              <Progress
                value={site.details.ik_signal.encoded_signal_value * 100}
              />
            </div>

            {/* 2x2 Grid of FGD Indicators */}
            <div className="grid grid-cols-2 gap-3 pt-1 text-xs text-slate-700">
              {[
                {
                  labelKey: "fishAbundance" as const,
                  value: site.details.ik_signal.fish_abundance,
                  icon: "🐟",
                  redVals: ["severely declined", "severe"],
                  orangeVals: [
                    "slightly declined",
                    "moderately declined",
                    "slight",
                    "moderate",
                  ],
                },
                {
                  labelKey: "waterQuality" as const,
                  value: site.details.ik_signal.water_clarity,
                  icon: "💧",
                  redVals: ["much worse"],
                  orangeVals: ["somewhat worse"],
                },
                {
                  labelKey: "vegetationCover" as const,
                  value: site.details.ik_signal.vegetation_cover,
                  icon: "🌱",
                  redVals: ["severely lost", "severe loss"],
                  orangeVals: ["partially lost", "partial loss"],
                },
                {
                  labelKey: "pollutionEvents" as const,
                  value: site.details.ik_signal.pollution_events,
                  icon: "⚠️",
                  redVals: ["frequent"],
                  orangeVals: ["occasional"],
                },
              ].map((item, idx) => {
                const valLower = (item.value || "")
                  .toLowerCase()
                  .replace(/_/g, " ")
                  .trim();
                let dotColor = "bg-green-500";
                let statusKey:
                  | "statusCritical"
                  | "statusWarning"
                  | "statusHealthy" = "statusHealthy";
                if (item.redVals.some((rv) => valLower.includes(rv))) {
                  dotColor = "bg-red-500";
                  statusKey = "statusCritical";
                } else if (
                  item.orangeVals.some((ov) => valLower.includes(ov))
                ) {
                  dotColor = "bg-amber-500";
                  statusKey = "statusWarning";
                }

                // Translate FGD indicator value
                const fgdTranslationKey = fgdValueToTranslation[valLower];
                const translatedValue = fgdTranslationKey
                  ? t(fgdTranslationKey)
                  : valLower;

                return (
                  <div
                    key={idx}
                    className="bg-white/80 p-2.5 rounded-lg border border-slate-100 flex flex-col justify-between gap-1 shadow-sm"
                  >
                    <span className="text-[10px] text-slate-400 font-medium tracking-wide uppercase">
                      {t(item.labelKey)}
                    </span>
                    <div className="flex items-center gap-1.5 mt-1 font-semibold text-slate-800 capitalize">
                      <span className="text-sm leading-none shrink-0">
                        {item.icon}
                      </span>
                      <span className="truncate">{translatedValue}</span>
                    </div>
                    <div className="flex items-center gap-1 text-[9px] font-semibold text-slate-500 mt-1">
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${dotColor}`}
                      />
                      <span>{t(statusKey)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* PDF Export Button */}
        <div className="pt-4 no-print pb-6">
          <Button
            onClick={handlePrint}
            disabled={isPrinting}
            className="w-full bg-[#38B1DD] hover:bg-[#27A0CD] disabled:opacity-70 text-white py-6 rounded-xl font-bold flex items-center justify-center gap-2 shadow-md transition-all active:scale-[0.98]"
          >
            {isPrinting ? (
              <>
                <LucideIcons.Loader2 className="w-5 h-5 animate-spin" />
                {t("preparingPdf")}
              </>
            ) : (
              <>
                <LucideIcons.Printer className="w-5 h-5" />
                {t("exportReport")}
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default SiteDrawer;

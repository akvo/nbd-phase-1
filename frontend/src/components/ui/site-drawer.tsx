"use client";

import React, { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import * as LucideIcons from "lucide-react";
import {
  getSiteSamplings,
  getSiteScores,
  GenericSamplingHistory,
  GenericScoreHistory,
} from "@/lib/api";
import { useTranslations, useLocale } from "next-intl";

import { InterventionsList } from "./site-drawer/interventions-list";
import { ParameterTable } from "./site-drawer/parameter-table";
import { ScoreBreakdownPanel } from "./site-drawer/score-breakdown-panel";

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

// Map FGD indicator values to translation keys
const fgdValueToTranslation: Record<string, string> = {
  same: "same",
  none: "none",
};

const hideFGD = true;
const hideFuzzy = true;
const hideCommunitySignal = true;

export function SiteDrawer({ site, onClose }: SiteDrawerProps) {
  // Hooks must be called unconditionally — before any early returns
  const t = useTranslations("drawer");
  const locale = useLocale();
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
  if (isCritical) {
    gradeCircleClass = "bg-red-500 text-red-50 border-transparent";
  } else if (isAtRisk) {
    gradeCircleClass = "bg-amber-500 text-amber-50 border-transparent";
  }

  return (
    <div
      id="site-drawer-print-area"
      className={`fixed inset-y-0 right-0 z-50 w-full bg-white shadow-2xl flex flex-col h-full border-l border-slate-200 animate-slide-in transition-all duration-300 ${
        isPrinting ? "max-w-4xl" : "max-w-md"
      }`}
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
            &nbsp;
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
        {site.last_updated && (
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
                d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
            <span>
              {t("lastReported")}:{" "}
              {new Date(site.last_updated).toLocaleDateString(locale, {
                year: "numeric",
                month: "short",
                day: "numeric",
              })}
            </span>
          </div>
        )}
        {site.is_ik_adjusted && !hideFuzzy && (
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
        {site.community_signal && !hideCommunitySignal && (
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
        <InterventionsList
          managementActions={site.details.management_actions || []}
          t={t}
        />

        {/* Parameter Table */}
        <ParameterTable
          metrics={site.details.metrics || {}}
          samplingsHistory={samplingsHistory}
          t={t}
          tm={tm}
          isPrinting={isPrinting}
        />

        {/* Score Breakdown Progress Bars */}
        <ScoreBreakdownPanel
          site={site}
          scoresHistory={scoresHistory}
          scoresError={scoresError}
          t={t}
          ts={ts}
          isPrinting={isPrinting}
        />

        {/* FGD Session Context */}
        {!hideFGD && (
          <div className="space-y-3 print-avoid-break">
            <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider">
              {t("fgdSession")}
            </h3>
            <div className="bg-blue-50/30 border border-blue-100 rounded-xl p-4.5 space-y-3.5">
              <div className="space-y-2">
                <div className="flex justify-between text-xs text-slate-500">
                  <span>{t("ikSignalStrength")}:</span>
                  <span className="font-semibold text-blue-700">
                    {(
                      site.details.ik_signal.encoded_signal_value * 100
                    ).toFixed(0)}
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
                  const isRed = item.redVals.some((rv) =>
                    valLower.includes(rv)
                  );
                  const isOrange = item.orangeVals.some((ov) =>
                    valLower.includes(ov)
                  );

                  const dotColor = isRed
                    ? "bg-red-500"
                    : isOrange
                      ? "bg-amber-500"
                      : "bg-green-500";
                  const statusKey = isRed
                    ? "statusCritical"
                    : isOrange
                      ? "statusWarning"
                      : "statusHealthy";

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
        )}

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

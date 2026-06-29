"use client";

import React from "react";
import * as LucideIcons from "lucide-react";
import { CollapsibleChartContainer } from "../collapsible-chart-container";
import { GenericScoreHistory } from "@/lib/api";

interface GroupScoreEntry {
  score: number;
  label: string;
  icon: string | null;
}

interface SiteDetails {
  score_breakdown: Record<string, GroupScoreEntry>;
  ik_signal: {
    encoded_signal_value: number;
  };
}

interface Site {
  current_health_class: string;
  current_score: number;
  is_ik_adjusted: boolean;
  details: SiteDetails;
}

interface ScoreBreakdownPanelProps {
  site: Site;
  scoresHistory: GenericScoreHistory[];
  scoresError: string | null;
  t: (key: string, values?: Record<string, string | number>) => string;
  ts: (key: string) => string;
}

const DynamicIcon = ({
  name,
  className,
}: {
  name: string | null;
  className?: string;
}) => {
  if (!name) {
    return null;
  }
  const IconComponent = LucideIcons[
    name as keyof typeof LucideIcons
  ] as React.ComponentType<{ className?: string }>;
  if (!IconComponent) {
    return null;
  }
  return <IconComponent className={className} />;
};

const scoreKeyToTranslation: Record<string, string> = {
  physico_chemical: "physicoChemical",
  catchment_hydrological: "catchmentHydrological",
  ecological: "ecological",
  governance: "governance",
};

const hideFuzzy = true;

export function ScoreBreakdownPanel({
  site,
  scoresHistory,
  scoresError,
  t,
  ts,
}: ScoreBreakdownPanelProps) {
  const isCritical = ["D", "E"].includes(site.current_health_class);
  const isAtRisk = site.current_health_class === "C";

  let gradeTextClass = "text-green-600";
  if (isCritical) {
    gradeTextClass = "text-red-600";
  } else if (isAtRisk) {
    gradeTextClass = "text-amber-600";
  }

  const getScoreColorClass = (score: number) => {
    if (score >= 0.6) return "bg-green-500";
    if (score >= 0.2) return "bg-amber-500";
    return "bg-red-500";
  };

  const rawComposite = (
    site.current_score + (site.is_ik_adjusted ? 0.05 : 0)
  ).toFixed(2);

  const scoreBreakdownEntries = Object.entries(
    site.details.score_breakdown || {}
  );

  return (
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
                    ? (h.breakdown[key] as Record<string, unknown>).score !==
                      undefined
                      ? Number(
                          (h.breakdown[key] as Record<string, unknown>).score
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
          {!hideFuzzy && (
            <div className="flex justify-between">
              <span>{t("compositePreAdjustment")}</span>
              <span className="font-semibold text-slate-800">
                {rawComposite}
              </span>
            </div>
          )}
          {site.is_ik_adjusted && !hideFuzzy && (
            <div className="flex justify-between">
              <span>{t("ikHealthSignal")}</span>
              <span className="font-semibold text-slate-800">
                {site.details.ik_signal.encoded_signal_value.toFixed(2)}
              </span>
            </div>
          )}
          <div
            className={`flex justify-between font-bold ${
              !hideFuzzy ? "border-t border-slate-200/60 pt-2 mt-1" : ""
            } ${gradeTextClass}`}
          >
            <span>
              {hideFuzzy
                ? `Score - Class ${site.current_health_class}`
                : t("adjustedScore", {
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
  );
}

"use client";

import React from "react";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import * as LucideIcons from "lucide-react";
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

export function SiteDrawer({ site, onClose }: SiteDrawerProps) {
  if (!site) return null;

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
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-white shadow-2xl flex flex-col h-full border-l border-slate-200 animate-slide-in">
      {/* Drawer Header */}
      <div className="p-6 border-b border-slate-200 flex items-center justify-between">
        <div className="flex-1 min-w-0 pr-4">
          <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">
            Monitoring Station
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
          {site.is_approved ? "Approved" : "Pending"}
        </Badge>
        {site.is_ik_adjusted && <Badge variant="primary">IK-adjusted</Badge>}
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
              Wetland health is currently at risk or degraded (Class{" "}
              {site.current_health_class}). Management interventions are highly
              recommended to prevent further ecological decline.
            </p>
          </div>
        )}

        {/* Community Signal Section */}
        {site.community_signal && (
          <div className="text-sm text-slate-700 leading-relaxed border-l-4 border-teal-500 pl-3.5 py-1 bg-teal-50/30 rounded-r-lg">
            <span className="font-bold text-slate-800">Community signal: </span>
            <span className="italic">&quot;{site.community_signal}&quot;</span>
          </div>
        )}

        {/* 2x2 Key Metrics Card Small Grid (Figma Node 8237:1345) */}
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

              return (
                <div
                  key={key}
                  className={`bg-slate-50/60 p-4 flex flex-col justify-between h-24 ${borderClass}`}
                >
                  <div className="flex justify-between items-start text-xs text-slate-500">
                    <span className="font-medium text-slate-400">
                      {metric.label}
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
                    <span className={`w-1.5 h-1.5 rounded-full ${colors.bg}`} />
                    <span>{metric.status}</span>
                  </div>
                </div>
              );
            }
          )}
        </div>

        {/* Score Breakdown Progress Bars */}
        <div className="bg-slate-50 border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
          <div className="bg-white border-b border-slate-200 px-4.5 py-3.5">
            <h4 className="font-bold text-sm text-slate-800">
              Score breakdown
            </h4>
            <p className="text-xs text-slate-500 mt-0.5">
              Parameter group scores (May 2026 sampling)
            </p>
          </div>
          <div className="p-4.5 space-y-4 bg-white">
            {scoreBreakdownEntries.map(([key, group]) => (
              <div key={key} className="space-y-2">
                <div className="flex justify-between text-xs font-semibold text-slate-700">
                  <div className="flex items-center gap-1.5">
                    <DynamicIcon
                      name={group.icon}
                      className="w-3.5 h-3.5 text-slate-400"
                    />
                    <span>{group.label}</span>
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
              </div>
            ))}
          </div>

          {/* Bottom adjustment score panel */}
          <div className="bg-slate-50 p-4 border-t border-slate-200 space-y-2 text-xs font-medium text-slate-700">
            <div className="flex justify-between">
              <span>Composite (pre-adjustment)</span>
              <span className="font-semibold text-slate-800">
                {rawComposite}
              </span>
            </div>
            {site.is_ik_adjusted && (
              <div className="flex justify-between">
                <span>IK health signal (FGD)</span>
                <span className="font-semibold text-slate-800">
                  {site.details.ik_signal.encoded_signal_value.toFixed(2)}
                </span>
              </div>
            )}
            <div
              className={`flex justify-between font-bold border-t border-slate-200/60 pt-2 mt-1 ${gradeTextClass}`}
            >
              <span>Adjusted score - Class {site.current_health_class}</span>
              <span className="text-sm font-extrabold">
                {site.current_score.toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        {/* Raw Sampling Method Table */}
        <div className="space-y-3">
          <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider">
            Raw sampling method
          </h3>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs uppercase text-slate-500 font-bold">
                  Parameter
                </TableHead>
                <TableHead className="text-xs uppercase text-slate-500 font-bold text-center">
                  Value
                </TableHead>
                <TableHead className="text-xs uppercase text-slate-500 font-bold text-center">
                  Unit
                </TableHead>
                <TableHead className="text-xs uppercase text-slate-500 font-bold text-center">
                  Flag
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.entries(site.details.metrics || {}).map(
                ([key, metric]) => (
                  <TableRow key={key}>
                    <TableCell className="text-xs font-semibold text-slate-700">
                      {metric.label}
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
                          (metric.status || "")
                            .toLowerCase()
                            .includes("normal") ||
                          (metric.status || "").toLowerCase().includes("stable")
                            ? "bg-green-100 text-green-700"
                            : "bg-amber-100 text-amber-700"
                        }`}
                      >
                        {metric.status || "Normal"}
                      </span>
                    </TableCell>
                  </TableRow>
                )
              )}
            </TableBody>
          </Table>
        </div>

        {/* FGD Session Context */}
        <div className="space-y-3">
          <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider">
            FGD Session (Indigenous Knowledge)
          </h3>
          <div className="bg-blue-50/30 border border-blue-100 rounded-xl p-4.5 space-y-3.5">
            <div className="space-y-2">
              <div className="flex justify-between text-xs text-slate-500">
                <span>IK Signal Strength:</span>
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
                  label: "Fish Abundance",
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
                  label: "Water Quality",
                  value: site.details.ik_signal.water_clarity,
                  icon: "💧",
                  redVals: ["much worse"],
                  orangeVals: ["somewhat worse"],
                },
                {
                  label: "Vegetation Cover",
                  value: site.details.ik_signal.vegetation_cover,
                  icon: "🌱",
                  redVals: ["severely lost", "severe loss"],
                  orangeVals: ["partially lost", "partial loss"],
                },
                {
                  label: "Pollution Events",
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
                if (item.redVals.some((rv) => valLower.includes(rv))) {
                  dotColor = "bg-red-500";
                } else if (
                  item.orangeVals.some((ov) => valLower.includes(ov))
                ) {
                  dotColor = "bg-amber-500";
                }

                return (
                  <div
                    key={idx}
                    className="bg-white/80 p-2.5 rounded-lg border border-slate-100 flex flex-col justify-between gap-1 shadow-sm"
                  >
                    <span className="text-[10px] text-slate-400 font-medium tracking-wide uppercase">
                      {item.label}
                    </span>
                    <div className="flex items-center gap-1.5 mt-1 font-semibold text-slate-800 capitalize">
                      <span className="text-sm leading-none shrink-0">
                        {item.icon}
                      </span>
                      <span className="truncate">{valLower}</span>
                    </div>
                    <div className="flex items-center gap-1 text-[9px] font-semibold text-slate-500 mt-1">
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${dotColor}`}
                      />
                      <span>
                        {dotColor === "bg-red-500"
                          ? "Critical"
                          : dotColor === "bg-amber-500"
                            ? "Warning"
                            : "Healthy"}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Interventions triggered */}
        <div className="space-y-3 pb-6">
          <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider">
            Required Interventions
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
              No interventions triggered for this level.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default SiteDrawer;

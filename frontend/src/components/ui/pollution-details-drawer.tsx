"use client";

import React from "react";
import { X, AlertTriangle, CheckCircle, Info } from "lucide-react";
import { useTranslations } from "next-intl";
import * as echarts from "echarts";
import { EChartsChart } from "./echarts-chart";
import { isVideoUrl } from "@/lib/utils";

interface PollutionDetailsDrawerProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  selectedSubCounty: any;
  onClose: () => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  incidents?: any[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onClickIncident?: (incident: any) => void;
}

export function PollutionDetailsDrawer({
  selectedSubCounty,
  onClose,
  incidents = [],
  onClickIncident,
}: PollutionDetailsDrawerProps) {
  const t = useTranslations("drawer");

  const imageUrls = React.useMemo(() => {
    return incidents
      .map((incident) => {
        if (incident.image_url) return incident.image_url;
        return incident.answers?.find(
          (a: any) => a.read_url && a.read_url.trim() !== ""
        )?.read_url;
      })
      .filter(Boolean) as string[];
  }, [incidents]);

  const breakdown: Record<string, number> = React.useMemo(() => {
    return selectedSubCounty?.properties?.incidentBreakdown || {};
  }, [selectedSubCounty]);

  const sortedBreakdown = React.useMemo(() => {
    return Object.entries(breakdown).sort((a, b) => b[1] - a[1]);
  }, [breakdown]);

  const chartOptions: echarts.EChartsOption = React.useMemo(() => {
    const reversedBreakdown = [...sortedBreakdown].reverse();
    const categories = reversedBreakdown.map(([label]) => label);
    const dataValues = reversedBreakdown.map(([, count]) => count);
    const maxVal = Math.max(...dataValues, 5);

    return {
      grid: {
        left: "2%",
        right: "2%",
        top: "5px",
        bottom: "5px",
        containLabel: false,
      },
      xAxis: {
        type: "value",
        show: false,
      },
      yAxis: {
        type: "category",
        data: categories,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { show: false },
      },
      series: [
        {
          type: "bar",
          data: dataValues,
          barWidth: 26,
          showBackground: true,
          backgroundStyle: {
            color: "#f1f5f9",
            borderRadius: 4,
          },
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: "#f97316" },
              { offset: 1, color: "#ef4444" },
            ]),
            borderRadius: 4,
          },
        },
        {
          type: "bar",
          itemStyle: {
            color: "rgba(0,0,0,0)",
          },
          barGap: "-100%",
          barWidth: 14,
          data: dataValues.map(() => maxVal),
          label: {
            show: true,
            position: "insideRight",
            formatter: (params: { dataIndex: number; name: string }) => {
              const actualCount = dataValues[params.dataIndex];
              return `${params.name} (${actualCount})`;
            },
            color: "#475569",
            fontSize: 12,
            fontWeight: "bold",
            fontFamily: "Inter, sans-serif",
            offset: [-8, 5],
          },
        },
      ],
    };
  }, [sortedBreakdown]);

  if (!selectedSubCounty) return null;

  const subCountyName =
    selectedSubCounty.properties?.name || t("selectedSubCountyFallback");
  const countyName = selectedSubCounty.properties?.county || "";
  const totalIncidents = selectedSubCounty.properties?.incidentCount || 0;

  // Determine sub-county status based on incident count
  let statusColor = "bg-green-50 text-green-700 border-green-200";
  let StatusIcon = CheckCircle;

  if (totalIncidents >= 16) {
    statusColor = "bg-red-50 text-red-700 border-red-200";
    StatusIcon = AlertTriangle;
  } else if (totalIncidents >= 6) {
    statusColor = "bg-orange-50 text-orange-700 border-orange-200";
    StatusIcon = AlertTriangle;
  } else if (totalIncidents >= 1) {
    statusColor = "bg-amber-50 text-amber-700 border-amber-200";
    StatusIcon = Info;
  }

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-white shadow-2xl flex flex-col h-full border-l border-slate-200 animate-slide-in">
      {/* Drawer Header */}
      <div className="p-6 border-b border-slate-200 flex items-center justify-between">
        <div className="flex-1 min-w-0 pr-4">
          <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">
            {countyName
              ? t("countySuffix", { countyName })
              : t("subCountyDetails")}
          </span>
          <h2 className="text-lg font-bold text-slate-800 truncate mt-0.5">
            {subCountyName}
          </h2>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-slate-600 transition-colors p-1.5 hover:bg-slate-50 rounded-full"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Drawer Body */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Status card */}
        <div
          className={`p-4 rounded-xl border flex items-start gap-3 ${statusColor}`}
        >
          <StatusIcon className="w-5 h-5 mt-0.5 shrink-0" />
          <div>
            <div className="font-bold text-sm">
              {t("reportedIncidents")}: {totalIncidents}
            </div>
            <p className="text-xs mt-1 leading-relaxed opacity-90">
              {totalIncidents > 0
                ? t("activePollutionIncidents", { count: totalIncidents })
                : t("noActivePollutionIncidents")}
            </p>
          </div>
        </div>

        {/* Incidents Breakdown section */}
        {totalIncidents > 0 ? (
          <div className="space-y-4">
            <div>
              <h3 className="font-bold text-slate-800 uppercase tracking-wider text-xs">
                {t("incidentDistribution")}
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                {t("incidentDistributionDesc")}
              </p>
            </div>

            {/* Horizontal Bar Chart with ECharts */}
            <div className="w-full">
              <EChartsChart
                options={chartOptions}
                style={{
                  height: `${Math.max(120, sortedBreakdown.length * 32)}px`,
                }}
              />
            </div>
          </div>
        ) : (
          <div className="text-center py-12 space-y-2">
            <CheckCircle className="w-12 h-12 text-slate-300 mx-auto" />
            <h4 className="font-semibold text-slate-700 text-sm">
              {t("cleanSubCounty")}
            </h4>
            <p className="text-xs text-slate-400 max-w-60 mx-auto leading-relaxed">
              {t("noReportedIncidents", { subCountyName })}
            </p>
          </div>
        )}

        {/* Reported Photos gallery */}
        <div className="space-y-4 pt-4 border-t border-slate-100">
          <div>
            <h3 className="font-bold text-slate-800 uppercase tracking-wider text-xs">
              {t("reportedPhotos")}
            </h3>
          </div>

          {imageUrls.length > 0 ? (
            <div className="grid grid-cols-2 gap-3">
              {imageUrls.map((url, idx) => {
                const isVideo = isVideoUrl(url);

                return (
                  <div
                    key={idx}
                    className="aspect-square rounded-xl overflow-hidden border border-slate-100 bg-slate-50 relative group cursor-pointer hover:border-slate-300 transition-colors"
                    onClick={() => {
                      const matchingIncident = incidents.find(
                        (inc: any) =>
                          inc.image_url === url ||
                          inc.answers?.find(
                            (a: { read_url?: string }) => a.read_url === url
                          )
                      );
                      if (matchingIncident && onClickIncident) {
                        onClickIncident(matchingIncident);
                      }
                    }}
                  >
                    {isVideo ? (
                      <video
                        src={url}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300 bg-black"
                        preload="metadata"
                        muted
                        playsInline
                      />
                    ) : (
                      /* eslint-disable-next-line @next/next/no-img-element */
                      <img
                        src={url}
                        alt={t("incidentPhotoAlt", { index: idx + 1 })}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      />
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-xs text-slate-400 italic">{t("noPhotos")}</p>
          )}
        </div>
      </div>
    </div>
  );
}

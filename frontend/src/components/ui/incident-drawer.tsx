"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { IncidentSummary } from "@/lib/api";
import { useTranslations } from "next-intl";
import {
  AlertTriangle,
  Calendar,
  MapPin,
  User,
  Image as ImageIcon,
} from "lucide-react";

type Severity = "Critical" | "Elevated" | "Moderate";

interface IncidentDrawerProps {
  incident: IncidentSummary | null;
  basinName?: string;
  onClose: () => void;
}

const SEVERITY_STYLES: Record<
  Severity,
  { badge: string; text: string; circle: string }
> = {
  Critical: {
    badge: "bg-red-50 text-red-700 border-red-200",
    text: "text-red-600",
    circle: "bg-red-500 text-red-50",
  },
  Elevated: {
    badge: "bg-amber-50 text-amber-700 border-amber-200",
    text: "text-amber-600",
    circle: "bg-amber-500 text-amber-50",
  },
  Moderate: {
    badge: "bg-slate-50 text-slate-600 border-slate-200",
    text: "text-slate-500",
    circle: "bg-slate-500 text-slate-50",
  },
};

export function IncidentDrawer({
  incident,
  basinName,
  onClose,
}: IncidentDrawerProps) {
  const t = useTranslations("incidentDrawer");
  const tLanding = useTranslations("landing");

  if (!incident) return null;

  // Resolve severity
  const qIncidentAns = incident.answers?.find(
    (a) => a.name === "incident_type" || a.question_id === 2
  );
  const optionVal = qIncidentAns?.options?.[0];
  let severity: Severity = "Moderate";
  if (optionVal !== undefined) {
    const valStr = String(optionVal);
    if (valStr === "3") severity = "Critical";
    else if (["1", "2"].includes(valStr)) severity = "Elevated";
  }

  const styles = SEVERITY_STYLES[severity];
  const incidentTypeName = qIncidentAns?.value || tLanding("pollutionReport");
  const formattedDate = incident.created_at
    ? new Date(incident.created_at).toLocaleString()
    : tLanding("unknownDate");

  // Find image answers
  const imageAnswers =
    incident.answers?.filter((a) => a.read_url && a.read_url.trim() !== "") ||
    [];

  const coords = incident.geo?.coordinates;

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-white shadow-2xl flex flex-col h-full border-l border-slate-200 animate-slide-in">
      {/* Drawer Header */}
      <div className="p-6 border-b border-slate-200 flex items-center justify-between">
        <div className="flex-1 min-w-0 pr-4">
          <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider flex items-center gap-1">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
            {t("title")}
          </span>
          <h2 className="text-lg font-bold text-slate-800 truncate mt-0.5">
            {incidentTypeName}
          </h2>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`text-xs font-bold tracking-wide uppercase px-2.5 py-1 rounded-md border shrink-0 ${styles.badge}`}
          >
            {t(severity.toLowerCase() as "moderate" | "critical" | "elevated")}
          </span>
          <Button
            variant="ghost"
            onClick={onClose}
            className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-400 hover:text-slate-600 transition-colors"
          >
            ✕
          </Button>
        </div>
      </div>

      {/* Drawer Body (Scrollable) */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Metadata section */}
        <div className="bg-slate-50 rounded-xl p-4 space-y-3 border border-slate-100 text-xs text-slate-600">
          <div className="flex items-center gap-2.5">
            <Calendar className="w-4 h-4 text-slate-400 shrink-0" />
            <div>
              <span className="font-semibold block text-slate-500">
                {t("reportedAt")}
              </span>
              <span>{formattedDate}</span>
            </div>
          </div>
          <div className="flex items-center gap-2.5">
            <User className="w-4 h-4 text-slate-400 shrink-0" />
            <div>
              <span className="font-semibold block text-slate-500">
                {t("reporter")}
              </span>
              <span>{incident.name || t("anonymousCitizen")}</span>
            </div>
          </div>
          {basinName && (
            <div className="flex items-center gap-2.5">
              <MapPin className="w-4 h-4 text-slate-400 shrink-0" />
              <div>
                <span className="font-semibold block text-slate-500">
                  {t("riverBasin")}
                </span>
                <span>{basinName}</span>
              </div>
            </div>
          )}
          {coords && (
            <div className="flex items-center gap-2.5">
              <MapPin className="w-4 h-4 text-slate-400 shrink-0" />
              <div>
                <span className="font-semibold block text-slate-500">
                  {t("gpsCoordinates")}
                </span>
                <span className="font-mono">
                  {coords[1].toFixed(5)}, {coords[0].toFixed(5)}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Photos section */}
        {imageAnswers.length > 0 && (
          <div className="space-y-2">
            <h3 className="font-bold text-slate-800 uppercase tracking-wider text-xs flex items-center gap-1.5">
              <ImageIcon className="w-4 h-4 text-slate-500" />
              {t("attachedMedia", { count: imageAnswers.length })}
            </h3>
            <div className="grid grid-cols-1 gap-4">
              {imageAnswers.map((img, i) => (
                <div
                  key={img.question_id ?? i}
                  className="relative rounded-xl overflow-hidden border border-slate-200 shadow-sm bg-slate-100 aspect-video group"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={img.read_url}
                    alt={`Incident report photo ${i + 1}`}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    loading="lazy"
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Full answers list */}
        {incident.answers && incident.answers.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              {t("questionnaireAnswers")}
            </h3>
            <div className="border border-slate-100 rounded-xl overflow-hidden divide-y divide-slate-100 text-xs">
              {incident.answers
                .filter(
                  (ans) =>
                    ans.value !== undefined &&
                    ans.value !== null &&
                    ans.value !== ""
                )
                .map((ans, idx) => (
                  <div
                    key={ans.question_id ?? idx}
                    className="p-3 bg-white flex justify-between gap-4"
                  >
                    <span className="text-slate-500 font-medium shrink-0">
                      {ans.name || `Question ${ans.question_id}`}
                    </span>
                    <span className="text-slate-800 text-right">
                      {String(ans.value)}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

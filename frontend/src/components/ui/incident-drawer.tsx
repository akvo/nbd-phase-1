"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { IncidentSummary, getSubmissionDetails } from "@/lib/api";
import { useTranslations } from "next-intl";
import { isVideoUrl } from "@/lib/utils";
import {
  AlertTriangle,
  Calendar,
  MapPin,
  User,
  Image as ImageIcon,
  Loader2,
} from "lucide-react";

interface IncidentDrawerProps {
  incident: IncidentSummary | null;
  basinName?: string;
  onClose: () => void;
}

export function IncidentDrawer({
  incident,
  basinName,
  onClose,
}: IncidentDrawerProps) {
  const t = useTranslations("incidentDrawer");
  const tLanding = useTranslations("landing");

  const [detailedIncident, setDetailedIncident] =
    React.useState<IncidentSummary | null>(null);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    if (incident?.id) {
      if (incident.answers && incident.answers.length > 0) {
        setDetailedIncident(incident);
        setLoading(false);
        return;
      }
      setLoading(true);
      getSubmissionDetails(incident.id)
        .then((data) => {
          setDetailedIncident(data as unknown as IncidentSummary);
        })
        .catch((err) => {
          console.error("Error loading incident details:", err);
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setDetailedIncident(null);
    }
  }, [incident]);

  if (!incident) return null;

  const activeIncident = detailedIncident || incident;

  const qIncidentAns = activeIncident.answers?.find(
    (a: any) => a.name === "incident_type" || a.question_id === 2
  );
  const incidentTypeName =
    qIncidentAns?.value ||
    activeIncident.incident_type_name ||
    tLanding("pollutionReport");
  const formattedDate = activeIncident.created_at
    ? new Date(activeIncident.created_at).toLocaleString()
    : tLanding("unknownDate");

  // Find image answers
  const imageAnswers =
    activeIncident.answers?.filter(
      (a: any) => a.read_url && a.read_url.trim() !== ""
    ) || [];

  const coords = activeIncident.geo?.coordinates;

  return (
    <div className="fixed inset-y-0 right-0 z-60 w-full max-w-md bg-white shadow-2xl flex flex-col h-full border-l border-slate-200 animate-slide-in">
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
              <span>{activeIncident.name || t("anonymousCitizen")}</span>
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

        {/* Loading Spinner */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-12 text-slate-400 space-y-2">
            <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
            <span className="text-xs">Loading incident details...</span>
          </div>
        )}

        {/* Photos section */}
        {!loading && imageAnswers.length > 0 && (
          <div className="space-y-2">
            <h3 className="font-bold text-slate-800 uppercase tracking-wider text-xs flex items-center gap-1.5">
              <ImageIcon className="w-4 h-4 text-slate-500" />
              {t("attachedMedia", { count: imageAnswers.length })}
            </h3>
            <div className="grid grid-cols-1 gap-4">
              {imageAnswers.map((img: any, i: number) => (
                <div
                  key={img.question_id ?? i}
                  className="relative rounded-xl overflow-hidden border border-slate-200 shadow-sm bg-slate-100 aspect-video group"
                >
                  {isVideoUrl(img.read_url) ? (
                    <video
                      src={img.read_url}
                      controls
                      className="w-full h-full object-cover"
                      preload="metadata"
                    />
                  ) : (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={img.read_url}
                      alt={t("incidentPhotoAlt", { index: i + 1 })}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      loading="lazy"
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Full answers list */}
        {!loading &&
          activeIncident.answers &&
          activeIncident.answers.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                {t("questionnaireAnswers")}
              </h3>
              <div className="border border-slate-100 rounded-xl overflow-hidden divide-y divide-slate-100 text-xs">
                {activeIncident.answers
                  .filter(
                    (ans: any) =>
                      ans.value !== undefined &&
                      ans.value !== null &&
                      ans.value !== ""
                  )
                  .map((ans: any, idx: number) => (
                    <div
                      key={ans.question_id ?? idx}
                      className="p-3 bg-white flex justify-between gap-4"
                    >
                      <span className="text-slate-500 font-medium shrink-0">
                        {ans.question_label ||
                          t("questionFallback", { id: ans.question_id ?? idx })}
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

"use client";

import React from "react";
import { Card } from "@/components/ui/card";

type Severity = "Critical" | "Elevated" | "Moderate";

interface IncidentCardProps {
  incidentTypeName: string;
  severity: Severity;
  dateReported: string;
  description: string;
  basinName?: string;
  onClick?: () => void;
}

const SEVERITY_STYLES: Record<Severity, string> = {
  Critical: "bg-red-50 text-red-700 border-red-200",
  Elevated: "bg-amber-50 text-amber-700 border-amber-200",
  Moderate: "bg-slate-50 text-slate-600 border-slate-200",
};

export function IncidentCard({
  incidentTypeName,
  severity,
  dateReported,
  description,
  basinName,
  onClick,
}: IncidentCardProps) {
  const formattedDate = dateReported
    ? new Date(dateReported).toLocaleDateString()
    : "Unknown date";

  return (
    <Card
      onClick={onClick}
      className={`p-4 border border-slate-100 hover:border-red-100 hover:shadow-md transition-all flex flex-col gap-2 relative overflow-hidden group ${
        onClick ? "cursor-pointer" : "cursor-default"
      }`}
    >
      {/* Header row */}
      <div className="flex justify-between items-start gap-2">
        <h4 className="font-bold text-slate-800 text-sm group-hover:text-red-600 transition-colors leading-tight">
          {incidentTypeName}
        </h4>
        <span
          className={`text-[10px] font-bold tracking-wide uppercase px-2 py-0.5 rounded-md border shrink-0 ${SEVERITY_STYLES[severity]}`}
        >
          {severity}
        </span>
      </div>

      {/* Description — clamped to 2 lines */}
      <p className="text-xs text-slate-500 line-clamp-2 leading-relaxed">
        {description || "No details recorded."}
      </p>

      {/* Footer row */}
      <div className="flex flex-wrap gap-1.5 mt-1">
        <span className="text-[10px] font-bold tracking-wide px-2 py-0.5 rounded-md bg-slate-50 text-slate-500 border border-slate-200 shadow-sm">
          {formattedDate}
        </span>
        {basinName && (
          <span className="text-[10px] font-bold tracking-wide px-2 py-0.5 rounded-md bg-blue-50 text-blue-600 border border-blue-100 shadow-sm">
            {basinName}
          </span>
        )}
      </div>
    </Card>
  );
}

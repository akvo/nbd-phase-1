"use client";

import React, { useState } from "react";
import { useTranslations } from "next-intl";
import { Dropdown } from "@/components/ui/dropdown";

export type MonitoringDomain = "wetland" | "pollution";

interface MapFilterProps {
  domain: MonitoringDomain;
  basins: { value: string; label: string }[];
  selectedBasin: string;
  onBasinChange: (val: string) => void;
  // Wetland
  wetlandOptions: { value: string; label: string }[];
  selectedWetland: string;
  onWetlandChange: (val: string) => void;
  selectedHealthFilter: string;
  onHealthFilterChange: (val: string) => void;
  // Pollution
  selectedIncidentType: string;
  onIncidentTypeChange: (val: string) => void;
  selectedDateFrom: string;
  onDateFromChange: (val: string) => void;
  selectedDateTo: string;
  onDateToChange: (val: string) => void;
}

const INCIDENT_TYPES = [
  { value: "", label: "All types" },
  { value: "1", label: "Water colour (darker/murkier)" },
  { value: "2", label: "Smell (bad odour)" },
  { value: "3", label: "Fish or animal kills" },
  { value: "4", label: "Storm event" },
  { value: "5", label: "High water level" },
  { value: "6", label: "Low water level" },
];

export function MapFilter({
  domain,
  basins,
  selectedBasin,
  onBasinChange,
  wetlandOptions,
  selectedWetland,
  onWetlandChange,
  selectedHealthFilter,
  onHealthFilterChange,
  selectedIncidentType,
  onIncidentTypeChange,
  selectedDateFrom,
  onDateFromChange,
  selectedDateTo,
  onDateToChange,
}: MapFilterProps) {
  const t = useTranslations("landing");
  const [isMobileExpanded, setIsMobileExpanded] = useState(false);

  const filterLabels: Record<string, string> = {
    All: t("filters.all"),
    Critical: t("filters.critical"),
    "At risk": t("filters.atRisk"),
    Healthy: t("filters.healthy"),
    Elevated: t("filters.elevated"),
  };

  const activeFilters =
    domain === "wetland"
      ? ["All", "Critical", "At risk", "Healthy"]
      : ["All", "Critical", "Elevated"];

  return (
    <div className="sticky top-16 z-40 bg-white border-b border-slate-100 shadow-sm shrink-0">
      {/* Desktop view / Mobile Row 1 */}
      <div className="max-w-full md:max-w-7xl w-full px-4 py-2 flex flex-col md:flex-row md:items-center justify-start gap-3">
        {/* Left Side / Always Visible on Mobile */}
        <div className="flex items-center justify-between md:justify-start gap-3">
          <div className="w-48 md:w-56 shrink-0">
            <Dropdown
              options={basins}
              value={selectedBasin}
              onChange={onBasinChange}
            />
          </div>

          {/* Toggle for remaining filters on mobile */}
          <button
            onClick={() => setIsMobileExpanded((p) => !p)}
            className="md:hidden flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-slate-700 bg-slate-50 px-2.5 py-1.5 rounded-lg border border-slate-200 transition-colors"
          >
            Filters
            <svg
              className={`w-3 h-3 transition-transform ${isMobileExpanded ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="2.5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>
        </div>

        {/* Desktop filters wrapper / Mobile collapsible content */}
        <div
          className={`${
            isMobileExpanded ? "flex" : "hidden"
          } md:flex flex-col md:flex-row md:items-center gap-3 w-full md:w-auto border-t md:border-t-0 pt-3 md:pt-0 mt-1 md:mt-0`}
        >
          {domain === "wetland" ? (
            <>
              {/* Wetland site selector */}
              <div className="w-full md:w-60">
                <Dropdown
                  options={wetlandOptions}
                  value={selectedWetland}
                  onChange={onWetlandChange}
                />
              </div>

              {/* Health pills */}
              <div className="flex bg-slate-100 p-1 rounded-lg w-full md:w-auto text-xs font-semibold h-9 items-center">
                {activeFilters.map((filter) => (
                  <button
                    key={filter}
                    onClick={() => onHealthFilterChange(filter)}
                    className={`flex-1 md:flex-none px-3 py-1 rounded-md text-center transition-all ${
                      selectedHealthFilter === filter
                        ? "bg-white text-slate-800 shadow"
                        : "text-slate-400 hover:text-slate-600"
                    }`}
                  >
                    {filterLabels[filter] || filter}
                  </button>
                ))}
              </div>
            </>
          ) : (
            <>
              {/* Incident type filter */}
              <div className="w-full md:w-60">
                <Dropdown
                  label="Incident Type"
                  options={INCIDENT_TYPES}
                  value={selectedIncidentType}
                  onChange={onIncidentTypeChange}
                />
              </div>

              {/* Date pickers */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full md:w-auto">
                <div className="flex flex-col gap-0.5 w-full sm:w-auto">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-1">
                    Date From
                  </span>
                  <input
                    type="date"
                    value={selectedDateFrom}
                    onChange={(e) => onDateFromChange(e.target.value)}
                    className="h-9 px-3 bg-slate-50 border border-slate-200 hover:border-slate-300 focus:border-nbd-primary/50 focus:bg-white rounded-lg text-xs font-medium text-slate-700 transition-all outline-none"
                  />
                </div>
                <div className="flex flex-col gap-0.5 w-full sm:w-auto">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-1">
                    Date To
                  </span>
                  <input
                    type="date"
                    value={selectedDateTo}
                    onChange={(e) => onDateToChange(e.target.value)}
                    className="h-9 px-3 bg-slate-50 border border-slate-200 hover:border-slate-300 focus:border-nbd-primary/50 focus:bg-white rounded-lg text-xs font-medium text-slate-700 transition-all outline-none"
                  />
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

"use client";

import React, { useState } from "react";
import { useTranslations } from "next-intl";
import { Dropdown } from "@/components/ui/dropdown";
import { MultiSelect } from "@/components/ui/multi-select";
import { DateRangePicker } from "@/components/ui/date-range-picker";
import { SlidersHorizontal, RotateCcw } from "lucide-react";

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
  selectedIncidentTypes: string[];
  onIncidentTypesChange: (val: string[]) => void;
  selectedDateFrom: string;
  onDateFromChange: (val: string) => void;
  selectedDateTo: string;
  onDateToChange: (val: string) => void;
  incidentTypeOptions?: { value: string; label: string }[];
  onClearFilters: () => void;
}

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
  selectedIncidentTypes,
  onIncidentTypesChange,
  selectedDateFrom,
  onDateFromChange,
  selectedDateTo,
  onDateToChange,
  incidentTypeOptions = [],
  onClearFilters,
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

  const hasActiveFilters =
    domain === "wetland"
      ? selectedWetland !== "" || selectedHealthFilter !== "All"
      : selectedIncidentTypes.length > 0 ||
        selectedDateFrom !== "" ||
        selectedDateTo !== "";

  return (
    <div className="sticky top-16 z-40 bg-white border-b border-slate-100 shadow-sm shrink-0">
      {/* Desktop view / Mobile Row 1 */}
      <div className="max-w-full md:max-w-7xl w-full px-4 py-2 flex flex-col md:flex-row md:items-center justify-start gap-3">
        {/* Left Side / Always Visible on Mobile */}
        <div className="flex items-center justify-between md:justify-start gap-3 w-full md:w-auto">
          <div className="flex-1 md:w-56 md:flex-none">
            <Dropdown
              options={basins}
              value={selectedBasin}
              onChange={onBasinChange}
            />
          </div>

          {/* Toggle for remaining filters on mobile */}
          <button
            onClick={() => setIsMobileExpanded((p) => !p)}
            className={`md:hidden flex items-center justify-center h-9 w-9 rounded-lg border transition-colors shrink-0 ${
              isMobileExpanded
                ? "bg-nbd-primary/10 border-nbd-primary/30 text-nbd-primary"
                : "bg-slate-50 border-slate-200 text-slate-500 hover:text-slate-700"
            }`}
            aria-label="Toggle Filters"
            data-testid="mobile-filter-toggle"
          >
            <SlidersHorizontal className="w-4 h-4" />
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
                <MultiSelect
                  options={incidentTypeOptions}
                  selectedValues={selectedIncidentTypes}
                  onChange={onIncidentTypesChange}
                  placeholder={t("filters.allTypes")}
                />
              </div>

              {/* Date pickers */}
              <DateRangePicker
                showLabel={false}
                startDate={selectedDateFrom}
                endDate={selectedDateTo}
                onStartDateChange={onDateFromChange}
                onEndDateChange={onDateToChange}
              />
            </>
          )}

          {hasActiveFilters && (
            <button
              onClick={onClearFilters}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-500 hover:text-red-600 hover:bg-red-50 border border-slate-200 hover:border-red-200 rounded-lg transition-all shadow-sm w-full md:w-auto justify-center"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              {t("filters.clear")}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

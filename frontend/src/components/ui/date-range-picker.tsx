"use client";

import React, { useState, useRef, useEffect } from "react";
import { Calendar, ChevronDown, X } from "lucide-react";
import { useTranslations } from "next-intl";

interface DateRangePickerProps {
  showLabel?: boolean;
  startDate: string;
  endDate: string;
  onStartDateChange: (date: string) => void;
  onEndDateChange: (date: string) => void;
}

export function DateRangePicker({
  showLabel = true,
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
}: DateRangePickerProps) {
  const t = useTranslations("landing");
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Local state for edits before applying
  const [tempStart, setTempStart] = useState(startDate);
  const [tempEnd, setTempEnd] = useState(endDate);

  // Keep local state in sync with props when picker is opened/closed or props change
  useEffect(() => {
    setTempStart(startDate);
    setTempEnd(endDate);
  }, [startDate, endDate, isOpen]);

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleApply = () => {
    onStartDateChange(tempStart);
    onEndDateChange(tempEnd);
    setIsOpen(false);
  };

  const handleClear = () => {
    setTempStart("");
    setTempEnd("");
    onStartDateChange("");
    onEndDateChange("");
    setIsOpen(false);
  };

  const applyPreset = (preset: "7days" | "30days" | "thisMonth") => {
    const today = new Date();
    let start = new Date();

    if (preset === "7days") {
      start.setDate(today.getDate() - 7);
    } else if (preset === "30days") {
      start.setDate(today.getDate() - 30);
    } else if (preset === "thisMonth") {
      start = new Date(today.getFullYear(), today.getMonth(), 1);
    }

    const formatDate = (date: Date) => {
      const yyyy = date.getFullYear();
      const mm = String(date.getMonth() + 1).padStart(2, "0");
      const dd = String(date.getDate()).padStart(2, "0");
      return `${yyyy}-${mm}-${dd}`;
    };

    const startStr = formatDate(start);
    const endStr = formatDate(today);

    setTempStart(startStr);
    setTempEnd(endStr);
    onStartDateChange(startStr);
    onEndDateChange(endStr);
    setIsOpen(false);
  };

  // Format display text on the button
  const getDisplayText = () => {
    if (!startDate && !endDate) {
      return t("filters.allTime") || "All Time";
    }
    if (startDate && !endDate) {
      return `${startDate} - ${t("filters.present") || "Present"}`;
    }
    if (!startDate && endDate) {
      return `${t("filters.upTo") || "Up to"} ${endDate}`;
    }
    return `${startDate} ${t("filters.to") || "to"} ${endDate}`;
  };

  const hasSelection = !!(startDate || endDate);

  return (
    <div
      className="relative inline-block w-full md:w-auto text-left"
      ref={containerRef}
    >
      <div className="flex flex-col gap-0.5 w-full md:w-60">
        {showLabel ? (
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-1">
            {t("filters.dateRange") || "Date Range"}
          </span>
        ) : (
          ""
        )}
        <div className="relative flex items-center">
          <button
            type="button"
            onClick={() => setIsOpen(!isOpen)}
            className="flex h-9 w-full items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-left text-xs font-medium text-slate-700 hover:border-slate-300 focus:border-nbd-primary/50 focus:bg-white outline-none transition-all"
            data-testid="date-range-picker-trigger"
          >
            <div className="flex items-center gap-2 truncate">
              <Calendar className="h-3.5 w-3.5 text-slate-400 shrink-0" />
              <span className="truncate">{getDisplayText()}</span>
            </div>
            <ChevronDown className="h-3 w-3 text-slate-400 shrink-0" />
          </button>
          {hasSelection && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                handleClear();
              }}
              className="absolute right-8 p-1 hover:bg-slate-200 rounded-full transition-colors"
              title={t("filters.clear") || "Clear Date Range"}
              data-testid="date-range-picker-clear"
            >
              <X className="h-3 w-3 text-slate-400 hover:text-slate-600" />
            </button>
          )}
        </div>
      </div>

      {isOpen && (
        <div
          className="absolute left-0 md:right-0 md:left-auto z-55 mt-2 w-full sm:w-80 origin-top-right rounded-xl border border-slate-100 bg-white p-4 shadow-xl ring-1 ring-black/5 animate-in fade-in slide-in-from-top-1 duration-155"
          data-testid="date-range-picker-popover"
        >
          <div className="flex flex-col gap-4">
            {/* Quick Presets */}
            <div className="flex flex-wrap gap-1.5 border-b border-slate-100 pb-3">
              <button
                type="button"
                onClick={() => applyPreset("7days")}
                className="rounded-md bg-slate-50 hover:bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-600 transition-colors"
              >
                {t("filters.last7Days") || "Last 7 Days"}
              </button>
              <button
                type="button"
                onClick={() => applyPreset("30days")}
                className="rounded-md bg-slate-50 hover:bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-600 transition-colors"
              >
                {t("filters.last30Days") || "Last 30 Days"}
              </button>
              <button
                type="button"
                onClick={() => applyPreset("thisMonth")}
                className="rounded-md bg-slate-50 hover:bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-600 transition-colors"
              >
                {t("filters.thisMonth") || "This Month"}
              </button>
            </div>

            {/* Date Inputs */}
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                  {t("filters.from") || "From"}
                </label>
                <input
                  type="date"
                  value={tempStart}
                  onChange={(e) => setTempStart(e.target.value)}
                  className="h-8 w-full rounded-md border border-slate-200 px-2 text-[11px] text-slate-700 outline-none focus:border-nbd-primary/50"
                  data-testid="date-picker-start-input"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                  {t("filters.to") || "To"}
                </label>
                <input
                  type="date"
                  value={tempEnd}
                  onChange={(e) => setTempEnd(e.target.value)}
                  className="h-8 w-full rounded-md border border-slate-200 px-2 text-[11px] text-slate-700 outline-none focus:border-nbd-primary/50"
                  data-testid="date-picker-end-input"
                />
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={handleClear}
                className="px-2.5 py-1.5 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors"
              >
                {t("filters.clear") || "Clear"}
              </button>
              <button
                type="button"
                onClick={handleApply}
                className="rounded-lg bg-nbd-primary px-3 py-1.5 text-[11px] font-bold text-white shadow-sm hover:bg-nbd-primary-hover transition-colors"
                data-testid="date-range-picker-apply"
              >
                {t("filters.apply") || "Apply"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

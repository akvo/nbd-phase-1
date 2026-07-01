"use client";

import React, { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Checkbox } from "./checkbox";

export interface MultiSelectOption {
  value: string;
  label: string;
}

interface MultiSelectProps {
  options: MultiSelectOption[];
  selectedValues: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  className?: string;
}

export function MultiSelect({
  options,
  selectedValues,
  onChange,
  placeholder = "",
  className,
}: MultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleToggleOption = (value: string) => {
    if (selectedValues.includes(value)) {
      onChange(selectedValues.filter((v) => v !== value));
    } else {
      onChange([...selectedValues, value]);
    }
  };

  const selectedLabels = options
    .filter((opt) => selectedValues.includes(opt.value))
    .map((opt) => opt.label);

  const displayValue =
    selectedLabels.length === 0
      ? placeholder
      : selectedLabels.length > 2
        ? `${selectedLabels.length} selected`
        : selectedLabels.join(", ");

  return (
    <div className={cn("relative w-full", className)} ref={containerRef}>
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex h-10 w-full items-center justify-between rounded-lg border border-grey-300 bg-white px-3.5 py-2 text-left text-sm text-nbd-text-dark transition-colors outline-none focus:border-nbd-primary focus:ring-2 focus:ring-nbd-primary/20"
      >
        <span className="truncate pr-4 font-normal text-slate-800">
          {displayValue}
        </span>
        <svg
          className={cn(
            "size-4 fill-none stroke-current text-slate-500 transition-transform duration-200",
            isOpen && "rotate-180"
          )}
          viewBox="0 0 24 24"
        >
          <polyline
            points="6 9 12 15 18 9"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute left-0 right-0 z-50 mt-1 max-h-60 overflow-y-auto rounded-lg border border-slate-100 bg-white p-2.5 shadow-lg flex flex-col gap-2.5 animate-in fade-in slide-in-from-top-1 duration-150">
          {options.map((opt) => (
            <div
              key={opt.value}
              className="flex items-center hover:bg-slate-50 p-1 rounded transition-colors"
            >
              <Checkbox
                label={opt.label}
                checked={selectedValues.includes(opt.value)}
                onChange={() => handleToggleOption(opt.value)}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

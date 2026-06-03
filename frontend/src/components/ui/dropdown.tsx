import * as React from "react";
import { cn } from "@/lib/utils";

export interface DropdownOption {
  value: string;
  label: string;
}

export interface DropdownProps extends Omit<
  React.SelectHTMLAttributes<HTMLSelectElement>,
  "value" | "onChange"
> {
  options: DropdownOption[];
  value?: string;
  onChange?: (value: string) => void;
  label?: string;
}

export function Dropdown({
  options,
  value,
  onChange,
  label,
  className,
  disabled = false,
  ...props
}: DropdownProps) {
  return (
    <div className="flex flex-col gap-1.5 w-full">
      {label && (
        <span className="text-sm font-medium text-nbd-text-dark select-none">
          {label}
        </span>
      )}
      <div className="relative w-full">
        <select
          value={value}
          disabled={disabled}
          onChange={(e) => onChange?.(e.target.value)}
          className={cn(
            "h-10 w-full rounded-lg border border-grey-300 bg-white px-3.5 py-2 text-sm text-nbd-text-dark transition-colors outline-none focus-visible:border-nbd-primary focus-visible:ring-2 focus-visible:ring-nbd-primary/20 disabled:cursor-not-allowed disabled:bg-nbd-disabled disabled:text-nbd-disabled-text appearance-none",
            className,
          )}
          {...props}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3.5 text-nbd-text-dark">
          <svg className="size-4 fill-none stroke-current" viewBox="0 0 24 24">
            <polyline
              points="6 9 12 15 18 9"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      </div>
    </div>
  );
}

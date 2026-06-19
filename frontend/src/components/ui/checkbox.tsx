"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface CheckboxProps extends Omit<
  React.InputHTMLAttributes<HTMLInputElement>,
  "onChange"
> {
  label?: string;
  checked?: boolean;
  onChange?: (checked: boolean) => void;
}

export function Checkbox({
  label,
  checked = false,
  onChange,
  disabled = false,
  className,
  ...props
}: CheckboxProps) {
  return (
    <label
      className={cn(
        "flex items-center gap-3 cursor-pointer select-none",
        disabled && "cursor-not-allowed opacity-50"
      )}
    >
      <div className="relative">
        <input
          type="checkbox"
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange?.(e.target.checked)}
          className="sr-only"
          {...props}
        />
        <div
          className={cn(
            "flex size-5 items-center justify-center rounded border transition-colors focus-visible:ring-2 focus-visible:ring-nbd-primary/50",
            checked
              ? "border-nbd-primary bg-nbd-primary text-white"
              : "border-grey-300 bg-white",
            disabled && "bg-nbd-disabled border-nbd-disabled-text",
            className
          )}
        >
          {checked && (
            <svg
              className="size-3.5 fill-current stroke-current stroke-2"
              viewBox="0 0 24 24"
            >
              <polyline
                points="20 6 9 17 4 12"
                fill="none"
                stroke="currentColor"
              />
            </svg>
          )}
        </div>
      </div>
      {label && (
        <span className="text-sm font-medium text-nbd-text-dark">{label}</span>
      )}
    </label>
  );
}

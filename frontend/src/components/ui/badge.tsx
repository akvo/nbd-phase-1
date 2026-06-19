import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "primary" | "success" | "warning" | "danger" | "neutral";
}

export function Badge({
  variant = "primary",
  className,
  ...props
}: BadgeProps) {
  const variants = {
    primary: "bg-nbd-secondary text-nbd-primary hover:bg-nbd-secondary-hover",
    success: "bg-green-100 text-green-700 hover:bg-green-200",
    warning: "bg-yellow-100 text-yellow-700 hover:bg-yellow-200",
    danger: "bg-red-100 text-red-700 hover:bg-red-200",
    neutral: "bg-grey-300 text-grey-700 hover:bg-grey-500",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}

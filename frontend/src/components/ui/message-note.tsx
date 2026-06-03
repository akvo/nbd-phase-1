import * as React from "react";
import { cn } from "@/lib/utils";

export interface MessageNoteProps extends React.HTMLAttributes<HTMLDivElement> {
  type?: "info" | "success" | "warning" | "error";
  title?: string;
  children?: React.ReactNode;
}

export function MessageNote({
  type = "info",
  title,
  children,
  className,
  ...props
}: MessageNoteProps) {
  const styles = {
    info: "border-nbd-primary bg-nbd-light-bg text-nbd-primary-hover",
    success: "border-green-500 bg-green-50 text-green-700",
    warning: "border-yellow-500 bg-yellow-50 text-yellow-700",
    error: "border-red-500 bg-red-50 text-red-700",
  };

  const icons = {
    info: (
      <svg
        className="size-5 shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="12" cy="12" r="10" />
        <path d="M12 16v-4" />
        <path d="M12 8h.01" />
      </svg>
    ),
    success: (
      <svg
        className="size-5 shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth="2"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    ),
    warning: (
      <svg
        className="size-5 shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth="2"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
    ),
    error: (
      <svg
        className="size-5 shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth="2"
      >
        <circle cx="12" cy="12" r="10" />
        <line x1="15" y1="9" x2="9" y2="15" />
        <line x1="9" y1="9" x2="15" y2="15" />
      </svg>
    ),
  };

  return (
    <div
      className={cn(
        "flex gap-3 rounded-lg border-l-4 p-4 text-sm font-medium transition-all shadow-sm",
        styles[type],
        className,
      )}
      {...props}
    >
      {icons[type]}
      <div className="flex flex-col gap-1">
        {title && <span className="font-bold">{title}</span>}
        <div className="text-sm opacity-90">{children}</div>
      </div>
    </div>
  );
}

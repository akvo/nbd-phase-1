"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface LoaderProps extends React.HTMLAttributes<HTMLDivElement> {
  message?: string;
}

export function Loader({
  message = "Loading...",
  className,
  ...props
}: LoaderProps) {
  return (
    <div
      className={cn(
        "h-full w-full min-h-[200px] bg-slate-50 rounded-xl flex flex-col items-center justify-center gap-3 text-slate-500 font-medium border border-slate-100 shadow-sm",
        className
      )}
      {...props}
    >
      <div className="relative w-10 h-10 flex items-center justify-center">
        <span className="absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75 animate-ping"></span>
        <span className="relative inline-flex rounded-full h-5 w-5 bg-teal-600 border border-white shadow"></span>
      </div>
      <p className="text-sm font-semibold tracking-wide text-teal-700 animate-pulse">
        {message}
      </p>
    </div>
  );
}

export default Loader;

"use client";

import React from "react";
import { cn } from "@/lib/utils";

type MapLegendProps = React.HTMLAttributes<HTMLDivElement>;

export function MapLegend({ className, ...props }: MapLegendProps) {
  return (
    <div
      className={cn(
        "absolute left-4 md:left-[25rem] right-auto top-20 z-20 pointer-events-none bg-slate-900/60 backdrop-blur-none text-white px-3 py-2 rounded-lg text-xs flex flex-col gap-1.5 shadow-lg border border-slate-700/50",
        className
      )}
      {...props}
    >
      <div className="font-bold border-b border-slate-700/60 pb-1">Legend</div>
      <div className="flex items-center gap-2">
        <span className="w-2.5 h-2.5 rounded-full bg-green-500" />
        <span>Healthy (A / B)</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
        <span>At Risk (C)</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
        <span>Critical (D / E)</span>
      </div>
      <div className="flex items-center gap-2 border-t border-slate-700/60 pt-1">
        <span className="w-2.5 h-2.5 rounded bg-red-600 flex items-center justify-center text-[8px] font-bold">
          !
        </span>
        <span>Pollution Incident</span>
      </div>
    </div>
  );
}

export default MapLegend;

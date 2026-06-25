"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { useTranslations } from "next-intl";

type MapLegendProps = React.HTMLAttributes<HTMLDivElement> & {
  domain?: "wetland" | "pollution";
};

export function MapLegend({
  className,
  domain = "wetland",
  ...props
}: MapLegendProps) {
  const t = useTranslations("legend");

  return (
    <div
      className={cn(
        "absolute left-4 md:left-100 right-auto top-20 z-20 pointer-events-none bg-slate-900/60 backdrop-blur-none text-white px-3 py-2 rounded-lg text-xs flex flex-col gap-1.5 shadow-lg border border-slate-700/50",
        className
      )}
      {...props}
    >
      <div className="font-bold border-b border-slate-700/60 pb-1">
        {t("title")}
      </div>
      {domain === "wetland" && (
        <>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-green-500" />
            <span>{t("healthy")}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
            <span>{t("atRisk")}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
            <span>{t("critical")}</span>
          </div>
        </>
      )}

      {domain === "pollution" && (
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded bg-red-600 flex items-center justify-center text-[8px] font-bold text-white">
              !
            </span>
            <span>{t("criticalSeverity")}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded bg-amber-500 flex items-center justify-center text-[8px] font-bold text-white">
              !
            </span>
            <span>{t("elevatedSeverity")}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded bg-yellow-500 flex items-center justify-center text-[8px] font-bold text-white">
              !
            </span>
            <span>{t("moderateSeverity")}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default MapLegend;

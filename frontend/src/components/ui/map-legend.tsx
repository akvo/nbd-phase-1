"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { useTranslations } from "next-intl";
import { EChartsChart } from "./echarts-chart";
import { useDomainOptional } from "@/context/domain-context";

type MapLegendProps = React.HTMLAttributes<HTMLDivElement> & {
  domain?: "wetland" | "pollution";
  draggable?: boolean;
};

export function MapLegend({
  className,
  domain = "wetland",
  draggable = false,
  style,
  ...props
}: MapLegendProps) {
  const t = useTranslations("legend");
  const context = useDomainOptional();
  const pollutionRange = context?.pollutionRange ?? [0, 20];

  const debounceTimerRef = React.useRef<NodeJS.Timeout | null>(null);

  const debouncedSetPollutionRange = React.useCallback(
    (range: [number, number]) => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      debounceTimerRef.current = setTimeout(() => {
        if (context?.setPollutionRange) {
          context.setPollutionRange(range);
        }
      }, 200);
    },
    [context]
  );

  React.useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  const [position, setPosition] = React.useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = React.useState(false);
  const dragRef = React.useRef({ startX: 0, startY: 0, posX: 0, posY: 0 });

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!draggable || e.button !== 0) return;
    const target = e.target as HTMLElement;
    if (
      target.closest("button") ||
      target.closest("input") ||
      target.closest("a")
    ) {
      return;
    }
    setIsDragging(true);
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      posX: position.x,
      posY: position.y,
    };
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!isDragging) return;
    const deltaX = e.clientX - dragRef.current.startX;
    const deltaY = e.clientY - dragRef.current.startY;
    setPosition({
      x: dragRef.current.posX + deltaX,
      y: dragRef.current.posY + deltaY,
    });
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!isDragging) return;
    setIsDragging(false);
    e.currentTarget.releasePointerCapture(e.pointerId);
  };

  const dynamicStyles = draggable
    ? {
        transform: `translate(${position.x}px, ${position.y}px)`,
        cursor: isDragging ? "grabbing" : "grab",
      }
    : {};

  return (
    <div
      className={cn(
        "absolute left-4 md:left-100 right-auto top-32 z-20 pointer-events-auto bg-slate-900/60 backdrop-blur-none text-white px-3 py-2 rounded-lg text-xs flex flex-col gap-1.5 shadow-lg border border-slate-700/50",
        draggable &&
          "select-none active:scale-[1.01] transition-transform duration-75",
        className
      )}
      style={{
        ...dynamicStyles,
        ...style,
      }}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
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
        <div className="w-44 select-none flex flex-col gap-1 items-center">
          <div className="sr-only">
            <span>{t("high")}</span>
            <span>{t("moderate")}</span>
            <span>{t("low")}</span>
            <span>{t("none")}</span>
          </div>
          <div className="w-full h-6">
            <EChartsChart
              options={{
                tooltip: { show: false },
                grid: { top: 0, bottom: 0, left: 0, right: 0 },
                xAxis: { show: false },
                yAxis: { show: false },
                visualMap: {
                  type: "continuous",
                  min: 0,
                  max: 20,
                  range: pollutionRange,
                  calculable: true,
                  orient: "horizontal",
                  left: "center",
                  top: "center",
                  itemWidth: 16,
                  itemHeight: 140,
                  inRange: {
                    color: ["#f1f5f9", "#fef3c7", "#f97316", "#dc2626"],
                  },
                },
                series: [],
              }}
              onEvents={{
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                datarangeselected: (params: any) => {
                  if (params.selected && params.selected.length === 2) {
                    debouncedSetPollutionRange([
                      params.selected[0],
                      params.selected[1],
                    ]);
                  }
                },
              }}
              className="w-full h-full"
            />
          </div>
          {/* HTML labels aligned under the 140px gradient bar */}
          <div className="flex justify-between w-[140px] text-[10px] text-slate-300 font-medium px-0.5 mt-0.5">
            <span>{t("none")}</span>
            <span>{t("high")}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default MapLegend;

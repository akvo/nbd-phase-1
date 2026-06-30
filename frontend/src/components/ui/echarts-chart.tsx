"use client";

import React, { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface EChartsChartProps {
  options: echarts.EChartsOption;
  className?: string;
  style?: React.CSSProperties;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onEvents?: Record<string, (params: any) => void>;
}

export function EChartsChart({
  options,
  className,
  style,
  onEvents,
}: EChartsChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    // Initialize chart
    const chart = echarts.init(chartRef.current);
    chartInstance.current = chart;

    // Set initial options
    chart.setOption(options);

    // Bind events
    if (onEvents) {
      Object.entries(onEvents).forEach(([eventName, handler]) => {
        chart.on(eventName, handler);
      });
    }

    // Resize handler
    const handleResize = () => {
      chart.resize();
    };

    window.addEventListener("resize", handleResize);
    window.addEventListener("beforeprint", handleResize);
    window.addEventListener("afterprint", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("beforeprint", handleResize);
      window.removeEventListener("afterprint", handleResize);
      if (onEvents && chartInstance.current) {
        Object.entries(onEvents).forEach(([eventName, handler]) => {
          chartInstance.current?.off(eventName, handler);
        });
      }
      chart.dispose();
    };
  }, [options, onEvents]);

  return (
    <div
      ref={chartRef}
      className={className}
      style={{ width: "100%", height: "100%", ...style }}
    />
  );
}

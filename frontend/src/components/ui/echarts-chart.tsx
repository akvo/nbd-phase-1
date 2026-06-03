"use client";

import React, { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface EChartsChartProps {
  options: echarts.EChartsOption;
  className?: string;
  style?: React.CSSProperties;
}

export function EChartsChart({ options, className, style }: EChartsChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    // Initialize chart
    const chart = echarts.init(chartRef.current);
    chartInstance.current = chart;

    // Set initial options
    chart.setOption(options);

    // Resize handler
    const handleResize = () => {
      chart.resize();
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.dispose();
    };
  }, [options]);

  return (
    <div
      ref={chartRef}
      className={className}
      style={{ width: "100%", height: "100%", ...style }}
    />
  );
}

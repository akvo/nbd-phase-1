"use client";

import React from "react";
import { Leaf, TriangleAlert } from "lucide-react";
import { MonitoringDomain } from "@/lib/api";

import { useTranslations } from "next-intl";

interface DomainSelectorProps {
  value: MonitoringDomain;
  onChange: (domain: MonitoringDomain) => void;
}

const DOMAINS: {
  value: MonitoringDomain;
  labelKey: "wetlandMonitoring" | "pollutionReports";
  Icon: React.ElementType;
}[] = [
  { value: "wetland", labelKey: "wetlandMonitoring", Icon: Leaf },
  { value: "pollution", labelKey: "pollutionReports", Icon: TriangleAlert },
];

export function DomainSelector({ value, onChange }: DomainSelectorProps) {
  const t = useTranslations("landing");

  return (
    <div className="flex bg-slate-100 p-1 rounded-lg w-full text-xs font-semibold">
      {DOMAINS.map(({ value: domain, labelKey, Icon }) => {
        const label = t(labelKey);
        return (
          <button
            key={domain}
            id={`domain-selector-${domain}`}
            onClick={() => onChange(domain)}
            className={`flex-1 py-1.5 rounded-md text-center transition-all flex items-center justify-center gap-1.5 ${
              value === domain
                ? "bg-white text-slate-800 shadow"
                : "text-slate-400 hover:text-slate-600"
            }`}
            aria-pressed={value === domain}
            aria-label={t("switchDomain", { domain: label })}
          >
            <Icon className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">{label}</span>
          </button>
        );
      })}
    </div>
  );
}

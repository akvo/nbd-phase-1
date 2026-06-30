"use client";

import React from "react";

interface ManagementAction {
  label: string;
  description: string;
}

interface InterventionsListProps {
  managementActions: ManagementAction[];
  t: (key: string) => string;
}

export function InterventionsList({
  managementActions,
  t,
}: InterventionsListProps) {
  return (
    <div className="space-y-3 print-avoid-break">
      <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider">
        {t("requiredInterventions")}
      </h3>
      {managementActions.length > 0 ? (
        <div className="space-y-3">
          {managementActions.map((action, i) => (
            <div
              key={i}
              className="p-4 border border-slate-100 rounded-xl bg-slate-50/50 shadow-sm"
            >
              <div className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <span className="text-amber-500">⚠️</span> {action.label}
              </div>
              <div className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                {action.description}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-xs text-slate-400 italic bg-slate-50 p-4 rounded-xl text-center border border-dashed border-slate-200">
          {t("noInterventions")}
        </div>
      )}
    </div>
  );
}

"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

export type MonitoringDomain = "wetland" | "pollution";

interface DomainContextType {
  selectedDomain: MonitoringDomain;
  setSelectedDomain: (domain: MonitoringDomain) => void;
}

const DomainContext = createContext<DomainContextType | null>(null);

export function DomainProvider({
  children,
  initialDomain = "wetland",
}: {
  children: React.ReactNode;
  initialDomain?: MonitoringDomain;
}) {
  const [selectedDomain, setSelectedDomain] =
    useState<MonitoringDomain>(initialDomain);

  return (
    <DomainContext.Provider value={{ selectedDomain, setSelectedDomain }}>
      {children}
    </DomainContext.Provider>
  );
}

export function useDomain() {
  const context = useContext(DomainContext);
  if (!context) {
    throw new Error("useDomain must be used within a DomainProvider");
  }
  return context;
}

export function useDomainOptional() {
  return useContext(DomainContext);
}

"use client";

import React, { createContext, useContext, useState, useCallback } from "react";

export type MonitoringDomain = "wetland" | "pollution";

interface DomainContextType {
  selectedDomain: MonitoringDomain;
  setSelectedDomain: (domain: MonitoringDomain) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  selectedSite: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  setSelectedSite: (site: any) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  selectedIncident: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  setSelectedIncident: (incident: any) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  selectedSubCounty: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  setSelectedSubCounty: (subCounty: any) => void;
  closeAllDrawers: () => void;
  pollutionRange: [number, number];
  setPollutionRange: (range: [number, number]) => void;
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
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [selectedSite, setSelectedSite] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [selectedIncident, setSelectedIncident] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [selectedSubCounty, setSelectedSubCounty] = useState<any>(null);
  const [pollutionRange, setPollutionRange] = useState<[number, number]>([
    0, 20,
  ]);

  const closeAllDrawers = useCallback(() => {
    setSelectedSite(null);
    setSelectedIncident(null);
    setSelectedSubCounty(null);
  }, []);

  return (
    <DomainContext.Provider
      value={{
        selectedDomain,
        setSelectedDomain,
        selectedSite,
        setSelectedSite,
        selectedIncident,
        setSelectedIncident,
        selectedSubCounty,
        setSelectedSubCounty,
        closeAllDrawers,
        pollutionRange,
        setPollutionRange,
      }}
    >
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

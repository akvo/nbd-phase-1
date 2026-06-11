"use client";

import React, { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Dropdown } from "@/components/ui/dropdown";
import { SiteDrawer } from "@/components/ui/site-drawer";
import { SiteHeader } from "@/components/ui/site-header";
import { Loader } from "@/components/ui/loader";
import { MapLegend } from "@/components/ui/map-legend";

import { getBasins } from "@/lib/api";

// Load static mock database
import mockData from "../../public/data/mock_map_data.json";

const SHOW_BASIN_SELECTOR = true;

const MapViewer = dynamic(() => import("@/components/ui/map-viewer"), {
  ssr: false,
  loading: () => <Loader message="Loading Regional Map..." />,
});

export default function Home() {
  const [selectedBasin, setSelectedBasin] = useState("MARA");
  const [selectedHealthFilter, setSelectedHealthFilter] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSite, setSelectedSite] = useState<any>(null);
  const [isListCollapsed, setIsListCollapsed] = useState(true);

  const [basinGeometries, setBasinGeometries] = useState<Record<string, any>>({});
  const [activeGeometry, setActiveGeometry] = useState<any>(null);

  useEffect(() => {
    getBasins()
      .then((data) => {
        const geomMap: Record<string, any> = {};
        data.forEach((b: any) => {
          if (b.code && b.geom) {
            geomMap[b.code] = b.geom;
          }
        });
        setBasinGeometries(geomMap);
        if (geomMap[selectedBasin]) {
          setActiveGeometry(geomMap[selectedBasin]);
        }
      })
      .catch((err) => console.error("Error loading basin geometries:", err));
  }, []);

  useEffect(() => {
    if (basinGeometries[selectedBasin]) {
      setActiveGeometry(basinGeometries[selectedBasin]);
    } else {
      setActiveGeometry(null);
    }
  }, [selectedBasin, basinGeometries]);

  // 1. Filtered sites based on basin, health, and search
  const filteredSites = mockData.sites.filter((site) => {
    // Basin filter
    if (site.basin !== selectedBasin) return false;

    // Health category filter
    if (selectedHealthFilter !== "All") {
      const hClass = site.current_health_class;
      if (selectedHealthFilter === "Critical" && !["D", "E"].includes(hClass))
        return false;
      if (selectedHealthFilter === "At risk" && hClass !== "C") return false;
      if (selectedHealthFilter === "Healthy" && !["A", "B"].includes(hClass))
        return false;
    }

    // Search query filter
    if (searchQuery.trim() !== "") {
      const query = searchQuery.toLowerCase();
      const matchName = site.site_name.toLowerCase().includes(query);
      const matchId = site.site_id.toLowerCase().includes(query);
      const matchCountry = site.country.toLowerCase().includes(query);
      if (!matchName && !matchId && !matchCountry) return false;
    }

    return true;
  });

  // 2. Filtered incidents based on basin
  const filteredIncidents = mockData.incidents.filter((incident) => {
    if (incident.basin !== selectedBasin) return false;

    // Also filter incidents by severity matching the selectedHealthFilter
    if (selectedHealthFilter !== "All") {
      if (selectedHealthFilter === "Critical" && incident.status !== "Critical")
        return false;
      if (selectedHealthFilter === "At risk" && incident.status !== "Elevated")
        return false;
      if (selectedHealthFilter === "Healthy" && incident.status !== "Moderate")
        return false;
    }

    return true;
  });

  // 3. Map markers configuration combining sites and incidents
  const mapMarkers = [
    ...filteredSites.map((site) => ({
      position: site.coordinates as [number, number],
      popupText: `${site.site_name} (${site.current_health_class})`,
      type: "site" as const,
      status: site.current_health_class,
    })),
    ...filteredIncidents.map((incident) => ({
      position: incident.coordinates as [number, number],
      popupText: `Incident: ${incident.incident_type.replace(/_/g, " ")} (${incident.status})`,
      type: "incident" as const,
      status: incident.status,
    })),
  ];

  // Map center logic (center of Mara or Sio depending on selection)
  const mapCenter: [number, number] =
    selectedBasin === "MARA" ? [-1.2345, 34.5678] : [0.22, 34.2];
  const mapZoom = selectedBasin === "MARA" ? 11 : 12;

  const dropdownOptions = mockData.basins.map((b) => ({
    value: b.basin_id,
    label: b.basin_name,
  }));

  return (
    <main className="min-h-screen bg-slate-50 flex flex-col font-sans relative overflow-hidden">
      {/* Header Navigation */}
      <SiteHeader showActions={true} />

      {/* Main content body with relative layout */}
      <div className="flex-1 relative overflow-hidden flex flex-col md:flex-row">
        {/* Map GIS Canvas - fills parent container */}
        <div className="absolute inset-0 z-0">
          <MapViewer
            center={mapCenter}
            zoom={mapZoom}
            markers={mapMarkers}
            basinGeometry={activeGeometry}
            zoomOffsetClass={
              isListCollapsed
                ? "max-md:[&_.leaflet-bottom.leaflet-right]:!bottom-[35vh] max-md:[&_.leaflet-bottom.leaflet-right]:transition-all max-md:[&_.leaflet-bottom.leaflet-right]:duration-300"
                : "max-md:[&_.leaflet-bottom.leaflet-right]:!bottom-[57vh] max-md:[&_.leaflet-bottom.leaflet-right]:transition-all max-md:[&_.leaflet-bottom.leaflet-right]:duration-300"
            }
            className="h-full w-full"
          />
        </div>

        {/* Left Side Panel (Mobile: floating bottom sheet, Desktop: sidebar panel) */}
        <section className="absolute bottom-0 left-0 right-0 md:relative md:bottom-auto md:left-auto md:right-auto md:w-96 bg-white/95 backdrop-blur-sm border-t md:border-t-0 md:border-r border-slate-200 z-10 flex flex-col max-h-[55vh] md:max-h-full h-auto md:h-full shadow-2xl md:shadow-lg rounded-t-2xl md:rounded-t-none">
          {/* Drag indicator for mobile */}
          <div className="w-12 h-1 bg-slate-300 rounded-full mx-auto my-2.5 shrink-0 md:hidden" />

          {/* Basin selector */}
          <div className="p-4 border-b border-slate-100 space-y-4 shrink-0">
            {SHOW_BASIN_SELECTOR &&
            <Dropdown
              label="Basin Region"
              options={dropdownOptions}
              value={selectedBasin}
              onChange={(val) => {
                setSelectedBasin(val);
                setSelectedSite(null);
              }}
            />
            }

            {/* Health filter toggles */}
            <div className="flex bg-slate-100 p-1 rounded-lg w-full text-xs font-semibold">
              {["All", "Critical", "At risk", "Healthy"].map((filter) => (
                <button
                  key={filter}
                  onClick={() => setSelectedHealthFilter(filter)}
                  className={`flex-1 py-1.5 rounded-md text-center transition-all ${selectedHealthFilter === filter
                      ? "bg-white text-slate-800 shadow"
                      : "text-slate-400 hover:text-slate-600"
                    }`}
                >
                  {filter}
                </button>
              ))}
            </div>

            {/* Search Input */}
            <Input
              type="text"
              placeholder="Search field, area, water source"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-50 border-slate-200 focus:bg-white text-sm"
            />
          </div>

          {/* Site cards list */}
          <div className={`p-4 flex flex-col min-h-0 ${isListCollapsed ? "shrink-0" : "flex-1 overflow-y-auto"}`}>
            <div
              className="text-xs font-bold text-slate-400 uppercase tracking-wider flex justify-between items-center cursor-pointer select-none hover:text-slate-600 transition-colors py-1"
              onClick={() => setIsListCollapsed(!isListCollapsed)}
            >
              <div className="flex items-center w-full justify-between gap-2">
                {filteredIncidents.length > 0 && (
                  <span className="text-red-500 normal-case font-medium">
                    {filteredIncidents.length} Incident{filteredIncidents.length > 1 ? "s" : ""}
                  </span>
                )}
                <svg
                  className={`w-3.5 h-3.5 transform transition-transform duration-200 ${isListCollapsed ? "" : "rotate-180"
                    }`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth="2.5"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>

            {!isListCollapsed && (
              <div className="mt-3 space-y-3 overflow-y-auto pr-1 flex-1">
                {filteredSites.length > 0 ? (
                  filteredSites.map((site) => {
                    const isCritical = ["D", "E"].includes(
                      site.current_health_class,
                    );
                    const isAtRisk = site.current_health_class === "C";

                    return (
                      <Card
                        key={site.site_id}
                        onClick={() => setSelectedSite(site)}
                        className="p-4 hover:shadow-md transition-all border border-slate-100 hover:border-teal-100 cursor-pointer flex flex-col gap-3 relative overflow-hidden group"
                      >
                        <div className="flex justify-between items-start">
                          <div>
                            <h4 className="font-bold text-slate-800 text-sm group-hover:text-teal-600 transition-colors">
                              {site.site_name}
                            </h4>
                            <span className="text-xs text-slate-400">
                              {site.site_id}
                            </span>
                          </div>
                          <div
                            className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${isCritical
                                ? "bg-red-50 text-red-600"
                                : isAtRisk
                                  ? "bg-amber-50 text-amber-600"
                                  : "bg-green-50 text-green-600"
                              }`}
                          >
                            {site.current_health_class}
                          </div>
                        </div>

                        <div className="space-y-1">
                          <div className="text-xs text-slate-500 font-medium">
                            Community Signal: {site.community_signal}
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full ${isCritical
                                    ? "bg-red-500"
                                    : isAtRisk
                                      ? "bg-amber-500"
                                      : "bg-green-500"
                                  }`}
                                style={{ width: `${site.progress_percent}%` }}
                              />
                            </div>
                            <span className="text-[10px] font-bold text-slate-600">
                              {site.progress_percent}%
                            </span>
                          </div>
                        </div>

                        <div className="flex gap-1.5">
                          <Badge variant={site.is_approved ? "success" : "warning"}>
                            {site.is_approved ? "Approved" : "Pending"}
                          </Badge>
                          {site.is_ik_adjusted && (
                            <Badge variant="primary">IK-adjusted</Badge>
                          )}
                          <div className="flex items-center gap-1 text-xs text-slate-700 bg-white border border-slate-200 px-2.5 py-1 rounded-full shadow-sm">
          <svg className="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span>{site.country}</span>
        </div>
                        </div>
                      </Card>
                    );
                  })
                ) : (
                  <div className="text-sm text-slate-400 italic py-8 text-center">
                    No active stations matching filters.
                  </div>
                )}
              </div>
            )}
          </div>
        </section>
      </div>

      {/* Floating Side Info Overlay of Legend */}
      <MapLegend />

      {/* Site granular details Drawer panel */}
      <SiteDrawer site={selectedSite} onClose={() => setSelectedSite(null)} />
    </main>
  );
}

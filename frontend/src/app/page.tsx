"use client";

import React, { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Dropdown } from "@/components/ui/dropdown";
import { SiteDrawer } from "@/components/ui/site-drawer";
import { SiteHeader } from "@/components/ui/site-header";
import { Loader } from "@/components/ui/loader";
import { MapLegend } from "@/components/ui/map-legend";

import { getBasins, getSites, getSubmissions } from "@/lib/api";

const SHOW_BASIN_SELECTOR = true;

const MapViewer = dynamic(() => import("@/components/ui/map-viewer"), {
  ssr: false,
  loading: () => <Loader message="Loading Regional Map..." />,
});

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mapDbSiteToDrawerSite = (site: any): any => {
  if (!site) return null;
  const coords = site.geom?.coordinates;
  const healthClass = site.status?.health_class || "C";
  const compositeScore = site.status?.composite_score ?? 0.5;
  const ikAdjustedScore = site.status?.ik_adjusted_score ?? compositeScore;

  // Re-map management actions list
  const management_actions = (site.management_actions || []).map(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (action: any) => ({
      label: action.label,
      description: action.description,
    })
  );

  // Match country from backend, fallback to prefix MS1 (Tanzania), SIO (Kenya)
  const country =
    site.country || (site.code?.includes("SIO") ? "Kenya" : "Tanzania");

  // Parse dynamic score breakdown from status if available
  const score_breakdown = site.status?.score_breakdown || {
    physico_chemical: {
      score: compositeScore,
      label: "Physico-chemical",
      icon: "FlaskConical",
    },
    catchment_hydrological: {
      score: compositeScore,
      label: "Catchment / hydro",
      icon: "Waves",
    },
    ecological: {
      score: compositeScore,
      label: "Ecological",
      icon: "Leaf",
    },
    governance: {
      score: 0.55,
      label: "Governance",
      icon: "ShieldCheck",
    },
  };

  return {
    site_id: site.code,
    site_name: site.name,
    country,
    basin: site.code?.includes("SIO") ? "SIO_SITEKO" : "MARA",
    current_health_class: healthClass,
    current_score: ikAdjustedScore,
    last_updated: site.status?.sampling_date || new Date().toISOString(),
    coordinates: coords ? [coords[1], coords[0]] : [0, 0],
    community_signal: site.description || "No signal details recorded.",
    progress_percent: Math.round(ikAdjustedScore * 100),
    is_approved: true,
    is_ik_adjusted:
      site.status?.ik_adjusted_score !== site.status?.composite_score,
    details: {
      score_breakdown,
      physico_chemical: {
        group_score: score_breakdown.physico_chemical?.score ?? compositeScore,
        ph: site.status?.metrics?.ph?.value ?? 7.2,
        dissolved_oxygen: site.status?.metrics?.dissolved_oxygen?.value ?? 6.5,
        temperature: site.status?.metrics?.temperature?.value ?? 22.0,
        weights: { ph: 0.3704, dissolved_oxygen: 0.6297 },
      },
      catchment_hydrological: {
        group_score:
          score_breakdown.catchment_hydrological?.score ?? compositeScore,
      },
      ecological: {
        group_score: score_breakdown.ecological?.score ?? compositeScore,
      },
      ik_signal: {
        encoded_signal_value:
          site.status?.ik_signal?.encoded_signal_value ??
          site.status?.ik_adjusted_score ??
          0.5,
        fish_abundance: site.status?.ik_signal?.fish_abundance ?? "Same",
        water_clarity: site.status?.ik_signal?.water_clarity ?? "Same",
        vegetation_cover: site.status?.ik_signal?.vegetation_cover ?? "Same",
        pollution_events: site.status?.ik_signal?.pollution_events ?? "None",
      },
      management_actions,
      water_level: site.status?.metrics?.water_level?.value || "MEDIUM",
      metrics: {
        ph: site.status?.metrics?.ph || {
          value: site.status?.metrics?.ph?.value ?? 7.2,
          unit: "-",
          status: "Normal",
          label: "pH",
          icon: "FlaskConical",
        },
        dissolved_oxygen: site.status?.metrics?.dissolved_oxygen || {
          value: site.status?.metrics?.dissolved_oxygen?.value ?? 6.5,
          unit: "mg/L",
          status: "Normal",
          label: "Dissolved O₂",
          icon: "Droplets",
        },
        temperature: site.status?.metrics?.temperature || {
          value: site.status?.metrics?.temperature?.value ?? 22.0,
          unit: "°C",
          status: "Normal",
          label: "Temperature",
          icon: "Thermometer",
        },
        water_level: site.status?.metrics?.water_level || {
          value: site.status?.metrics?.water_level?.value || "MEDIUM",
          unit: "-",
          status: "Normal",
          label: "Water level",
          icon: "Waves",
        },
        turbidity: site.status?.metrics?.turbidity || {
          value: 38,
          unit: "NTU",
          status: "Normal",
          label: "Turbidity",
          icon: "EyeOff",
        },
        macroinvertebrate: site.status?.metrics?.macroinvertebrate || {
          value: 0.48,
          unit: "index",
          status: "Normal",
          label: "Macroinvertebrate",
          icon: "Bug",
        },
      },
    },
  };
};

export default function Home() {
  const [selectedBasin, setSelectedBasin] = useState("MARA");
  const [selectedHealthFilter, setSelectedHealthFilter] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [selectedSite, setSelectedSite] = useState<any>(null);
  const [isListCollapsed, setIsListCollapsed] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [basinGeometries, setBasinGeometries] = useState<Record<string, any>>(
    {}
  );
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [activeGeometry, setActiveGeometry] = useState<any>(null);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [basins, setBasins] = useState<any[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [dbSites, setDbSites] = useState<any[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [dbIncidents, setDbIncidents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getBasins()
      .then((data) => {
        setBasins(data);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const geomMap: Record<string, any> = {};
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (basinGeometries[selectedBasin]) {
      setActiveGeometry(basinGeometries[selectedBasin]);
    } else {
      setActiveGeometry(null);
    }
  }, [selectedBasin, basinGeometries]);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getSites({ basin: selectedBasin }),
      getSubmissions({ status: "APPROVED" }),
    ])
      .then(([sitesData, subsData]) => {
        setDbSites(sitesData);
        // Filter submissions to only include "Pollution Reporting Form"
        const filteredSubs = subsData.filter(
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (sub: any) => sub.form_name === "Pollution Reporting Form"
        );
        setDbIncidents(filteredSubs);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error loading database map data:", err);
        setLoading(false);
      });
  }, [selectedBasin]);

  // 1. Filtered sites based on health and search
  const filteredSites = dbSites.filter((site) => {
    // Health category filter
    if (selectedHealthFilter !== "All") {
      const hClass = site.status?.health_class;
      if (selectedHealthFilter === "Critical" && !["D", "E"].includes(hClass))
        return false;
      if (selectedHealthFilter === "At risk" && hClass !== "C") return false;
      if (selectedHealthFilter === "Healthy" && !["A", "B"].includes(hClass))
        return false;
    }

    // Search query filter
    if (searchQuery.trim() !== "") {
      const query = searchQuery.toLowerCase();
      const matchName = site.name.toLowerCase().includes(query);
      const matchId = site.code.toLowerCase().includes(query);
      const matchDescription = site.description?.toLowerCase().includes(query);
      if (!matchName && !matchId && !matchDescription) return false;
    }

    return true;
  });

  // 2. Filtered incidents based on basin and health/severity
  const activeBasin = basins.find((b) => b.code === selectedBasin);
  const activeBasinId = activeBasin?.id;

  const filteredIncidents = dbIncidents.filter((incident) => {
    // Basin filter
    const matchesBasin =
      incident.basin_id === activeBasinId ||
      (incident.site_id && dbSites.some((s) => s.id === incident.site_id));
    if (!matchesBasin) return false;

    // Resolve incident type and map to severity status
    const qIncidentAns = incident.answers.find(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (a: any) => a.name === "incident_type" || a.question_id === 2
    );
    const optionVal = qIncidentAns?.options?.[0];
    let severity = "Moderate";
    if (optionVal === 3 || optionVal === "3") {
      severity = "Critical";
    } else if (
      optionVal === 1 ||
      optionVal === "1" ||
      optionVal === 2 ||
      optionVal === "2"
    ) {
      severity = "Elevated";
    }

    // Also filter incidents by severity matching the selectedHealthFilter
    if (selectedHealthFilter !== "All") {
      if (selectedHealthFilter === "Critical" && severity !== "Critical")
        return false;
      if (selectedHealthFilter === "At risk" && severity !== "Elevated")
        return false;
      if (selectedHealthFilter === "Healthy" && severity !== "Moderate")
        return false;
    }

    return true;
  });

  // 3. Map markers configuration combining sites and incidents
  const mapMarkers = [
    ...filteredSites.map((site) => {
      const coords = site.geom?.coordinates;
      const position: [number, number] = coords
        ? [coords[1], coords[0]]
        : [0, 0];
      const ikAdjustedScore = site.status?.ik_adjusted_score ?? 0.5;
      const progressPercent = Math.round(ikAdjustedScore * 100);
      return {
        position,
        popupText: `${site.name} (${site.status?.health_class || "N/A"})`,
        type: "site" as const,
        status: site.status?.health_class,
        code: site.code,
        name: site.name,
        score: progressPercent,
        description: site.description || "No signal details recorded.",
      };
    }),
    ...filteredIncidents.map((incident) => {
      const coords = incident.geo?.coordinates;
      const position: [number, number] = coords
        ? [coords[1], coords[0]]
        : [0, 0];

      const qIncidentAns = incident.answers.find(
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (a: any) => a.name === "incident_type" || a.question_id === 2
      );
      const optionVal = qIncidentAns?.options?.[0];
      let severity = "Moderate";
      if (optionVal === 3 || optionVal === "3") {
        severity = "Critical";
      } else if (
        optionVal === 1 ||
        optionVal === "1" ||
        optionVal === 2 ||
        optionVal === "2"
      ) {
        severity = "Elevated";
      }

      const qDetailAns = incident.answers.find(
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (a: any) =>
          a.name === "incident_description" ||
          a.name === "details" ||
          a.question_id === 3
      );
      const descText =
        qDetailAns?.value || incident.description || "No details recorded.";
      const incidentTypeName = qIncidentAns?.value || "Pollution Report";
      const formattedDate = incident.submitted_at
        ? new Date(incident.submitted_at).toLocaleDateString()
        : "Unknown date";

      return {
        position,
        popupText: `Incident: ${incidentTypeName} (${severity})`,
        type: "incident" as const,
        status: severity,
        name: incidentTypeName,
        description: descText,
        additionalInfo: `Reported on: ${formattedDate}`,
      };
    }),
  ];

  // Map center logic (center of Mara or Sio depending on selection)
  const mapCenter: [number, number] =
    selectedBasin === "MARA" ? [-1.2345, 34.5678] : [0.22, 34.2];
  const mapZoom = selectedBasin === "MARA" ? 11 : 12;

  const dropdownOptions = basins.map((b) => ({
    value: b.code,
    label: b.name,
  }));

  return (
    <main className="min-h-screen bg-slate-50 flex flex-col font-sans relative overflow-hidden">
      {/* Header Navigation */}
      <SiteHeader showActions={true} />

      {/* Main content body with relative layout */}
      <div className="flex-1 relative overflow-hidden flex flex-col md:flex-row">
        {/* Map GIS Canvas - occupies top half on mobile, full screen on desktop */}
        <div className="relative h-[60vh] md:absolute md:inset-0 md:h-full z-0 w-full shrink-0">
          <MapViewer
            center={mapCenter}
            zoom={mapZoom}
            markers={mapMarkers}
            basinGeometry={activeGeometry}
            className="h-full w-full"
          />
        </div>

        {/* Left Side Panel (Mobile: stacks below map, Desktop: floating sidebar panel) */}
        <section
          className={`relative ${isListCollapsed ? "flex-initial" : "flex-1"} md:absolute md:bottom-auto md:left-auto md:right-auto md:w-96 md:h-full bg-white/95 backdrop-blur-sm border-t md:border-t-0 md:border-r border-slate-200 z-10 flex flex-col shadow-2xl md:shadow-lg rounded-t-2xl md:rounded-t-none`}
        >
          {/* Drag indicator for mobile - clickable toggle */}
          <button
            onClick={() => setIsListCollapsed(!isListCollapsed)}
            className="w-12 h-1.5 bg-slate-300 hover:bg-slate-400 rounded-full mx-auto my-2.5 shrink-0 md:hidden cursor-pointer active:scale-95 transition-all focus:outline-none"
            aria-label="Toggle panel collapse"
          />

          {/* Basin selector */}
          <div className="p-4 border-b border-slate-100 space-y-4 shrink-0">
            {SHOW_BASIN_SELECTOR && (
              <Dropdown
                label="Basin Region"
                options={dropdownOptions}
                value={selectedBasin}
                onChange={(val) => {
                  setSelectedBasin(val);
                  setSelectedSite(null);
                }}
              />
            )}

            {/* Health filter toggles */}
            <div className="flex bg-slate-100 p-1 rounded-lg w-full text-xs font-semibold">
              {["All", "Critical", "At risk", "Healthy"].map((filter) => (
                <button
                  key={filter}
                  onClick={() => setSelectedHealthFilter(filter)}
                  className={`flex-1 py-1.5 rounded-md text-center transition-all ${
                    selectedHealthFilter === filter
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
          <div
            className={`p-4 flex flex-col min-h-0 ${isListCollapsed ? "shrink-0" : "flex-1 overflow-y-auto"}`}
          >
            <div
              className="text-xs font-bold text-slate-400 uppercase tracking-wider flex justify-between items-center cursor-pointer select-none hover:text-slate-600 transition-colors py-1"
              onClick={() => setIsListCollapsed(!isListCollapsed)}
            >
              <div className="flex items-center w-full justify-between gap-2">
                <span className="text-slate-500 font-bold text-xs uppercase tracking-wider">
                  Monitoring Sites ({filteredSites.length})
                  {filteredIncidents.length > 0 && (
                    <span className="text-red-500 normal-case font-medium ml-2">
                      • {filteredIncidents.length} Incident
                      {filteredIncidents.length > 1 ? "s" : ""}
                    </span>
                  )}
                </span>
                <svg
                  className={`w-3.5 h-3.5 transform transition-transform duration-200 ${
                    isListCollapsed ? "" : "rotate-180"
                  }`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth="2.5"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </div>
            </div>

            {!isListCollapsed && (
              <div className="mt-3 space-y-3 overflow-y-auto pr-1 flex-1">
                {loading ? (
                  <div className="py-8 flex justify-center">
                    <Loader message="Loading wetland data..." />
                  </div>
                ) : filteredSites.length > 0 ? (
                  filteredSites.map((site) => {
                    const hClass = site.status?.health_class || "C";
                    const isCritical = ["D", "E"].includes(hClass);
                    const isAtRisk = hClass === "C";
                    const ikAdjustedScore =
                      site.status?.ik_adjusted_score ?? 0.5;
                    const progressPercent = Math.round(ikAdjustedScore * 100);
                    const isIkAdjusted =
                      site.status?.ik_adjusted_score !==
                      site.status?.composite_score;
                    const country =
                      site.country ||
                      (site.code?.includes("SIO") ? "Kenya" : "Tanzania");

                    return (
                      <Card
                        key={site.code}
                        onClick={() => setSelectedSite(site)}
                        className="p-4 hover:shadow-md transition-all border border-slate-100 hover:border-teal-100 cursor-pointer flex flex-col gap-3 relative overflow-hidden group"
                      >
                        <div className="flex justify-between items-start">
                          <div>
                            <h4 className="font-bold text-slate-800 text-sm group-hover:text-teal-600 transition-colors">
                              {site.name}
                            </h4>
                            <span className="text-xs text-slate-400 font-mono">
                              {site.code}
                            </span>
                          </div>
                          <div
                            className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm border ${
                              isCritical
                                ? "bg-red-50 text-red-700 border-red-200"
                                : isAtRisk
                                  ? "bg-amber-50 text-amber-700 border-amber-200"
                                  : "bg-green-50 text-green-700 border-green-200"
                            }`}
                          >
                            {hClass}
                          </div>
                        </div>

                        <div className="space-y-1">
                          <div className="text-xs text-slate-500 font-medium">
                            Community Signal:{" "}
                            {site.description || "No signal details recorded."}
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full ${
                                  isCritical
                                    ? "bg-red-500"
                                    : isAtRisk
                                      ? "bg-amber-500"
                                      : "bg-green-500"
                                }`}
                                style={{ width: `${progressPercent}%` }}
                              />
                            </div>
                            <span className="text-[10px] font-bold text-slate-600">
                              {progressPercent}%
                            </span>
                          </div>
                        </div>

                        <div className="flex flex-wrap gap-1.5 mt-1">
                          <span className="text-[10px] font-bold tracking-wide uppercase px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-100 shadow-sm flex items-center gap-1">
                            Approved
                          </span>
                          <span className="text-[10px] font-bold tracking-wide px-2 py-0.5 rounded-md bg-slate-50 text-slate-600 border border-slate-200/80 shadow-sm flex items-center gap-1 shrink-0">
                            <svg
                              className="w-3 h-3 text-slate-400"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                              strokeWidth="2.5"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
                              />
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
                              />
                            </svg>
                            {country}
                          </span>
                          {isIkAdjusted && (
                            <span className="text-[10px] font-bold tracking-wide px-2 py-0.5 rounded-md bg-teal-50 text-teal-700 border border-teal-100 shadow-sm flex items-center gap-1 shrink-0">
                              IK-adjusted
                            </span>
                          )}
                        </div>

                        {/* Action Warning Banners for sites requiring intervention */}
                        {(isCritical || isAtRisk) && (
                          <div
                            className={`p-2.5 rounded-lg flex items-start gap-2 text-xs border ${
                              isCritical
                                ? "bg-red-50/80 border-red-100 text-red-700"
                                : "bg-amber-50/80 border-amber-100 text-amber-700"
                            }`}
                          >
                            <svg
                              className="w-4 h-4 mt-0.5 shrink-0"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                              strokeWidth="2.5"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                              />
                            </svg>
                            <div className="flex-1 font-semibold leading-relaxed">
                              {site.management_actions &&
                              site.management_actions.length > 0 ? (
                                <span>
                                  Action:{" "}
                                  <span className="font-bold">
                                    {site.management_actions[0].label}
                                  </span>{" "}
                                  — {site.management_actions[0].description}
                                </span>
                              ) : (
                                <span>
                                  {isCritical
                                    ? "Action: Critical degradation detected. Immediate intervention recommended."
                                    : "Action: Water quality declining. Preventive intervention recommended."}
                                </span>
                              )}
                            </div>
                          </div>
                        )}
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
      <SiteDrawer
        site={mapDbSiteToDrawerSite(selectedSite)}
        onClose={() => setSelectedSite(null)}
      />
    </main>
  );
}

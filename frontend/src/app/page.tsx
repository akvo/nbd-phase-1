"use client";

import React, { useState, useEffect, useMemo } from "react";
import dynamic from "next/dynamic";
import { Card } from "@/components/ui/card";
import { SiteDrawer } from "@/components/ui/site-drawer";
import { SiteHeader } from "@/components/ui/site-header";
import { Loader } from "@/components/ui/loader";
import { MapLegend } from "@/components/ui/map-legend";
import { IncidentCard } from "@/components/ui/incident-card";
import { IncidentDrawer } from "@/components/ui/incident-drawer";
import { MapFilter } from "@/components/ui/map-filter";
import { useTranslations, useLocale } from "next-intl";
import { useDomain } from "@/context/domain-context";
import { useStaticData } from "@/context/static-data-context";
import booleanPointInPolygon from "@turf/boolean-point-in-polygon";
import { point } from "@turf/helpers";
import { PollutionDetailsDrawer } from "@/components/ui/pollution-details-drawer";
import {
  AlertTriangle,
  Droplet,
  Fish,
  Wind,
  CloudLightning,
  Waves,
} from "lucide-react";

import { getSubmissions, IncidentSummary } from "@/lib/api";

const MapViewer = dynamic(() => import("@/components/ui/map-viewer"), {
  ssr: false,
});

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mapDbSiteToDrawerSite = (site: any, noSignalText: string): any => {
  if (!site) return null;
  const coords = site.geom?.coordinates;
  const hasStatus =
    !!site.status &&
    (site.status.health_class != null ||
      site.status.composite_score != null ||
      site.status.ik_adjusted_score != null);
  const healthClass = site.status?.health_class || null;
  const compositeScore = site.status?.composite_score ?? null;
  const ikAdjustedScore = site.status?.ik_adjusted_score ?? compositeScore;

  // Re-map management actions list
  const management_actions = (site.management_actions || []).map(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (action: any) => ({
      label: action.label,
      description: action.description,
    })
  );

  // Prefer backend site.country if present, otherwise fallback to code lookup (e.g. SIO-002/003 for Uganda)
  const country =
    site.country ||
    (site.code?.includes("SIO-002") || site.code?.includes("SIO-003")
      ? "Uganda"
      : site.code?.includes("SIO")
        ? "Kenya"
        : "Tanzania");

  // Parse dynamic score breakdown from status if available
  const score_breakdown =
    site.status?.score_breakdown ||
    (compositeScore !== null
      ? {
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
        }
      : null);

  return {
    site_id: site.code,
    site_name: site.name,
    country,
    basin: site.code?.includes("SIO") ? "SIO_SITEKO" : "MARA",
    current_health_class: healthClass,
    current_score: ikAdjustedScore,
    last_updated: site.status?.sampling_date || null,
    coordinates: coords ? [coords[1], coords[0]] : [0, 0],
    community_signal: site.description || noSignalText,
    progress_percent:
      ikAdjustedScore !== null ? Math.round(ikAdjustedScore * 100) : null,
    is_approved: true,
    is_ik_adjusted:
      hasStatus &&
      site.status?.ik_adjusted_score !== site.status?.composite_score,
    details: {
      score_breakdown,
      physico_chemical: {
        group_score: score_breakdown?.physico_chemical?.score ?? compositeScore,
        ph: site.status?.metrics?.ph?.value ?? null,
        dissolved_oxygen: site.status?.metrics?.dissolved_oxygen?.value ?? null,
        temperature: site.status?.metrics?.temperature?.value ?? null,
        weights: { ph: 0.3704, dissolved_oxygen: 0.6297 },
      },
      catchment_hydrological: {
        group_score:
          score_breakdown?.catchment_hydrological?.score ?? compositeScore,
      },
      ecological: {
        group_score: score_breakdown?.ecological?.score ?? compositeScore,
      },
      ik_signal: {
        encoded_signal_value:
          site.status?.ik_signal?.encoded_signal_value ??
          site.status?.ik_adjusted_score ??
          null,
        fish_abundance: site.status?.ik_signal?.fish_abundance ?? null,
        water_clarity: site.status?.ik_signal?.water_clarity ?? null,
        vegetation_cover: site.status?.ik_signal?.vegetation_cover ?? null,
        pollution_events: site.status?.ik_signal?.pollution_events ?? null,
      },
      management_actions,
      water_level: site.status?.metrics?.water_level?.value || null,
      metrics: {
        ph: site.status?.metrics?.ph || {
          value: null,
          unit: "-",
          status: null,
          label: "pH",
          icon: "FlaskConical",
        },
        dissolved_oxygen: site.status?.metrics?.dissolved_oxygen || {
          value: null,
          unit: "mg/L",
          status: null,
          label: "Dissolved O₂",
          icon: "Droplets",
        },
        temperature: site.status?.metrics?.temperature || {
          value: null,
          unit: "°C",
          status: null,
          label: "Temperature",
          icon: "Thermometer",
        },
        water_level: site.status?.metrics?.water_level || {
          value: null,
          unit: "-",
          status: null,
          label: "Water level",
          icon: "Waves",
        },
        turbidity: site.status?.metrics?.turbidity || {
          value: null,
          unit: "NTU",
          status: null,
          label: "Turbidity",
          icon: "EyeOff",
        },
        macroinvertebrate: site.status?.metrics?.macroinvertebrate || {
          value: null,
          unit: "index",
          status: null,
          label: "Macroinvertebrate",
          icon: "Bug",
        },
      },
    },
  };
};

const getIncidentIcon = (typeName: string) => {
  const lower = typeName.toLowerCase();
  if (
    lower.includes("colour") ||
    lower.includes("color") ||
    lower.includes("chafu") ||
    lower.includes("nyeusi")
  ) {
    return <Droplet className="w-4 h-4 text-sky-500" />;
  }
  if (
    lower.includes("smell") ||
    lower.includes("harufu") ||
    lower.includes("odour")
  ) {
    return <Wind className="w-4 h-4 text-emerald-500" />;
  }
  if (
    lower.includes("fish") ||
    lower.includes("samaki") ||
    lower.includes("kill") ||
    lower.includes("vifo")
  ) {
    return <Fish className="w-4 h-4 text-rose-500" />;
  }
  if (lower.includes("storm") || lower.includes("dhoruba")) {
    return <CloudLightning className="w-4 h-4 text-amber-500" />;
  }
  if (lower.includes("high water") || lower.includes("juu ya maji")) {
    return <Waves className="w-4 h-4 text-blue-500" />;
  }
  if (lower.includes("low water") || lower.includes("chini ya maji")) {
    return <Waves className="w-4 h-4 text-teal-500 rotate-180" />;
  }
  return <AlertTriangle className="w-4 h-4 text-slate-500" />;
};

export default function Home() {
  const t = useTranslations("landing");

  const [selectedBasin, setSelectedBasin] = useState("MARA");
  const [selectedHealthFilter, setSelectedHealthFilter] = useState("All");
  const [selectedWetland, setSelectedWetland] = useState("");
  const [selectedIncidentTypes, setSelectedIncidentTypes] = useState<string[]>(
    []
  );
  const [selectedDateFrom, setSelectedDateFrom] = useState("");
  const [selectedDateTo, setSelectedDateTo] = useState("");
  const {
    selectedDomain,
    selectedSite,
    setSelectedSite,
    selectedIncident,
    setSelectedIncident,
    selectedSubCounty,
    setSelectedSubCounty,
    closeAllDrawers,
    pollutionRange,
    setPollutionRange,
  } = useDomain();
  const { basins, sites, getFormsList, getFormDetails } = useStaticData();

  const [isListCollapsed, setIsListCollapsed] = useState(false);
  const locale = useLocale();
  const [incidentTypeOptions, setIncidentTypeOptions] = useState<
    Array<{ value: string; label: string }>
  >([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [basinGeometries, setBasinGeometries] = useState<Record<string, any>>(
    {}
  );
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [activeGeometry, setActiveGeometry] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [wetlandGeometry, setWetlandGeometry] = useState<any>(null);

  // Spatial Location Cascade state
  const [counties, setCounties] = useState<
    Array<{ value: string; label: string }>
  >([]);
  const [subCounties, setSubCounties] = useState<
    Array<{ value: string; label: string }>
  >([]);
  const [wards, setWards] = useState<Array<{ value: string; label: string }>>(
    []
  );
  const [selectedCounty, setSelectedCounty] = useState<string>("");
  const [selectedSubCountyId, setSelectedSubCountyId] = useState<string>("");
  const [selectedWardId, setSelectedWardId] = useState<string>("");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [wardGeometry, setWardGeometry] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [selectedWardFeature, setSelectedWardFeature] = useState<any>(null);

  const dbSites = useMemo(() => {
    return sites.filter((site) => {
      const siteBasin = site.code?.includes("SIO") ? "SIO_SITEKO" : "MARA";
      return siteBasin === selectedBasin;
    });
  }, [sites, selectedBasin]);

  const [dbIncidents, setDbIncidents] = useState<IncidentSummary[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch wetland GeoJSON when in wetland domain
  useEffect(() => {
    if (selectedDomain === "wetland") {
      const isSio = selectedBasin?.toUpperCase().includes("SIO");
      const fileName = isSio
        ? "sio-siteko-wetland.geojson"
        : "mara-wetland.geojson";
      fetch(`/spatial/${fileName}?v=1.0.1`)
        .then((res) => {
          if (!res.ok) throw new Error("Failed to load wetland GeoJSON");
          return res.json();
        })
        .then((data) => setWetlandGeometry(data))
        .catch((err) => {
          console.error("Error loading wetland geometry:", err);
          setWetlandGeometry(null);
        });
    } else {
      setWetlandGeometry(null);
    }
  }, [selectedDomain, selectedBasin]);

  // Fetch Ward GeoJSON for vector map overlay and unified choropleth
  useEffect(() => {
    const isSio = selectedBasin?.toUpperCase().includes("SIO");
    const fileName = isSio ? "sio-wards.geojson" : "mara-wards.geojson";
    fetch(`/spatial/${fileName}?v=1.2.0`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && data.features) {
          // Normalize features so choropleth logic and components can use .name
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const normalizedFeatures = data.features.map((f: any) => ({
            ...f,
            properties: {
              ...f.properties,
              name: f.properties["Ward"] || f.properties.name || "",
              subCountyName:
                f.properties["Sub-County"] || f.properties.subCountyName || "",
              countyName:
                f.properties["County"] || f.properties.countyName || "",
            },
          }));
          setWardGeometry({ ...data, features: normalizedFeatures });
        } else {
          setWardGeometry(data);
        }
      })
      .catch((err) => {
        console.error("Error loading ward GeoJSON:", err);
        setWardGeometry(null);
      });
  }, [selectedBasin]);

  // Fetch Level 2 Counties reference data
  useEffect(() => {
    const backendUrl =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    fetch(`${backendUrl}/api/v1/reference/sub-counties/0`)
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => {
        if (Array.isArray(data)) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const countyOpts = data.map((c: any) => ({
            value: c.id,
            label: c.name,
          }));
          setCounties([
            { value: "", label: t("filters.allCounties") },
            ...countyOpts,
          ]);
        }
      })
      .catch((err) => console.error("Error fetching counties:", err));
  }, [t]);

  const handleCountyChange = (countyId: string) => {
    setSelectedCounty(countyId);
    setSelectedSubCountyId("");
    setSelectedWardId("");
    setSubCounties([]);
    setWards([]);
    setSelectedWardFeature(null);

    if (countyId) {
      const backendUrl =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      fetch(`${backendUrl}/api/v1/reference/sub-counties/${countyId}`)
        .then((res) => (res.ok ? res.json() : []))
        .then((data) => {
          if (Array.isArray(data)) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const scOpts = data.map((sc: any) => ({
              value: sc.id,
              label: sc.name,
            }));
            setSubCounties([
              { value: "", label: t("filters.allSubCounties") },
              ...scOpts,
            ]);
          }
        })
        .catch((err) => console.error("Error fetching sub-counties:", err));
    }
  };

  const handleSubCountyChange = (scId: string) => {
    setSelectedSubCountyId(scId);
    setSelectedWardId("");
    setWards([]);
    setSelectedWardFeature(null);

    if (scId) {
      const backendUrl =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      fetch(`${backendUrl}/api/v1/reference/wards/${scId}`)
        .then((res) => (res.ok ? res.json() : []))
        .then((data) => {
          if (Array.isArray(data)) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const wardOpts = data.map((w: any) => ({
              value: w.id,
              label: w.name,
            }));
            setWards([
              { value: "", label: t("filters.allWards") },
              ...wardOpts,
            ]);
          }
        })
        .catch((err) => console.error("Error fetching wards:", err));
    }
  };

  const handleWardChange = (wardId: string) => {
    setSelectedWardId(wardId);
    if (!wardId) {
      setSelectedWardFeature(null);
      return;
    }
    const wardObj = wards.find((w) => w.value === wardId);
    if (wardObj && wardGeometry?.features) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const feature = wardGeometry.features.find((f: any) => {
        const wName = f.properties?.Ward || f.properties?.name;
        return (
          wName?.toString().trim().toLowerCase() ===
          wardObj.label.toString().trim().toLowerCase()
        );
      });
      setSelectedWardFeature(feature || null);
    }
  };

  // Fetch dynamic incident type options from questionnaire
  useEffect(() => {
    getFormsList(locale)
      .then((formsList) => {
        // Find latest version of Citizen Reporter form (type === 1)
        const type1Forms = formsList.filter((f) => f.type === 1);
        const pForm = type1Forms.sort(
          (a, b) => (b.version || 0) - (a.version || 0)
        )[0];
        if (pForm) {
          return getFormDetails(pForm.id, locale);
        }
        return null;
      })
      .then((fullForm) => {
        if (fullForm) {
          let foundOptions: Array<{ value: string; label: string }> = [];
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          fullForm.question_groups?.forEach((group: any) => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            group.questions?.forEach((q: any) => {
              if (q.name === "incident_type" && q.options) {
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                foundOptions = q.options.map((opt: any) => ({
                  value: String(opt.value),
                  label: opt.label || opt.name,
                }));
              }
            });
          });
          if (foundOptions.length > 0) {
            setIncidentTypeOptions(foundOptions);
            return;
          }
        }
        // Fallback static options
        setIncidentTypeOptions([
          { value: "1", label: t("filters.optionWaterColour") },
          { value: "2", label: t("filters.optionSmell") },
          { value: "3", label: t("filters.optionFishKills") },
          { value: "4", label: t("filters.optionStormEvent") },
          { value: "5", label: t("filters.optionHighWater") },
          { value: "6", label: t("filters.optionLowWater") },
          { value: "7", label: t("filters.optionNoWater") },
        ]);
      })
      .catch((err) => {
        console.error("Error fetching questionnaire options:", err);
        setIncidentTypeOptions([
          { value: "1", label: t("filters.optionWaterColour") },
          { value: "2", label: t("filters.optionSmell") },
          { value: "3", label: t("filters.optionFishKills") },
          { value: "4", label: t("filters.optionStormEvent") },
          { value: "5", label: t("filters.optionHighWater") },
          { value: "6", label: t("filters.optionLowWater") },
          { value: "7", label: t("filters.optionNoWater") },
        ]);
      });
  }, [locale, t, getFormsList, getFormDetails]);

  // Synchronize filter resets whenever selectedDomain changes
  useEffect(() => {
    setSelectedHealthFilter("All");
    setSelectedIncident(null);
    setSelectedWetland("");
    setSelectedIncidentTypes([]);
    setSelectedDateFrom("");
    setSelectedDateTo("");
    setSelectedSubCounty(null);
    if (selectedDomain === "pollution") {
      setSelectedSite(null);
    }
  }, [
    selectedDomain,
    setSelectedHealthFilter,
    setSelectedIncident,
    setSelectedSubCounty,
    setSelectedSite,
  ]);

  // Automatically close any open drawers when any filter changes
  useEffect(() => {
    closeAllDrawers();
  }, [
    selectedDomain,
    selectedBasin,
    selectedHealthFilter,
    selectedWetland,
    selectedIncidentTypes,
    selectedDateFrom,
    selectedDateTo,
    closeAllDrawers,
  ]);

  useEffect(() => {
    if (basins.length > 0) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const geomMap: Record<string, any> = {};
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      basins.forEach((b: any) => {
        if (b.code && b.geom) {
          geomMap[b.code] = b.geom;
        }
      });
      setBasinGeometries(geomMap);
      if (geomMap[selectedBasin]) {
        setActiveGeometry(geomMap[selectedBasin]);
      }
    }
  }, [basins, selectedBasin]);

  useEffect(() => {
    if (basinGeometries[selectedBasin]) {
      setActiveGeometry(basinGeometries[selectedBasin]);
    } else {
      setActiveGeometry(null);
    }
  }, [selectedBasin, basinGeometries]);

  useEffect(() => {
    setLoading(true);
    getSubmissions({ status: "APPROVED", domain: selectedDomain, brief: true })
      .then((subsData) => {
        setDbIncidents(subsData as unknown as IncidentSummary[]);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error loading database map data:", err);
        setLoading(false);
      });
  }, [selectedDomain]);

  // 1. Filtered sites based on health and wetland selector
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

    // Wetland site selection filter
    if (selectedWetland !== "" && site.code !== selectedWetland) {
      return false;
    }

    return true;
  });

  // 2. Filtered incidents based on basin, severity, incident type, and date range
  const activeBasin = basins.find((b) => b.code === selectedBasin);
  const activeBasinId = activeBasin?.id;

  const filteredIncidents = dbIncidents.filter((incident) => {
    // Basin filter
    const matchesBasin =
      incident.basin_id === activeBasinId ||
      (incident.site_id && dbSites.some((s) => s.id === incident.site_id));
    if (!matchesBasin) return false;

    // Resolve incident type and map to severity status
    const qIncidentAns = incident.answers?.find(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (a: any) => a.question_name === "incident_type"
    );
    const optionVal = qIncidentAns?.options?.[0] || incident.incident_type_id;

    // Filter by incident type
    if (selectedIncidentTypes.length > 0) {
      if (!selectedIncidentTypes.includes(String(optionVal))) return false;
    }

    // Filter by Date From
    if (selectedDateFrom !== "") {
      if (new Date(incident.created_at || "") < new Date(selectedDateFrom))
        return false;
    }

    // Filter by Date To
    if (selectedDateTo !== "") {
      const endOfDay = new Date(selectedDateTo);
      endOfDay.setHours(23, 59, 59, 999);
      if (new Date(incident.created_at || "") > endOfDay) return false;
    }

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
      if (selectedHealthFilter === "Elevated" && severity !== "Elevated")
        return false;
      if (selectedHealthFilter === "At risk" && severity !== "Elevated")
        return false;
      if (selectedHealthFilter === "Healthy" && severity !== "Moderate")
        return false;
    }

    return true;
  });

  // 3. Map markers configuration combining sites and incidents based on selectedDomain
  const mapMarkers = useMemo(() => {
    if (selectedDomain === "wetland") {
      return filteredSites.map((site) => {
        const coords = site.geom?.coordinates;
        const position: [number, number] = coords
          ? [coords[1], coords[0]]
          : [0, 0];
        const ikAdjustedScore =
          site.status?.ik_adjusted_score ??
          site.status?.composite_score ??
          null;
        const progressPercent =
          ikAdjustedScore !== null ? Math.round(ikAdjustedScore * 100) : null;
        const healthClass = site.status?.health_class;
        return {
          position,
          popupText: `${site.name} (${healthClass || t("noData")})`,
          type: "site" as const,
          status: healthClass || "UNSCORED",
          code: site.code,
          name: site.name,
          score: progressPercent,
          description: site.description || t("noSignal"),
        };
      });
    }

    // Pollution Reports domain - point markers are hidden in favor of choropleth shapes
    return [];
  }, [selectedDomain, filteredSites, t]);

  // 1. Calculate all ward features with incident counts
  const allWardLayers = useMemo(() => {
    if (selectedDomain !== "pollution" || !wardGeometry || loading) return [];

    const features = JSON.parse(JSON.stringify(wardGeometry.features || []));

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return features.map((feature: any) => {
      let count = 0;
      const breakdown: Record<string, number> = {};

      const wardName = feature.properties?.name
        ?.toString()
        .toLowerCase()
        .trim();
      const subCountyName = feature.properties?.subCountyName
        ?.toString()
        .toLowerCase()
        .trim();
      const countyName = feature.properties?.countyName
        ?.toString()
        .toLowerCase()
        .trim();

      filteredIncidents.forEach((incident) => {
        const reportedLoc = incident.reported_location
          ?.toString()
          .toLowerCase()
          .trim();

        // Tier 1: Exact Ward match (new incidents)
        let isInside = !!(reportedLoc && wardName && reportedLoc === wardName);

        // Tier 2: Sub-County match (legacy incidents — uniform distribution across sub-county wards)
        if (
          !isInside &&
          reportedLoc &&
          subCountyName &&
          reportedLoc === subCountyName
        ) {
          isInside = true;
        }

        // Tier 2.5: County match (legacy/county-level incidents — uniform distribution across county wards)
        if (
          !isInside &&
          reportedLoc &&
          countyName &&
          reportedLoc === countyName
        ) {
          isInside = true;
        }

        // Tier 3: location_id answer name match
        if (!isInside) {
          const locationAns = incident.answers?.find(
            (a: any) =>
              a.question_name === "location_id" &&
              a.value?.toString().toLowerCase().trim() === wardName
          );
          if (locationAns) isInside = true;
        }

        // Tier 4: Point-in-polygon (GPS-tagged)
        if (!isInside) {
          const coords = incident.geo?.coordinates;
          if (coords && coords.length >= 2) {
            try {
              isInside = booleanPointInPolygon(point(coords), feature);
            } catch {
              // silent
            }
          }
        }

        if (isInside) {
          count++;
          const qIncidentAns = incident.answers?.find(
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (a: any) => a.question_name === "incident_type"
          );
          const typeLabel =
            qIncidentAns?.value || incident.incident_type_name || "Unknown";
          breakdown[typeLabel] = (breakdown[typeLabel] || 0) + 1;
        }
      });

      feature.properties = {
        ...feature.properties,
        incidentCount: count,
        incidentBreakdown: breakdown,
      };

      return feature;
    });
  }, [selectedDomain, wardGeometry, filteredIncidents, loading]);

  // Compute maximum incident count among all wards for dynamic slider scale
  const maxIncidentCount = useMemo(() => {
    if (!allWardLayers || allWardLayers.length === 0) return 20;
    let max = 0;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    allWardLayers.forEach((feature: any) => {
      const cnt = feature.properties?.incidentCount || 0;
      if (cnt > max) max = cnt;
    });
    return Math.max(20, Math.ceil(max / 10) * 10);
  }, [allWardLayers]);

  // Compute filtered choroplethLayers based on active pollutionRange
  const choroplethLayers = useMemo(() => {
    if (!allWardLayers) return [];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return allWardLayers.filter((feature: any) => {
      const count = feature.properties?.incidentCount || 0;
      const isMaxSelected = pollutionRange[1] >= maxIncidentCount;
      const maxRange = isMaxSelected ? Infinity : pollutionRange[1];
      return count >= pollutionRange[0] && count <= maxRange;
    });
  }, [allWardLayers, pollutionRange, maxIncidentCount]);

  // Compute sidebar/list incidents filtered by selected ward/sub-county
  const sidebarIncidents = useMemo(() => {
    if (selectedDomain !== "pollution") return [];

    // If no ward polygon is selected, return all basin-wide incidents matching filters
    if (!selectedSubCounty) {
      return [...filteredIncidents].sort((a, b) => {
        const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
        const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
        return dateA - dateB;
      });
    }

    const selWardName = selectedSubCounty.properties?.name
      ?.toString()
      .trim()
      .toLowerCase();
    const selSubCountyName = selectedSubCounty.properties?.subCountyName
      ?.toString()
      .trim()
      .toLowerCase();
    const selCountyName = selectedSubCounty.properties?.countyName
      ?.toString()
      .trim()
      .toLowerCase();

    const matched = filteredIncidents.filter((incident) => {
      const reportedLoc = incident.reported_location
        ?.toString()
        .trim()
        .toLowerCase();

      // 1. Direct match on Ward name, Sub-County legacy name, or County name
      if (
        reportedLoc &&
        ((selWardName && reportedLoc === selWardName) ||
          (selSubCountyName && reportedLoc === selSubCountyName) ||
          (selCountyName && reportedLoc === selCountyName))
      ) {
        return true;
      }

      // 2. Fallback to location_id answer
      const locationAns = incident.answers?.find(
        (a: any) =>
          a.question_name === "location_id" &&
          a.value &&
          a.value.toString().trim().toLowerCase() === selWardName
      );
      if (locationAns) return true;

      // 3. Fallback to point-in-polygon check
      const coords = incident.geo?.coordinates;
      if (!coords || coords.length < 2) return false;
      try {
        const pt = point(coords);
        return booleanPointInPolygon(pt, selectedSubCounty);
      } catch (err) {
        console.error("Point-in-polygon check for sidebar failed:", err);
        return false;
      }
    });

    // Sort by created_at ASC
    return [...matched].sort((a, b) => {
      const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
      const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
      return dateA - dateB;
    });
  }, [selectedDomain, selectedSubCounty, filteredIncidents]);

  // Map center logic (accurate centroid of Mara or Sio)
  const isMara = selectedBasin?.toUpperCase().includes("MARA");
  const mapCenter: [number, number] = isMara ? [-1.15, 35.3] : [0.37, 34.25];
  const mapZoom = isMara ? 10 : 11;

  const dropdownOptions = basins.map((b) => ({
    value: b.code,
    label: b.name,
  }));

  return (
    <main className="min-h-screen bg-slate-50 flex flex-col font-sans relative md:overflow-hidden">
      {/* Header Navigation */}
      <SiteHeader showActions={true} />

      {/* Map Filter Bar */}
      <MapFilter
        domain={selectedDomain}
        basins={dropdownOptions}
        selectedBasin={selectedBasin}
        onBasinChange={(val) => {
          setSelectedBasin(val);
          setWardGeometry(null);
          setWetlandGeometry(null);
          setSelectedSite(null);
          setSelectedIncident(null);
          setSelectedWetland("");
          setSelectedSubCounty(null);
          setSelectedCounty("");
          setSelectedSubCountyId("");
          setSelectedWardId("");
          setSubCounties([]);
          setWards([]);
          setSelectedWardFeature(null);
        }}
        counties={counties}
        selectedCounty={selectedCounty}
        onCountyChange={handleCountyChange}
        subCounties={subCounties}
        selectedSubCounty={selectedSubCountyId}
        onSubCountyChange={handleSubCountyChange}
        wards={wards}
        selectedWard={selectedWardId}
        onWardChange={handleWardChange}
        selectedHealthFilter={selectedHealthFilter}
        onHealthFilterChange={setSelectedHealthFilter}
        selectedIncidentTypes={selectedIncidentTypes}
        onIncidentTypesChange={setSelectedIncidentTypes}
        selectedDateFrom={selectedDateFrom}
        onDateFromChange={setSelectedDateFrom}
        selectedDateTo={selectedDateTo}
        onDateToChange={setSelectedDateTo}
        incidentTypeOptions={incidentTypeOptions}
        onClearFilters={() => {
          setSelectedHealthFilter("All");
          setSelectedWetland("");
          setSelectedIncidentTypes([]);
          setSelectedDateFrom("");
          setSelectedDateTo("");
          setPollutionRange([0, Infinity]);
          setSelectedCounty("");
          setSelectedSubCountyId("");
          setSelectedWardId("");
          setSubCounties([]);
          setWards([]);
          setSelectedWardFeature(null);
          closeAllDrawers();
        }}
      />

      {/* Main content body with relative layout */}
      <div className="flex-1 relative overflow-hidden flex flex-col md:flex-row">
        {/* Map GIS Canvas - occupies top half on mobile, full screen on desktop */}
        <div className="relative h-[60vh] md:absolute md:inset-0 md:h-full z-0 w-full shrink-0">
          <MapViewer
            center={mapCenter}
            zoom={mapZoom}
            markers={mapMarkers}
            basinGeometry={activeGeometry}
            wetlandGeometry={wetlandGeometry}
            wardGeometry={wardGeometry}
            selectedWard={selectedWardFeature}
            onSelectWard={(feature) => setSelectedWardFeature(feature)}
            choroplethLayers={choroplethLayers}
            selectedSubCounty={selectedSubCounty}
            onSelectSubCounty={(subCounty) => {
              setSelectedSubCounty(subCounty);
              if (subCounty) {
                setSelectedSite(null);
                setSelectedIncident(null);
              }
            }}
            className="h-full w-full"
            onSelectMarker={(code, type) => {
              if (type === "site") {
                const s = dbSites.find((x) => x.code === code);
                if (s) setSelectedSite(s);
              } else {
                const inc = dbIncidents.find((x) => x.id === code);
                if (inc) setSelectedIncident(inc);
              }
            }}
          />
        </div>

        {/* Left Side Panel (Mobile: stacks below map, Desktop: floating sidebar panel) */}
        <section
          className={`relative ${isListCollapsed ? "flex-initial" : "flex-1"} md:absolute md:bottom-auto md:left-auto md:right-auto md:w-96 md:h-full bg-white/95 backdrop-blur-sm border-t md:border-t-0 md:border-r border-slate-200 z-10 flex flex-col shadow-2xl md:shadow-lg rounded-t-2xl md:rounded-t-none`}
        >
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
                  {selectedDomain === "wetland"
                    ? `${t("monitoringSites")} (${filteredSites.length})`
                    : selectedSubCounty
                      ? `Pollution Incidents: ${selectedSubCounty.properties.name}${selectedSubCounty.properties.subCountyName ? ` (${selectedSubCounty.properties.subCountyName})` : ""} (${sidebarIncidents.length})`
                      : `Pollution Incidents (${sidebarIncidents.length})`}
                  {selectedDomain === "wetland" &&
                    filteredIncidents.length > 0 && (
                      <span className="text-red-500 normal-case font-medium ml-2">
                        • {filteredIncidents.length}{" "}
                        {filteredIncidents.length > 1
                          ? t("incidentsPlural")
                          : t("incidents")}
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
                    <Loader
                      message={
                        selectedDomain === "wetland"
                          ? t("loadingWetland")
                          : "Loading data..."
                      }
                    />
                  </div>
                ) : selectedDomain === "wetland" ? (
                  filteredSites.length > 0 ? (
                    filteredSites.map((site) => {
                      const hasScore =
                        site.status?.ik_adjusted_score != null ||
                        site.status?.composite_score != null;
                      const hClass = site.status?.health_class || null;
                      const isCritical = hClass
                        ? ["D", "E"].includes(hClass)
                        : false;
                      const isAtRisk = hClass === "C";
                      const ikAdjustedScore =
                        site.status?.ik_adjusted_score ??
                        site.status?.composite_score ??
                        null;
                      const progressPercent =
                        ikAdjustedScore !== null
                          ? Math.round(ikAdjustedScore * 100)
                          : null;
                      const country =
                        site.country ||
                        (site.code?.includes("SIO-002") ||
                        site.code?.includes("SIO-003")
                          ? "Uganda"
                          : site.code?.includes("SIO")
                            ? "Kenya"
                            : "Tanzania");

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
                              className={`w-3 h-3 rounded-full border mt-1 shrink-0 ${
                                !hasScore
                                  ? "bg-slate-300 border-slate-400"
                                  : isCritical
                                    ? "bg-red-500 border-red-600"
                                    : isAtRisk
                                      ? "bg-amber-500 border-amber-600"
                                      : "bg-green-500 border-green-600"
                              }`}
                            />
                          </div>

                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                {hasScore && progressPercent !== null ? (
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
                                ) : null}
                              </div>
                              <span className="text-[10px] font-bold text-slate-500">
                                {hasScore && progressPercent !== null
                                  ? `${progressPercent}%`
                                  : t("noData")}
                              </span>
                            </div>
                          </div>

                          <div className="flex flex-wrap gap-1.5 mt-1">
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
                          </div>

                          {/* Action Warning Banners for sites requiring intervention or unscored info */}
                          {!hasScore ? (
                            <div className="p-2 rounded-lg flex items-center gap-1.5 text-xs bg-slate-50 border border-slate-100 text-slate-500">
                              <span className="leading-snug text-[11px]">
                                {t("noSamplingDataRecorded")}
                              </span>
                            </div>
                          ) : isCritical || isAtRisk ? (
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
                          ) : null}
                        </Card>
                      );
                    })
                  ) : (
                    <div className="text-sm text-slate-400 italic py-8 text-center">
                      No active stations matching filters.
                    </div>
                  )
                ) : sidebarIncidents.length > 0 ? (
                  sidebarIncidents.map((incident, idx) => {
                    const incidentTypeName =
                      incident.incident_type_name ||
                      incident.name ||
                      "Pollution Report";
                    const imageUrl = incident.image_url;
                    let subCountyName = incident.reported_location;

                    if (!subCountyName) {
                      const wardFeature = wardGeometry?.features?.find(
                        (wFeature: any) => {
                          const coords = incident.geo?.coordinates;
                          if (!coords || coords.length < 2) return false;
                          try {
                            return booleanPointInPolygon(
                              point(coords),
                              wFeature
                            );
                          } catch {
                            return false;
                          }
                        }
                      );
                      subCountyName = wardFeature?.properties?.name
                        ? `${wardFeature.properties.name}${wardFeature.properties.subCountyName ? ` (${wardFeature.properties.subCountyName})` : ""}`
                        : undefined;
                    }

                    return (
                      <IncidentCard
                        key={incident.id ?? idx}
                        incidentTypeName={incidentTypeName}
                        dateReported={incident.created_at || ""}
                        description={incident.description}
                        subCountyName={subCountyName}
                        disableClick={true}
                        imageUrl={imageUrl}
                        icon={getIncidentIcon(incidentTypeName)}
                      />
                    );
                  })
                ) : (
                  <div className="text-sm text-slate-400 italic py-8 text-center">
                    {selectedSubCounty
                      ? "No pollution incidents reported in this ward."
                      : t("noIncidents")}
                  </div>
                )}
              </div>
            )}
          </div>
        </section>
      </div>

      {/* Floating Side Info Overlay of Legend */}
      <MapLegend domain={selectedDomain} maxCount={maxIncidentCount} />

      {/* Site granular details Drawer panel */}
      <SiteDrawer
        site={mapDbSiteToDrawerSite(selectedSite, t("noSignal"))}
        onClose={() => setSelectedSite(null)}
      />

      {/* Incident details Drawer panel */}
      <IncidentDrawer
        incident={selectedIncident}
        basinName={activeBasin?.name}
        onClose={() => setSelectedIncident(null)}
      />

      {/* Pollution ward details Drawer panel */}
      <PollutionDetailsDrawer
        selectedSubCounty={selectedSubCounty}
        incidents={sidebarIncidents}
        onClickIncident={(incident: any) => {
          setSelectedIncident(incident);
          setSelectedSubCounty(null);
        }}
        onClose={() => setSelectedSubCounty(null)}
      />
    </main>
  );
}

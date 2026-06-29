import React, { useEffect, useState, useMemo } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  ZoomControl,
  GeoJSON,
  useMap,
} from "react-leaflet";
import * as L from "leaflet";
import { Loader } from "@/components/ui/loader";

interface MapMarker {
  position: [number, number];
  popupText?: string;
  type: "site" | "incident";
  status?: string;
  code?: string;
  name?: string;
  score?: number;
  description?: string;
  additionalInfo?: string;
}

interface MapViewerProps {
  center: [number, number];
  zoom: number;
  markers?: MapMarker[];
  className?: string;
  zoomOffsetClass?: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  basinGeometry?: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  wetlandGeometry?: any;
  onSelectMarker?: (code: string, type: "site" | "incident") => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  choroplethLayers?: any[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  selectedSubCounty?: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onSelectSubCounty?: (feature: any) => void;
}

function MapController({
  basinGeometry,
  wetlandGeometry,
  choroplethLayers,
}: {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  basinGeometry: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  wetlandGeometry: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  choroplethLayers: any;
}) {
  const map = useMap();

  useEffect(() => {
    const targetGeom =
      wetlandGeometry ||
      (choroplethLayers && choroplethLayers.length > 0
        ? { type: "FeatureCollection", features: choroplethLayers }
        : null) ||
      basinGeometry;
    if (targetGeom) {
      try {
        const layer = L.geoJSON(targetGeom);
        map.fitBounds(layer.getBounds(), { padding: [30, 30] });
      } catch (err) {
        console.error("Failed to fit bounds to geometry:", err);
      }
    }
  }, [basinGeometry, wetlandGeometry, choroplethLayers, map]);

  return null;
}

const getChoroplethColor = (count: number) => {
  if (count >= 16) return "#dc2626"; // red-600
  if (count >= 6) return "#f97316"; // orange-500
  if (count >= 1) return "#fef3c7"; // amber-100
  return "#f1f5f9"; // slate-100
};

export default function MapViewer({
  center,
  zoom,
  markers = [],
  className,
  zoomOffsetClass,
  basinGeometry,
  wetlandGeometry,
  onSelectMarker,
  choroplethLayers = [],
  selectedSubCounty,
  onSelectSubCounty,
}: MapViewerProps) {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const icons = useMemo(() => {
    if (!isMounted || typeof window === "undefined" || !L) return null;

    const createIcon = (
      type: "site" | "incident" | "siteDefault",
      status?: string
    ) => {
      let pingBg: string;
      let centerBg: string;

      if (type === "siteDefault") {
        return L.divIcon({
          html: `<div class="relative flex items-center justify-center w-6 h-6">
              <span class="absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-60 animate-ping"></span>
              <div class="relative rounded-full h-4.5 w-4.5 bg-teal-600 border border-white shadow"></div>
            </div>`,
          className: "custom-leaflet-icon",
          iconSize: [24, 24],
          iconAnchor: [12, 12],
        });
      }

      if (type === "site") {
        if (status === "A" || status === "B") {
          pingBg = "bg-green-400";
          centerBg = "bg-green-600";
        } else if (status === "C") {
          pingBg = "bg-amber-400";
          centerBg = "bg-amber-500";
        } else {
          pingBg = "bg-red-400";
          centerBg = "bg-red-600";
        }

        return L.divIcon({
          html: `<div class="relative flex items-center justify-center w-6 h-6">
              <span class="absolute inline-flex h-full w-full rounded-full ${pingBg} opacity-60 animate-ping"></span>
              <div class="relative rounded-full h-4.5 w-4.5 ${centerBg} border border-white shadow"></div>
            </div>`,
          className: "custom-leaflet-icon",
          iconSize: [24, 24],
          iconAnchor: [12, 12],
        });
      }

      // Incident warning pin
      if (status === "Critical") {
        pingBg = "bg-red-400";
        centerBg = "bg-red-600";
      } else if (status === "Elevated") {
        pingBg = "bg-amber-400";
        centerBg = "bg-amber-500";
      } else {
        pingBg = "bg-yellow-400";
        centerBg = "bg-yellow-500";
      }

      return L.divIcon({
        html: `<div class="relative flex items-center justify-center w-8 h-8">
            <span class="absolute inline-flex h-full w-full rounded-full ${pingBg} opacity-75 animate-ping"></span>
            <div class="relative flex items-center justify-center rounded-full h-6 w-6 ${centerBg} border border-white shadow text-white font-bold text-xs">!</div>
          </div>`,
        className: "custom-leaflet-icon",
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });
    };

    return {
      siteDefault: createIcon("siteDefault"),
      siteA: createIcon("site", "A"),
      siteB: createIcon("site", "B"),
      siteC: createIcon("site", "C"),
      siteD: createIcon("site", "D"),
      siteE: createIcon("site", "E"),
      incidentCritical: createIcon("incident", "Critical"),
      incidentElevated: createIcon("incident", "Elevated"),
      incidentModerate: createIcon("incident", "Moderate"),
    };
  }, [isMounted]);

  console.log("MapViewer State:", { isMounted, hasIcons: !!icons, hasL: !!L });

  if (!isMounted || !icons) {
    return <Loader message="Loading Regional Map (Component)..." />;
  }

  return (
    <div
      className={`${className || ""} ${zoomOffsetClass || ""}`}
      style={{ width: "100%", height: "100%" }}
    >
      <MapContainer
        center={center}
        zoom={zoom}
        scrollWheelZoom={true}
        zoomControl={false}
        style={{ width: "100%", height: "100%" }}
        key={`nbd-map-${center[0]}-${center[1]}`}
      >
        <TileLayer
          attribution="&copy; Google Maps"
          url="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"
        />
        <ZoomControl position="bottomright" />
        <MapController
          basinGeometry={basinGeometry}
          wetlandGeometry={wetlandGeometry}
          choroplethLayers={choroplethLayers}
        />

        {choroplethLayers && choroplethLayers.length > 0 && (
          <GeoJSON
            key={`choropleth-${choroplethLayers.length}-${selectedSubCounty?.properties?.name || ""}`}
            data={
              { type: "FeatureCollection", features: choroplethLayers } as any
            }
            onEachFeature={(feature, layer) => {
              const count = feature.properties?.incidentCount || 0;
              const isSelected =
                selectedSubCounty &&
                selectedSubCounty.properties?.name === feature.properties?.name;

              if (typeof (layer as any).setStyle === "function") {
                (layer as any).setStyle({
                  fillColor: getChoroplethColor(count),
                  fillOpacity: isSelected ? 0.8 : 0.45,
                  color: isSelected ? "#2563eb" : "#475569",
                  weight: isSelected ? 3.5 : 1.5,
                  opacity: 0.8,
                });
              }

              layer.on({
                mouseover: (e) => {
                  const l = e.target;
                  if (!isSelected && typeof l.setStyle === "function") {
                    l.setStyle({
                      weight: 3,
                      fillOpacity: 0.65,
                      color: "#1e293b",
                    });
                  }
                },
                mouseout: (e) => {
                  const l = e.target;
                  if (!isSelected && typeof l.setStyle === "function") {
                    l.setStyle({
                      weight: 1.5,
                      fillOpacity: 0.45,
                      color: "#475569",
                    });
                  }
                },
                click: () => {
                  if (onSelectSubCounty) {
                    onSelectSubCounty(feature);
                  }
                },
              });
            }}
          />
        )}

        {wetlandGeometry && (
          <GeoJSON
            key={JSON.stringify(wetlandGeometry)}
            data={wetlandGeometry}
            interactive={false}
            style={{
              color: "#14b8a6",
              weight: 2,
              opacity: 0.9,
              fillColor: "#14b8a6",
              fillOpacity: 0.12,
            }}
          />
        )}

        {basinGeometry && (
          <GeoJSON
            key={JSON.stringify(basinGeometry)}
            data={basinGeometry}
            interactive={false}
            style={{
              color: "#0d9488",
              weight: 2,
              opacity: 0.8,
              fillColor: "#0d9488",
              fillOpacity: 0.05,
            }}
          />
        )}
        {markers.map((marker, index) => {
          let icon;
          if (marker.type === "site") {
            if (!marker.status) icon = icons.siteDefault;
            else if (marker.status === "A") icon = icons.siteA;
            else if (marker.status === "B") icon = icons.siteB;
            else if (marker.status === "C") icon = icons.siteC;
            else if (marker.status === "D") icon = icons.siteD;
            else icon = icons.siteE;
          } else {
            if (marker.status === "Critical") icon = icons.incidentCritical;
            else if (marker.status === "Elevated")
              icon = icons.incidentElevated;
            else icon = icons.incidentModerate;
          }
          if (!icon) return null;
          return (
            <Marker
              key={index}
              position={marker.position}
              icon={icon}
              eventHandlers={{
                click: () => {
                  if (onSelectMarker && marker.code) {
                    onSelectMarker(marker.code, marker.type);
                  }
                },
              }}
            />
          );
        })}
      </MapContainer>
    </div>
  );
}

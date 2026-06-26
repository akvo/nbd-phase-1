import React, { useEffect, useState, useMemo } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
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
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function MapController({
  basinGeometry,
  wetlandGeometry,
}: {
  basinGeometry: any;
  wetlandGeometry: any;
}) {
  const map = useMap();

  useEffect(() => {
    const targetGeom = wetlandGeometry || basinGeometry;
    if (targetGeom) {
      try {
        const layer = L.geoJSON(targetGeom);
        map.fitBounds(layer.getBounds(), { padding: [30, 30] });
      } catch (err) {
        console.error("Failed to fit bounds to geometry:", err);
      }
    }
  }, [basinGeometry, wetlandGeometry, map]);

  return null;
}

export default function MapViewer({
  center,
  zoom,
  markers = [],
  className,
  zoomOffsetClass,
  basinGeometry,
  wetlandGeometry,
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
      let isWarningIcon = false;

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
      } else {
        isWarningIcon = true;
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
      }

      const htmlContent = isWarningIcon
        ? `<div class="relative flex items-center justify-center w-8 h-8">
            <span class="absolute inline-flex h-full w-full rounded-full ${pingBg} opacity-75 animate-ping"></span>
            <div class="relative flex items-center justify-center rounded-full h-6 w-6 ${centerBg} border border-white shadow text-white font-bold text-xs">!</div>
          </div>`
        : `<div class="relative flex items-center justify-center w-8 h-8">
            <span class="absolute inline-flex h-full w-full rounded-full ${pingBg} opacity-75 animate-ping"></span>
            <div class="relative flex items-center justify-center rounded-full h-6 w-6 ${centerBg} border border-white shadow text-white font-bold text-xs">${status || ""}</div>
          </div>`;

      return L.divIcon({
        html: htmlContent,
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
        />

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
            <Marker key={index} position={marker.position} icon={icon}>
              <Popup>
                <div className="p-1 min-w-[200px] flex flex-col gap-2 text-slate-800 font-sans">
                  <div className="flex justify-between items-start gap-3">
                    <div>
                      <h4 className="font-bold text-sm leading-tight text-slate-900">
                        {marker.name ||
                          (marker.type === "site"
                            ? "Monitoring Station"
                            : "Incident Report")}
                      </h4>
                      {marker.code && (
                        <span className="text-[10px] text-slate-400 font-mono block mt-0.5">
                          {marker.code}
                        </span>
                      )}
                    </div>
                    {marker.status && (
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          marker.type === "site"
                            ? ["D", "E"].includes(marker.status)
                              ? "bg-red-50 text-red-600 border border-red-200"
                              : marker.status === "C"
                                ? "bg-amber-50 text-amber-600 border border-amber-200"
                                : "bg-green-50 text-green-600 border border-green-200"
                            : marker.status === "Critical"
                              ? "bg-red-50 text-red-600 border border-red-200"
                              : marker.status === "Elevated"
                                ? "bg-orange-50 text-orange-600 border border-orange-200"
                                : "bg-yellow-50 text-yellow-600 border border-yellow-200"
                        }`}
                      >
                        {marker.status}
                      </span>
                    )}
                  </div>

                  {marker.type === "site" && marker.score !== undefined && (
                    <div className="space-y-1 mt-1">
                      <div className="flex justify-between text-[10px] font-medium text-slate-500">
                        <span>Health Index</span>
                        <span className="font-bold text-slate-700">
                          {marker.score}%
                        </span>
                      </div>
                      <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            ["D", "E"].includes(marker.status || "")
                              ? "bg-red-500"
                              : marker.status === "C"
                                ? "bg-amber-500"
                                : "bg-green-500"
                          }`}
                          style={{ width: `${marker.score}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {marker.description && (
                    <p className="text-[11px] text-slate-600 bg-slate-50 p-2 rounded border border-slate-100 leading-snug mt-1">
                      {marker.description}
                    </p>
                  )}

                  {!marker.name && !marker.code && marker.popupText && (
                    <div className="font-semibold text-sm text-slate-800 mt-1">
                      {marker.popupText}
                    </div>
                  )}

                  {marker.additionalInfo && (
                    <span className="text-[10px] text-slate-400 block mt-1 border-t border-slate-100 pt-1">
                      {marker.additionalInfo}
                    </span>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}

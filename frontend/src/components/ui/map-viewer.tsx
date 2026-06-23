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
}

interface MapViewerProps {
  center: [number, number];
  zoom: number;
  markers?: MapMarker[];
  className?: string;
  zoomOffsetClass?: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  basinGeometry?: any;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function MapController({ basinGeometry }: { basinGeometry: any }) {
  const map = useMap();

  useEffect(() => {
    if (basinGeometry) {
      try {
        const layer = L.geoJSON(basinGeometry);
        map.fitBounds(layer.getBounds(), { padding: [30, 30] });
      } catch (err) {
        console.error("Failed to fit bounds to basin geometry:", err);
      }
    }
  }, [basinGeometry, map]);

  return null;
}

function GestureHandling() {
  const map = useMap();

  useEffect(() => {
    if (typeof window === "undefined") return;

    // Check if it's mobile/touch device
    const isTouch = "ontouchstart" in window || navigator.maxTouchPoints > 0;
    if (!isTouch) return;

    // Disable dragging on touch devices by default
    map.dragging.disable();

    const handleTouchStart = (e: TouchEvent) => {
      if (e.touches.length >= 2) {
        map.dragging.enable();
      } else {
        map.dragging.disable();
      }
    };

    const handleTouchEnd = () => {
      map.dragging.disable();
    };

    const container = map.getContainer();
    container.addEventListener("touchstart", handleTouchStart, { passive: true });
    container.addEventListener("touchend", handleTouchEnd, { passive: true });

    return () => {
      container.removeEventListener("touchstart", handleTouchStart);
      container.removeEventListener("touchend", handleTouchEnd);
    };
  }, [map]);

  return null;
}

export default function MapViewer({
  center,
  zoom,
  markers = [],
  className,
  zoomOffsetClass,
  basinGeometry,
}: MapViewerProps) {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const icons = useMemo(() => {
    if (!isMounted || typeof window === "undefined" || !L) return null;

    const createIcon = (type: "site" | "incident", status?: string) => {
      let pingBg: string;
      let centerBg: string;
      let isWarningIcon = false;

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
          pingBg = "bg-orange-400";
          centerBg = "bg-orange-500";
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
        <MapController basinGeometry={basinGeometry} />
        <GestureHandling />
        {basinGeometry && (
          <GeoJSON
            key={JSON.stringify(basinGeometry)}
            data={basinGeometry}
            style={{
              color: "#0d9488",
              weight: 2,
              opacity: 0.8,
              fillColor: "#0d9488",
              fillOpacity: 0.05,
            }}
          />
        )}
        <TileLayer
          attribution="Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        />
        <ZoomControl position="bottomright" />
        {markers.map((marker, index) => {
          let icon;
          if (marker.type === "site") {
            if (marker.status === "A") icon = icons.siteA;
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
              {marker.popupText && (
                <Popup>
                  <div className="font-semibold text-sm text-slate-800">
                    {marker.popupText}
                  </div>
                </Popup>
              )}
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}

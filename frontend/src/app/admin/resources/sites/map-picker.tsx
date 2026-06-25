"use client";

import React, { useEffect, useState, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  useMapEvents,
  useMap,
} from "react-leaflet";
import * as L from "leaflet";

interface MapPickerProps {
  lat: number;
  lng: number;
  onMapClick: (lat: number, lng: number) => void;
}

// Component to handle map clicks
function MapClickHandler({
  onMapClick,
}: {
  onMapClick: (lat: number, lng: number) => void;
}) {
  useMapEvents({
    click: (e) => {
      onMapClick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

// Component to update map center when coordinates change
function MapCenterUpdater({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap();
  const prevCoords = useRef({ lat, lng });

  useEffect(() => {
    // Only pan if coordinates actually changed significantly
    if (
      Math.abs(prevCoords.current.lat - lat) > 0.0001 ||
      Math.abs(prevCoords.current.lng - lng) > 0.0001
    ) {
      if (!isNaN(lat) && !isNaN(lng)) {
        map.panTo([lat, lng]);
        prevCoords.current = { lat, lng };
      }
    }
  }, [lat, lng, map]);

  return null;
}

export default function MapPicker({ lat, lng, onMapClick }: MapPickerProps) {
  const [isMounted, setIsMounted] = useState(false);
  const [markerIcon, setMarkerIcon] = useState<L.DivIcon | null>(null);

  useEffect(() => {
    setIsMounted(true);

    // Create custom marker icon
    const icon = L.divIcon({
      html: `<div class="relative flex items-center justify-center w-8 h-8">
        <span class="absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75 animate-ping"></span>
        <div class="relative flex items-center justify-center rounded-full h-6 w-6 bg-sky-600 border-2 border-white shadow">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" class="w-3 h-3">
            <path fill-rule="evenodd" d="m11.54 22.351.07.04.028.016a.76.76 0 0 0 .723 0l.028-.015.071-.041a16.975 16.975 0 0 0 1.144-.742 19.58 19.58 0 0 0 2.683-2.282c1.944-1.99 3.963-4.98 3.963-8.827a8.25 8.25 0 0 0-16.5 0c0 3.846 2.02 6.837 3.963 8.827a19.58 19.58 0 0 0 2.682 2.282 16.975 16.975 0 0 0 1.145.742ZM12 13.5a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" clip-rule="evenodd" />
          </svg>
        </div>
      </div>`,
      className: "custom-leaflet-icon",
      iconSize: [32, 32],
      iconAnchor: [16, 32],
    });
    setMarkerIcon(icon);
  }, []);

  if (!isMounted || !markerIcon) {
    return (
      <div className="h-full w-full bg-slate-100 flex items-center justify-center text-slate-400">
        Loading map...
      </div>
    );
  }

  const validLat = isNaN(lat) ? -1.5 : lat;
  const validLng = isNaN(lng) ? 34.5 : lng;

  return (
    <MapContainer
      center={[validLat, validLng]}
      zoom={10}
      scrollWheelZoom={true}
      style={{ width: "100%", height: "100%" }}
    >
      <TileLayer
        attribution="Tiles &copy; Esri"
        url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
      />
      <MapClickHandler onMapClick={onMapClick} />
      <MapCenterUpdater lat={validLat} lng={validLng} />
      {!isNaN(lat) && !isNaN(lng) && (
        <Marker position={[lat, lng]} icon={markerIcon} />
      )}
    </MapContainer>
  );
}

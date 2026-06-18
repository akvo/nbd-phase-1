import { render } from "@testing-library/react";
import MapViewer from "../map-viewer";
import { expect, test, vi } from "vitest";

vi.mock("react-leaflet", () => {
  return {
    MapContainer: ({ children }: any) => (
      <div data-testid="map-container">{children}</div>
    ),
    TileLayer: () => <div data-testid="tile-layer" />,
    Marker: ({ children }: any) => <div data-testid="marker">{children}</div>,
    Popup: ({ children }: any) => <div data-testid="popup">{children}</div>,
    ZoomControl: () => <div data-testid="zoom-control" />,
    GeoJSON: ({ data }: any) => (
      <div data-testid="geojson" data-geojson={JSON.stringify(data)} />
    ),
    useMap: () => ({
      fitBounds: vi.fn(),
    }),
  };
});

vi.mock("leaflet", () => {
  return {
    divIcon: vi.fn(),
    geoJSON: () => ({
      getBounds: vi.fn(() => "mockBounds"),
    }),
  };
});

test("renders map container and mounts leaflet components", () => {
  const center: [number, number] = [0, 0];
  const { container } = render(<MapViewer center={center} zoom={13} />);
  expect(container.firstChild).toBeInTheDocument();
});

test("renders basin geometry overlay when provided", () => {
  const center: [number, number] = [0, 0];
  const mockGeoJson = {
    type: "Feature",
    geometry: { type: "MultiPolygon", coordinates: [] },
  };
  const { getByTestId } = render(
    <MapViewer center={center} zoom={13} basinGeometry={mockGeoJson} />
  );
  expect(getByTestId("geojson")).toBeInTheDocument();
});

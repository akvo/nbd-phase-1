import { render } from '@testing-library/react';
import MapViewer from '../map-viewer';
import { expect, test, vi } from 'vitest';

vi.mock('react-leaflet', () => {
  return {
    MapContainer: ({ children }: any) => <div data-testid="map-container">{children}</div>,
    TileLayer: () => <div data-testid="tile-layer" />,
    Marker: ({ children }: any) => <div data-testid="marker">{children}</div>,
    Popup: ({ children }: any) => <div data-testid="popup">{children}</div>,
    ZoomControl: () => <div data-testid="zoom-control" />,
  };
});

vi.mock('leaflet', () => {
  return {
    divIcon: vi.fn(),
  };
});

test('renders map container and mounts leaflet components', () => {
  const center: [number, number] = [0, 0];
  const { container } = render(<MapViewer center={center} zoom={13} />);
  expect(container.firstChild).toBeInTheDocument();
});

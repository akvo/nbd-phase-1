import { render, screen, fireEvent } from "@testing-library/react";
import Home from "../page";
import { expect, test, vi } from "vitest";

// Mock the MapViewer component to bypass leaflet loading in jsdom
vi.mock("@/components/ui/map-viewer", () => {
  return {
    default: () => <div data-testid="mock-map-viewer" />,
  };
});

vi.mock("@/lib/api", () => {
  return {
    getBasins: vi.fn().mockResolvedValue([]),
    getSites: vi.fn().mockResolvedValue([]),
    getSubmissions: vi.fn().mockResolvedValue([]),
  };
});

test("renders Home page elements and handles filtering", () => {
  render(<Home />);

  // Verify Logoipsum exists in header
  expect(screen.getByText("Logoipsum")).toBeInTheDocument();

  // Verify search input
  const searchInput = screen.getByPlaceholderText(
    "Search field, area, water source"
  );
  expect(searchInput).toBeInTheDocument();
  fireEvent.change(searchInput, { target: { value: "Gulu" } });

  // Verify filter buttons
  const allButton = screen.getByRole("button", { name: "All" });
  expect(allButton).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Critical" }));
});

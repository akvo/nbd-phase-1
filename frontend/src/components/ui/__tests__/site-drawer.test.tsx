import { render, screen, fireEvent } from "@testing-library/react";
import { SiteDrawer } from "../site-drawer";
import { expect, test, vi } from "vitest";

const mockSite = {
  site_id: "SITE-001",
  site_name: "Gulu Wetland",
  country: "Uganda",
  basin: "Victoria",
  current_health_class: "B",
  current_score: 0.82,
  last_updated: "2026-05-28",
  coordinates: [2.77, 32.28] as [number, number],
  community_signal: "High fish populations observed.",
  progress_percent: 85,
  is_approved: true,
  is_ik_adjusted: true,
  details: {
    physico_chemical: {
      group_score: 0.88,
      ph: 7.2,
      dissolved_oxygen: 6.8,
      temperature: 24.5,
      weights: { ph: 0.5, dissolved_oxygen: 0.5 },
    },
    catchment_hydrological: { group_score: 0.79 },
    ecological: { group_score: 0.81 },
    ik_signal: {
      encoded_signal_value: 0.8,
      fish_abundance: "HIGH",
      water_clarity: "CLEAR",
      vegetation_cover: "STABLE",
    },
    management_actions: [
      { label: "Revegetation", description: "Plant native reeds." },
    ],
  },
};

test("renders site drawer details", () => {
  const handleClose = vi.fn();
  render(<SiteDrawer site={mockSite} onClose={handleClose} />);

  expect(screen.getByText("Gulu Wetland")).toBeInTheDocument();
  expect(screen.getByText("Uganda")).toBeInTheDocument();
  expect(screen.getByText("Community signal:")).toBeInTheDocument();
  expect(screen.getByText("Revegetation")).toBeInTheDocument();

  const closeButton = screen.getByText("✕");
  fireEvent.click(closeButton);
  expect(handleClose).toHaveBeenCalled();
});

test("returns null when site is null", () => {
  const { container } = render(<SiteDrawer site={null} onClose={vi.fn()} />);
  expect(container.firstChild).toBeNull();
});

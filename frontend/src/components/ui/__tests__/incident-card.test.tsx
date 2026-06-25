import { render, screen, fireEvent } from "@testing-library/react";
import { IncidentCard } from "../incident-card";
import { vi, test, expect } from "vitest";

const base = {
  incidentTypeName: "Fish kill",
  severity: "Critical" as const,
  dateReported: "2026-06-01T10:00:00Z",
  description: "Large-scale fish mortality observed near the river mouth.",
  basinName: "Mara Basin",
};

test("renders incident type name", () => {
  render(<IncidentCard {...base} />);
  expect(screen.getByText("Fish kill")).toBeInTheDocument();
});

test("renders severity badge with correct label", () => {
  render(<IncidentCard {...base} />);
  expect(screen.getByText("Critical")).toBeInTheDocument();
});

test("renders basin name chip when provided", () => {
  render(<IncidentCard {...base} />);
  expect(screen.getByText("Mara Basin")).toBeInTheDocument();
});

test("gracefully handles missing description", () => {
  render(<IncidentCard {...base} description="" />);
  expect(screen.getByText("No details recorded.")).toBeInTheDocument();
});

test("calls onClick when clicked", () => {
  const onClick = vi.fn();
  render(<IncidentCard {...base} onClick={onClick} />);
  fireEvent.click(screen.getByText("Fish kill"));
  expect(onClick).toHaveBeenCalled();
});

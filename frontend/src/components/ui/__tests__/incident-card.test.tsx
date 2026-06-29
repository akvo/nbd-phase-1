import { render, screen, fireEvent } from "@testing-library/react";
import { IncidentCard } from "../incident-card";
import { vi, test, expect } from "vitest";

const base = {
  incidentTypeName: "Fish kill",
  severity: "Critical" as const,
  dateReported: "2026-06-01T10:00:00Z",
  description: "Large-scale fish mortality observed near the river mouth.",
  subCountyName: "Mara Subcounty",
};

test("renders incident type name", () => {
  render(<IncidentCard {...base} />);
  expect(screen.getByText("Fish kill")).toBeInTheDocument();
});

test("renders severity badge with correct label", () => {
  render(<IncidentCard {...base} />);
  expect(screen.getByText("Critical")).toBeInTheDocument();
});

test("renders sub-county name chip when provided", () => {
  render(<IncidentCard {...base} />);
  expect(screen.getByText("Mara Subcounty")).toBeInTheDocument();
});

test("hides description element when missing or empty", () => {
  const { queryByText } = render(<IncidentCard {...base} description="" />);
  expect(queryByText("No details recorded.")).not.toBeInTheDocument();
});

test("calls onClick when clicked and not disabled", () => {
  const onClick = vi.fn();
  render(<IncidentCard {...base} onClick={onClick} />);
  fireEvent.click(screen.getByText("Fish kill"));
  expect(onClick).toHaveBeenCalled();
});

test("does not call onClick when click is disabled", () => {
  const onClick = vi.fn();
  render(<IncidentCard {...base} onClick={onClick} disableClick={true} />);
  fireEvent.click(screen.getByText("Fish kill"));
  expect(onClick).not.toHaveBeenCalled();
});

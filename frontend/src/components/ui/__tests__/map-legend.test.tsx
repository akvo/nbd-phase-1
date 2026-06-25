import { render, screen } from "@testing-library/react";
import { MapLegend } from "../map-legend";
import { expect, test } from "vitest";

test("renders map legend details for wetland domain", () => {
  render(<MapLegend domain="wetland" />);
  expect(screen.getByText("Legend")).toBeInTheDocument();
  expect(screen.getByText("Healthy (A / B)")).toBeInTheDocument();
  expect(screen.getByText("At Risk (C)")).toBeInTheDocument();
  expect(screen.getByText("Critical (D / E)")).toBeInTheDocument();
});

test("renders map legend details for pollution domain", () => {
  render(<MapLegend domain="pollution" />);
  expect(screen.getByText("Legend")).toBeInTheDocument();
  expect(screen.queryByText("Healthy (A / B)")).not.toBeInTheDocument();
  expect(screen.getByText("Critical Severity")).toBeInTheDocument();
});

import { render, screen } from "@testing-library/react";
import { MapLegend } from "../map-legend";
import { expect, test } from "vitest";

test("renders map legend details", () => {
  render(<MapLegend />);
  expect(screen.getByText("Legend")).toBeInTheDocument();
  expect(screen.getByText("Healthy (A / B)")).toBeInTheDocument();
  expect(screen.getByText("At Risk (C)")).toBeInTheDocument();
  expect(screen.getByText("Critical (D / E)")).toBeInTheDocument();
});

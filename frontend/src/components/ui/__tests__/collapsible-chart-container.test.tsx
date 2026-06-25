import { render, screen, fireEvent } from "@testing-library/react";
import { CollapsibleChartContainer } from "../collapsible-chart-container";
import { expect, test, vi } from "vitest";

// Mock the EChartsChart component since it uses DOM manipulation not fully supported in jsdom
vi.mock("../echarts-chart", () => ({
  EChartsChart: vi.fn(() => <div data-testid="mock-echarts-chart" />),
}));

vi.mock("@/lib/charts", () => ({
  getHistoricalChartOptions: vi.fn(() => ({})),
}));

const mockData = [
  { date: "2026-05-01T00:00:00Z", value: 7.2 },
  { date: "2026-05-15T00:00:00Z", value: 7.5 },
];

test("renders trend toggle button", () => {
  render(<CollapsibleChartContainer label="pH" data={mockData} />);

  const toggleBtn = screen.getByText("Show Trend");
  expect(toggleBtn).toBeInTheDocument();
});

test("collapses and expands the chart on click", () => {
  render(<CollapsibleChartContainer label="pH" data={mockData} />);

  // Should be closed by default
  expect(screen.queryByTestId("mock-echarts-chart")).not.toBeInTheDocument();

  // Click to open
  const toggleBtn = screen.getByText("Show Trend");
  fireEvent.click(toggleBtn);

  expect(screen.getByText("Hide Trend")).toBeInTheDocument();
  expect(screen.getByTestId("mock-echarts-chart")).toBeInTheDocument();

  // Click to close again
  fireEvent.click(toggleBtn);
  expect(screen.getByText("Show Trend")).toBeInTheDocument();
  expect(screen.queryByTestId("mock-echarts-chart")).not.toBeInTheDocument();
});

test("shows fallback message when data is empty", () => {
  render(<CollapsibleChartContainer label="pH" data={[]} />);

  const toggleBtn = screen.getByText("Show Trend");
  fireEvent.click(toggleBtn);

  expect(
    screen.getByText("No historical data for this period")
  ).toBeInTheDocument();
  expect(screen.queryByTestId("mock-echarts-chart")).not.toBeInTheDocument();
});

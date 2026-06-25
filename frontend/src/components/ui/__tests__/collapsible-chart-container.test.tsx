import { render, screen, fireEvent } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { CollapsibleChartContainer } from "../collapsible-chart-container";
import { expect, test, vi } from "vitest";
import messages from "../../../../messages/en.json";

// Mock the EChartsChart component since it uses DOM manipulation not fully supported in jsdom
vi.mock("../echarts-chart", () => ({
  EChartsChart: vi.fn(() => <div data-testid="mock-echarts-chart" />),
}));

vi.mock("@/lib/charts", () => ({
  getHistoricalChartOptions: vi.fn(() => ({})),
}));

const renderWithIntl = (ui: React.ReactElement) => {
  return render(
    <NextIntlClientProvider messages={messages} locale="en">
      {ui}
    </NextIntlClientProvider>
  );
};

const mockData = [
  { date: "2026-05-01T00:00:00Z", value: 7.2 },
  { date: "2026-05-15T00:00:00Z", value: 7.5 },
];

test("renders trend toggle button", () => {
  renderWithIntl(<CollapsibleChartContainer label="pH" data={mockData} />);

  const toggleBtn = screen.getByText(messages.drawer.showTrend);
  expect(toggleBtn).toBeInTheDocument();
});

test("collapses and expands the chart on click", () => {
  renderWithIntl(<CollapsibleChartContainer label="pH" data={mockData} />);

  // Should be closed by default
  expect(screen.queryByTestId("mock-echarts-chart")).not.toBeInTheDocument();

  // Click to open
  const toggleBtn = screen.getByText(messages.drawer.showTrend);
  fireEvent.click(toggleBtn);

  expect(screen.getByText(messages.drawer.hideTrend)).toBeInTheDocument();
  expect(screen.getByTestId("mock-echarts-chart")).toBeInTheDocument();

  // Click to close again
  fireEvent.click(toggleBtn);
  expect(screen.getByText(messages.drawer.showTrend)).toBeInTheDocument();
  expect(screen.queryByTestId("mock-echarts-chart")).not.toBeInTheDocument();
});

test("shows fallback message when data is empty", () => {
  renderWithIntl(<CollapsibleChartContainer label="pH" data={[]} />);

  const toggleBtn = screen.getByText(messages.drawer.showTrend);
  fireEvent.click(toggleBtn);

  expect(
    screen.getByText(messages.drawer.noHistoricalData)
  ).toBeInTheDocument();
  expect(screen.queryByTestId("mock-echarts-chart")).not.toBeInTheDocument();
});

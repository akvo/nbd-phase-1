import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { MapLegend } from "../map-legend";
import { expect, test } from "vitest";
import messages from "../../../../messages/en.json";

const renderWithIntl = (ui: React.ReactElement) => {
  return render(
    <NextIntlClientProvider messages={messages} locale="en">
      {ui}
    </NextIntlClientProvider>
  );
};

test("renders map legend details for wetland domain", () => {
  renderWithIntl(<MapLegend domain="wetland" />);
  expect(screen.getByText(messages.legend.title)).toBeInTheDocument();
  expect(screen.getByText(messages.legend.healthy)).toBeInTheDocument();
  expect(screen.getByText(messages.legend.atRisk)).toBeInTheDocument();
  expect(screen.getByText(messages.legend.critical)).toBeInTheDocument();
  expect(screen.queryByText(messages.legend.criticalSeverity)).not.toBeInTheDocument();
});

test("renders map legend details for pollution domain", () => {
  renderWithIntl(<MapLegend domain="pollution" />);
  expect(screen.getByText(messages.legend.title)).toBeInTheDocument();
  expect(screen.queryByText(messages.legend.healthy)).not.toBeInTheDocument();
  expect(screen.getByText(messages.legend.criticalSeverity)).toBeInTheDocument();
  expect(screen.getByText(messages.legend.elevatedSeverity)).toBeInTheDocument();
  expect(screen.getByText(messages.legend.moderateSeverity)).toBeInTheDocument();
});

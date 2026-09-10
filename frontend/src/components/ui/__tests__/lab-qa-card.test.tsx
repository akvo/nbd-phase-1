import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { LabQaCard } from "../site-drawer/lab-qa-card";
import { expect, test } from "vitest";
import enMessages from "../../../../messages/en.json";
import swMessages from "../../../../messages/sw.json";
import { LabQaReport } from "@/lib/api";

const renderWithEn = (ui: React.ReactElement) => {
  return render(
    <NextIntlClientProvider messages={enMessages} locale="en">
      {ui}
    </NextIntlClientProvider>
  );
};

const renderWithSw = (ui: React.ReactElement) => {
  return render(
    <NextIntlClientProvider messages={swMessages} locale="sw">
      {ui}
    </NextIntlClientProvider>
  );
};

test("renders empty state when report is null", () => {
  const t = (key: string) =>
    (enMessages.drawer as Record<string, string>)[key] || key;
  const tm = (key: string) =>
    (enMessages.metrics as Record<string, string>)[key] || key;

  renderWithEn(<LabQaCard report={null} t={t} tm={tm} locale="en" />);

  expect(screen.getByText(enMessages.drawer.noLabQaData)).toBeInTheDocument();
  expect(screen.getByText(enMessages.drawer.labQaReport)).toBeInTheDocument();
});

test("renders empty state when report has no metrics", () => {
  const t = (key: string) =>
    (enMessages.drawer as Record<string, string>)[key] || key;
  const tm = (key: string) =>
    (enMessages.metrics as Record<string, string>)[key] || key;

  const emptyReport: LabQaReport = {
    id: 1,
    created_at: "2026-08-10T10:00:00Z",
    status: "APPROVED",
    submitter: "Chemist",
    metrics: {},
  };

  renderWithEn(<LabQaCard report={emptyReport} t={t} tm={tm} locale="en" />);

  expect(screen.getByText(enMessages.drawer.noLabQaData)).toBeInTheDocument();
});

test("renders full approved lab report with metrics and metadata", () => {
  const t = (key: string) =>
    (enMessages.drawer as Record<string, string>)[key] || key;
  const tm = (key: string) =>
    (enMessages.metrics as Record<string, string>)[key] || key;

  const report: LabQaReport = {
    id: 42,
    created_at: "2026-08-15T09:00:00Z",
    status: "APPROVED",
    submitter: "Senior Chemist",
    metrics: {
      lab_ph: {
        value: 7.35,
        unit: null,
        status: "Verified",
        label: "pH (Lab)",
        icon: "droplet",
      },
      bod: {
        value: 3.2,
        unit: "mg/L",
        status: "Verified",
        label: "BOD",
        icon: "flask-conical",
      },
      heavy_metals: {
        value: "None detected",
        unit: null,
        status: "Verified",
        label: "Heavy Metals Screening",
        icon: "shield-alert",
      },
      orthophosphate: {
        value: 0.05,
        unit: "mg/L",
        status: "Verified",
        label: "Orthophosphate",
        icon: "test-tube",
      },
    },
  };

  renderWithEn(<LabQaCard report={report} t={t} tm={tm} locale="en" />);

  expect(screen.getByText(enMessages.drawer.labQaReport)).toBeInTheDocument();

  // Metrics
  expect(screen.getByText("7.35")).toBeInTheDocument();
  expect(screen.getByText("3.2")).toBeInTheDocument();
  expect(screen.getByText("None detected")).toBeInTheDocument();
  expect(screen.getByText("0.05")).toBeInTheDocument();

  // All 4 metrics verified
  const verifiedBadges = screen.getAllByText(enMessages.drawer.verified);
  expect(verifiedBadges.length).toBe(4);
});

test("renders lab report correctly in Swahili locale", () => {
  const t = (key: string) =>
    (swMessages.drawer as Record<string, string>)[key] || key;
  const tm = (key: string) =>
    (swMessages.metrics as Record<string, string>)[key] || key;

  const report: LabQaReport = {
    id: 43,
    created_at: "2026-08-15T09:00:00Z",
    status: "APPROVED",
    submitter: "Mtaalamu",
    metrics: {
      lab_ph: {
        value: 7.1,
        unit: null,
        status: "Verified",
        label: "pH (Lab)",
        icon: "droplet",
      },
    },
  };

  renderWithSw(<LabQaCard report={report} t={t} tm={tm} locale="sw" />);

  expect(screen.getByText(swMessages.drawer.labQaReport)).toBeInTheDocument();
  expect(screen.getByText(swMessages.drawer.verified)).toBeInTheDocument();
  expect(screen.getByText(swMessages.metrics.lab_ph)).toBeInTheDocument();
});

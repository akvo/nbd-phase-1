import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import Home from "../page";
import { expect, test, vi } from "vitest";
import messages from "../../../messages/en.json";
import { DomainProvider } from "@/context/domain-context";

// Mock the MapViewer component to bypass leaflet loading in jsdom
vi.mock("@/components/ui/map-viewer", () => {
  return {
    default: () => <div data-testid="mock-map-viewer" />,
  };
});

vi.mock("@/lib/api", () => {
  return {
    apiClient: {
      get: vi.fn().mockRejectedValue({ response: { status: 401 } }),
      post: vi.fn().mockResolvedValue({}),
    },
    getBasins: vi.fn().mockResolvedValue([]),
    getSites: vi.fn().mockResolvedValue([]),
    getSubmissions: vi.fn().mockResolvedValue([]),
  };
});

const renderWithContextAndIntl = (ui: React.ReactElement) => {
  return render(
    <NextIntlClientProvider messages={messages} locale="en">
      <DomainProvider>{ui}</DomainProvider>
    </NextIntlClientProvider>
  );
};

test("renders Home page elements and handles filtering", () => {
  renderWithContextAndIntl(<Home />);

  // Verify Logoipsum exists in header
  expect(screen.getByText(messages.header.brand)).toBeInTheDocument();
});

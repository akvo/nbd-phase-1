import { render, screen, fireEvent } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import Home from "../page";
import { expect, test, vi } from "vitest";
import messages from "../../../messages/en.json";

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

const renderWithIntl = (ui: React.ReactElement) => {
  return render(
    <NextIntlClientProvider messages={messages} locale="en">
      {ui}
    </NextIntlClientProvider>
  );
};

test("renders Home page elements and handles filtering", () => {
  renderWithIntl(<Home />);

  // Verify Logoipsum exists in header
  expect(screen.getByText(messages.header.brand)).toBeInTheDocument();

  // Verify search input
  const searchInput = screen.getByPlaceholderText(
    messages.landing.searchPlaceholder
  );
  expect(searchInput).toBeInTheDocument();
  fireEvent.change(searchInput, { target: { value: "Gulu" } });

  // Verify filter buttons
  const allButton = screen.getByRole("button", {
    name: messages.landing.filters.all,
  });
  expect(allButton).toBeInTheDocument();
  fireEvent.click(
    screen.getByRole("button", { name: messages.landing.filters.critical })
  );
});

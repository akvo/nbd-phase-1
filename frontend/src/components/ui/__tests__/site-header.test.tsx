import { render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { SiteHeader } from "../site-header";
import { expect, test, vi, beforeEach } from "vitest";
import * as api from "@/lib/api";
import messages from "../../../../messages/en.json";

// Mock apiClient to simulate unauthenticated state by default
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    apiClient: {
      get: vi.fn().mockRejectedValue({ response: { status: 401 } }),
      post: vi.fn().mockResolvedValue({}),
    },
  };
});

const renderWithIntl = (ui: React.ReactElement) => {
  return render(
    <NextIntlClientProvider messages={messages} locale="en">
      {ui}
    </NextIntlClientProvider>
  );
};

beforeEach(() => {
  vi.clearAllMocks();
  // Default: unauthenticated
  (api.apiClient.get as ReturnType<typeof vi.fn>).mockRejectedValue({
    response: { status: 401 },
  });
});

test("renders logo", async () => {
  renderWithIntl(<SiteHeader showActions={true} />);
  expect(screen.getByText(messages.header.brand)).toBeInTheDocument();
});

test("shows Log in button when unauthenticated", async () => {
  renderWithIntl(<SiteHeader showActions={true} />);
  await waitFor(() => {
    expect(
      screen.getByRole("button", {
        name: new RegExp(messages.common.login, "i"),
      })
    ).toBeInTheDocument();
  });
});

test("shows user menu button when authenticated", async () => {
  (api.apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValue({
    data: {
      id: "1",
      email: "admin@example.com",
      role: "Admin",
      display_name: "Admin User",
    },
  });

  renderWithIntl(<SiteHeader showActions={true} />);
  await waitFor(() => {
    expect(
      screen.getByRole("button", { name: /user menu/i })
    ).toBeInTheDocument();
  });
});

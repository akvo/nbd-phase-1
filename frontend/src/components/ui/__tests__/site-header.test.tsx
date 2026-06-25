import { render, screen, waitFor } from "@testing-library/react";
import { SiteHeader } from "../site-header";
import { expect, test, vi, beforeEach } from "vitest";
import * as api from "@/lib/api";

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

beforeEach(() => {
  vi.clearAllMocks();
  // Default: unauthenticated
  (api.apiClient.get as ReturnType<typeof vi.fn>).mockRejectedValue({
    response: { status: 401 },
  });
});

test("renders logo", async () => {
  render(<SiteHeader showActions={true} />);
  expect(screen.getByText("Logoipsum")).toBeInTheDocument();
});

test("shows Log in button when unauthenticated", async () => {
  render(<SiteHeader showActions={true} />);
  await waitFor(() => {
    expect(screen.getByRole("button", { name: /log in/i })).toBeInTheDocument();
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

  render(<SiteHeader showActions={true} />);
  await waitFor(() => {
    expect(
      screen.getByRole("button", { name: /user menu/i })
    ).toBeInTheDocument();
  });
});

test("renders toggle menu when actions are disabled", () => {
  render(<SiteHeader showActions={false} />);
  expect(
    screen.getByRole("button", { name: /toggle menu/i })
  ).toBeInTheDocument();
});

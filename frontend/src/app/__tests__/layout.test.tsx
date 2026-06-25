import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

// Mock Next.js font
vi.mock("next/font/google", () => ({
  Inter: () => ({
    className: "inter-mock",
    variable: "--font-inter",
  }),
}));

// Mock Next.js navigation hooks used by AuthProvider
vi.mock("next/navigation", () => {
  return {
    useRouter: () => ({
      push: vi.fn(),
      replace: vi.fn(),
      prefetch: vi.fn(),
    }),
    usePathname: () => "/",
  };
});

// Mock the API client
vi.mock("@/lib/api", () => {
  return {
    apiClient: {
      get: vi.fn(() => Promise.resolve({ data: null })),
      post: vi.fn(() => Promise.resolve({ data: {} })),
    },
  };
});

// Mock next-intl server functions
vi.mock("next-intl/server", () => ({
  getLocale: vi.fn(() => Promise.resolve("en")),
  getMessages: vi.fn(() =>
    Promise.resolve({
      common: { login: "Log in", signOut: "Sign out" },
    })
  ),
}));

// Mock next-intl client provider
vi.mock("next-intl", () => ({
  NextIntlClientProvider: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
}));

// Import after mocks
import RootLayout from "../layout";

test("renders root layout with children", async () => {
  const layout = await RootLayout({
    children: <div data-testid="layout-child">Child Element</div>,
  });

  render(layout);

  expect(screen.getByTestId("layout-child")).toBeInTheDocument();
  expect(screen.getByText("Child Element")).toBeInTheDocument();
});

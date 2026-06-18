import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

// Mock Next.js navigation
vi.mock("next/navigation", () => {
  return {
    useSearchParams: () => ({
      get: vi.fn(() => null),
    }),
  };
});

// Mock next/script
vi.mock("next/script", () => {
  return {
    default: ({ children, ...props }: any) => null,
  };
});

// Mock API client
vi.mock("@/lib/api", () => {
  return {
    apiClient: {
      get: vi.fn(() => Promise.resolve({ data: null })),
      post: vi.fn(() => Promise.resolve({ data: {} })),
    },
  };
});

// Import after mocks
import LoginPage from "../page";

test("renders login page elements and validations", () => {
  render(<LoginPage />);

  // Verify page title
  expect(screen.getByText("Log in to your account")).toBeInTheDocument();
  expect(
    screen.getByText("Citizen-Led Wetland Monitoring Platform")
  ).toBeInTheDocument();

  // Verify no Sign Up / Register button exists (SSO-only)
  expect(screen.queryByText(/sign up/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/register/i)).not.toBeInTheDocument();

  // Verify invite-only notice
  expect(
    screen.getByText(/No account\? Contact your platform administrator/i)
  ).toBeInTheDocument();
  expect(
    screen.getByText(/Self-registration is not available/i)
  ).toBeInTheDocument();
});

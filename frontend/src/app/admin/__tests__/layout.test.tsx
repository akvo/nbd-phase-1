import { render, screen } from "@testing-library/react";
import { expect, test, vi, describe } from "vitest";
import AdminLayout from "../layout";

// Mock Next.js navigation
vi.mock("next/navigation", () => {
  return {
    usePathname: () => "/admin/data",
    useRouter: () => ({
      push: vi.fn(),
      replace: vi.fn(),
      prefetch: vi.fn(),
    }),
  };
});

// Mock apiClient
vi.mock("@/lib/api", () => {
  return {
    apiClient: {
      get: vi.fn(() => Promise.resolve({ data: [] })),
      post: vi.fn(() => Promise.resolve({ data: {} })),
    },
  };
});

// Mock useAuth hook
vi.mock("@/context/AuthContext", () => {
  return {
    useAuth: () => ({
      user: {
        id: "test-user-id",
        email: "admin@test.com",
        role: "Admin",
        display_name: "Test Admin",
        avatar_url: null,
      },
      loading: false,
      error: null,
      logout: vi.fn(),
      refresh: vi.fn(),
      isAdmin: true,
      isReviewer: false,
    }),
  };
});

describe("Admin Top-Nav Layout", () => {
  test("renders top navigation and headers", () => {
    render(
      <AdminLayout>
        <div data-testid="admin-content">Data list content</div>
      </AdminLayout>
    );

    // Verify main top navigation links exist
    expect(
      screen.getByRole("link", { name: "Admin view" })
    ).toBeInTheDocument();
    // expect(screen.getByRole("link", { name: "Projects" })).toBeInTheDocument();
    // expect(screen.getByRole("link", { name: "Tasks" })).toBeInTheDocument();

    // Verify active link state for main header link
    const adminViewLink = screen.getByRole("link", { name: "Admin view" });
    expect(adminViewLink).toHaveClass("bg-sky-50");

    // Verify right utility header buttons
    expect(
      screen.getByRole("button", { name: "Settings" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Notifications" })
    ).toBeInTheDocument();
  });

  test("renders page title, badges, action buttons and sub-nav tabs", () => {
    render(
      <AdminLayout>
        <div data-testid="admin-content">Data list content</div>
      </AdminLayout>
    );

    // Verify overview title and instance count badge
    expect(screen.getByText("Data overview")).toBeInTheDocument();
    // expect(screen.getByText("240 instances")).toBeInTheDocument();

    // Verify action buttons
    expect(
      screen.getByRole("button", { name: "Download CSV" })
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add new" })).toBeInTheDocument();

    // Verify secondary sub-navigation tabs
    expect(screen.getByRole("link", { name: "Data" })).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Resource management" })
    ).toBeInTheDocument();

    // Verify active tab matching
    const dataTab = screen.getByRole("link", { name: "Data" });
    expect(dataTab).toHaveAttribute("data-active", "true");

    // Verify dynamic children injection
    expect(screen.getByTestId("admin-content")).toBeInTheDocument();
  });
});

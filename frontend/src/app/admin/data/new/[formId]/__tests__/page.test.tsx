import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { expect, test, vi, describe } from "vitest";
import React from "react";

// Mock React.use hook to prevent suspension in testing
vi.mock("react", async () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const actual = await vi.importActual<any>("react");
  return {
    ...actual,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    use: (_promise: any) => {
      return { formId: "fgd" };
    },
  };
});

import NewFormPage from "../page";

// Mock Next.js navigation
vi.mock("next/navigation", () => {
  return {
    useRouter: () => ({
      push: vi.fn(),
      replace: vi.fn(),
      prefetch: vi.fn(),
    }),
  };
});

// Mock apiClient
const mockGet = vi.fn();
const mockPost = vi.fn();
vi.mock("@/lib/api", () => {
  return {
    apiClient: {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      get: (...args: any[]) => mockGet(...args),
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      post: (...args: any[]) => mockPost(...args),
    },
  };
});

// Mock akvo-react-form
vi.mock("akvo-react-form", () => {
  return {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    Webform: ({ forms, onFinish }: any) => (
      <div data-testid="mock-webform">
        <span>Form: {forms?.name}</span>
        <button
          data-testid="submit-btn"
          onClick={() => onFinish({ "1": "GOOD", wetland_id: 1 })}
        >
          Submit Form
        </button>
      </div>
    ),
  };
});

describe("NewFormPage", () => {
  test("renders form blueprint when loaded successfully", async () => {
    mockGet.mockResolvedValueOnce({
      data: {
        form_id: 1,
        name: "Focus Group Discussion",
        type: 3,
        question_group: [],
      },
    });

    const params = Promise.resolve({ formId: "fgd" });
    render(<NewFormPage params={params} />);

    // Shows loading first
    expect(
      screen.getByText(/Fetching form blueprint definition/i)
    ).toBeInTheDocument();

    // Eventually loads blueprint
    await waitFor(() => {
      expect(screen.queryByText(/Fetching/i)).not.toBeInTheDocument();
      expect(screen.getByTestId("mock-webform")).toBeInTheDocument();
    });

    expect(
      screen.getByText("Form: Focus Group Discussion")
    ).toBeInTheDocument();
  });

  test("submits successfully for FGD type", async () => {
    mockGet.mockResolvedValueOnce({
      data: {
        form_id: 1,
        name: "Focus Group Discussion",
        type: 3,
        question_group: [],
      },
    });
    mockPost.mockResolvedValueOnce({ data: { success: true } });

    const params = Promise.resolve({ formId: "fgd" });
    render(<NewFormPage params={params} />);

    await waitFor(() => {
      expect(screen.getByTestId("mock-webform")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("submit-btn"));

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith("/internal/fgd", {
        "1": "GOOD",
        wetland_id: 1,
        form_id: 1,
      });
    });
  });
});

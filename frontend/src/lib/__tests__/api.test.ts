import { expect, test, vi, describe, beforeEach } from "vitest";

const { mockCreate, mockGet } = vi.hoisted(() => {
  const mockGet = vi.fn();
  const mockCreate = vi.fn((config?: any) => ({
    get: mockGet,
  }));
  return { mockCreate, mockGet };
});

// Mock axios module
vi.mock("axios", () => {
  return {
    default: {
      create: (config?: any) => (mockCreate as any)(config),
    },
  };
});

// Import after setting up mocks
import { apiClient, getBasins } from "../api";

describe("API Client", () => {
  beforeEach(() => {
    // Only clear the mockGet call history, do not clear mockCreate
    // because mockCreate was called once during module import.
    mockGet.mockClear();
  });

  test("apiClient is configured with correct baseURL and headers", () => {
    expect(mockCreate).toHaveBeenCalledWith({
      baseURL: "/api/v1",
      headers: {
        "Content-Type": "application/json",
      },
    });
    expect(apiClient).toBeDefined();
  });

  test("getBasins fetches data from correct endpoint and returns response data", async () => {
    const mockData = [{ id: "basin-1", name: "Mara Basin" }];
    mockGet.mockResolvedValue({ data: mockData });

    const result = await getBasins();

    expect(apiClient.get).toHaveBeenCalledWith("/basins");
    expect(result).toEqual(mockData);
  });
});

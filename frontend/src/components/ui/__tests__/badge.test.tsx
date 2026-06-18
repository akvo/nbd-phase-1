import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Badge } from "../badge";

describe("Badge Component", () => {
  it("renders primary variant by default", () => {
    render(<Badge>Test Badge</Badge>);
    const element = screen.getByText("Test Badge");
    expect(element).toBeInTheDocument();
    expect(element).toHaveClass("bg-nbd-secondary");
  });

  it("renders success variant correctly", () => {
    render(<Badge variant="success">Success Badge</Badge>);
    const element = screen.getByText("Success Badge");
    expect(element).toBeInTheDocument();
    expect(element).toHaveClass("bg-green-100");
  });
});

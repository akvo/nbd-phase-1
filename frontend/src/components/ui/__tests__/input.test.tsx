import { render, screen, fireEvent } from "@testing-library/react";
import { Input } from "../input";
import { expect, test, vi } from "vitest";

test("renders input with default placeholder", () => {
  render(<Input placeholder="Enter email" />);
  const input = screen.getByPlaceholderText("Enter email");
  expect(input).toBeInTheDocument();
  expect(input).toHaveAttribute("data-slot", "input");
});

test("handles typing events", () => {
  const handleChange = vi.fn();
  render(<Input placeholder="Enter email" onChange={handleChange} />);
  const input = screen.getByPlaceholderText("Enter email");
  fireEvent.change(input, { target: { value: "test@example.com" } });
  expect(handleChange).toHaveBeenCalled();
});

test("supports disabled state", () => {
  render(<Input disabled placeholder="Disabled input" />);
  const input = screen.getByPlaceholderText("Disabled input");
  expect(input).toBeDisabled();
});

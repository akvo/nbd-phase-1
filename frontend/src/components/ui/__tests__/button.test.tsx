import { render, screen, fireEvent } from "@testing-library/react";
import { Button } from "../button";
import { expect, test, vi } from "vitest";

test("renders button with children", () => {
  render(<Button>Click me</Button>);
  const button = screen.getByRole("button", { name: /click me/i });
  expect(button).toBeInTheDocument();
  expect(button).toHaveAttribute("data-slot", "button");
});

test("applies custom variant classes", () => {
  render(<Button variant="destructive">Delete</Button>);
  const button = screen.getByRole("button", { name: /delete/i });
  expect(button.className).toContain("bg-destructive");
});

test("handles click events", () => {
  const handleClick = vi.fn();
  render(<Button onClick={handleClick}>Click me</Button>);
  const button = screen.getByRole("button", { name: /click me/i });
  fireEvent.click(button);
  expect(handleClick).toHaveBeenCalledTimes(1);
});

test("does not trigger click when disabled", () => {
  const handleClick = vi.fn();
  render(
    <Button disabled onClick={handleClick}>
      Click me
    </Button>
  );
  const button = screen.getByRole("button", { name: /click me/i });
  expect(button).toBeDisabled();
});

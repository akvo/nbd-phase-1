import { render, screen, fireEvent } from "@testing-library/react";
import { Toggle } from "../toggle";
import { expect, test, vi } from "vitest";

test("renders toggle with label and checked status", () => {
  render(<Toggle checked={true} label="Notifications" onChange={vi.fn()} />);
  expect(screen.getByText("Notifications")).toBeInTheDocument();
  expect(screen.getByRole("switch")).toHaveAttribute("aria-checked", "true");
});

test("handles state toggle change", () => {
  const handleChange = vi.fn();
  render(
    <Toggle checked={false} label="Notifications" onChange={handleChange} />
  );
  const switchElement = screen.getByRole("switch");
  fireEvent.click(switchElement);
  expect(handleChange).toHaveBeenCalledWith(true);
});

test("supports disabled toggle switch", () => {
  const handleChange = vi.fn();
  render(
    <Toggle
      checked={false}
      disabled
      label="Notifications"
      onChange={handleChange}
    />
  );
  const switchElement = screen.getByRole("switch");
  expect(switchElement).toBeDisabled();
  fireEvent.click(switchElement);
  expect(handleChange).not.toHaveBeenCalled();
});

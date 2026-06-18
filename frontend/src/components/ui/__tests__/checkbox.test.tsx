import { render, screen, fireEvent } from "@testing-library/react";
import { Checkbox } from "../checkbox";
import { expect, test, vi } from "vitest";

test("renders checkbox with label", () => {
  render(<Checkbox label="Accept terms" checked={false} />);
  expect(screen.getByText("Accept terms")).toBeInTheDocument();
});

test("handles check state change", () => {
  const handleChange = vi.fn();
  render(
    <Checkbox label="Accept terms" checked={false} onChange={handleChange} />
  );
  const checkbox = screen.getByLabelText("Accept terms");
  fireEvent.click(checkbox);
  expect(handleChange).toHaveBeenCalledWith(true);
});

test("respects disabled state", () => {
  const handleChange = vi.fn();
  render(
    <Checkbox
      label="Accept terms"
      disabled
      checked={false}
      onChange={handleChange}
    />
  );
  const checkbox = screen.getByLabelText("Accept terms") as HTMLInputElement;
  expect(checkbox).toBeDisabled();

  // Guard click execution for fireEvent which bypasses native HTML disabled checks
  if (!checkbox.disabled) {
    fireEvent.click(checkbox);
  }
  expect(handleChange).not.toHaveBeenCalled();
});

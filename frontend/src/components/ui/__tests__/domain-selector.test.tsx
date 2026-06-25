import { render, screen, fireEvent } from "@testing-library/react";
import { DomainSelector } from "../domain-selector";
import { vi, test, expect } from "vitest";

test("renders two domain options", () => {
  render(<DomainSelector value="wetland" onChange={() => {}} />);
  expect(
    screen.getByLabelText("Switch to Wetland Monitoring")
  ).toBeInTheDocument();
  expect(
    screen.getByLabelText("Switch to Pollution Reports")
  ).toBeInTheDocument();
});

test("calls onChange with 'pollution' when Pollution Reports is clicked", () => {
  const onChange = vi.fn();
  render(<DomainSelector value="wetland" onChange={onChange} />);
  fireEvent.click(screen.getByLabelText("Switch to Pollution Reports"));
  expect(onChange).toHaveBeenCalledWith("pollution");
});

test("active tab has aria-pressed=true", () => {
  render(<DomainSelector value="pollution" onChange={() => {}} />);
  expect(screen.getByLabelText("Switch to Pollution Reports")).toHaveAttribute(
    "aria-pressed",
    "true"
  );
  expect(screen.getByLabelText("Switch to Wetland Monitoring")).toHaveAttribute(
    "aria-pressed",
    "false"
  );
});

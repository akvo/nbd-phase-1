import { render, screen } from "@testing-library/react";
import { SiteHeader } from "../site-header";
import { expect, test } from "vitest";

test("renders site header logo and sign in buttons", () => {
  render(<SiteHeader showActions={true} />);
  expect(screen.getByText("Logoipsum")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /log in/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /sign up/i })).toBeInTheDocument();
});

test("renders toggle menu when actions are disabled", () => {
  render(<SiteHeader showActions={false} />);
  expect(
    screen.getByRole("button", { name: /toggle menu/i })
  ).toBeInTheDocument();
});

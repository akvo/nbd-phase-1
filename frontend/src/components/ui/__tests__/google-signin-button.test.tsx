import { render, screen, fireEvent } from "@testing-library/react";
import { GoogleSignInButton } from "../google-signin-button";
import { expect, test, vi } from "vitest";

test("renders sign in button and triggers callback", () => {
  const handleClick = vi.fn();
  render(<GoogleSignInButton onClick={handleClick} />);

  const button = screen.getByRole("button");
  expect(button).toBeInTheDocument();
  expect(screen.getAllByText("Sign in with Google")[0]).toBeInTheDocument();

  fireEvent.click(button);
  expect(handleClick).toHaveBeenCalled();
});

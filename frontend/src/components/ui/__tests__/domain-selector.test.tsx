import { render, screen, fireEvent } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { DomainSelector } from "../domain-selector";
import { vi, test, expect } from "vitest";
import messages from "../../../../messages/en.json";

const renderWithIntl = (ui: React.ReactElement) => {
  return render(
    <NextIntlClientProvider messages={messages} locale="en">
      {ui}
    </NextIntlClientProvider>
  );
};

test("renders two domain options", () => {
  renderWithIntl(<DomainSelector value="wetland" onChange={() => {}} />);
  expect(
    screen.getByLabelText(
      messages.landing.switchDomain.replace(
        "{domain}",
        messages.landing.wetlandMonitoring
      )
    )
  ).toBeInTheDocument();
  expect(
    screen.getByLabelText(
      messages.landing.switchDomain.replace(
        "{domain}",
        messages.landing.pollutionReports
      )
    )
  ).toBeInTheDocument();
});

test("calls onChange with 'pollution' when Pollution Reports is clicked", () => {
  const onChange = vi.fn();
  renderWithIntl(<DomainSelector value="wetland" onChange={onChange} />);
  fireEvent.click(
    screen.getByLabelText(
      messages.landing.switchDomain.replace(
        "{domain}",
        messages.landing.pollutionReports
      )
    )
  );
  expect(onChange).toHaveBeenCalledWith("pollution");
});

test("active tab has aria-pressed=true", () => {
  renderWithIntl(<DomainSelector value="pollution" onChange={() => {}} />);
  expect(
    screen.getByLabelText(
      messages.landing.switchDomain.replace(
        "{domain}",
        messages.landing.pollutionReports
      )
    )
  ).toHaveAttribute("aria-pressed", "true");
  expect(
    screen.getByLabelText(
      messages.landing.switchDomain.replace(
        "{domain}",
        messages.landing.wetlandMonitoring
      )
    )
  ).toHaveAttribute("aria-pressed", "false");
});

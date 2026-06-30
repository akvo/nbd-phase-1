import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { DateRangePicker } from "../date-range-picker";
import messages from "../../../../messages/en.json";
import { expect, test, vi } from "vitest";

test("opens date range picker popover and applies preset", () => {
  const onStartChange = vi.fn();
  const onEndChange = vi.fn();

  render(
    <NextIntlClientProvider messages={messages} locale="en">
      <DateRangePicker
        showLabel={true}
        startDate=""
        endDate=""
        onStartDateChange={onStartChange}
        onEndDateChange={onEndChange}
      />
    </NextIntlClientProvider>
  );

  // Open popover
  const trigger = screen.getByTestId("date-range-picker-trigger");
  fireEvent.click(trigger);

  // Presets should be visible
  const presetBtn = screen.getByText("Last 7 Days");
  expect(presetBtn).toBeInTheDocument();
  fireEvent.click(presetBtn);

  // Check callback invocation
  expect(onStartChange).toHaveBeenCalled();
  expect(onEndChange).toHaveBeenCalled();
});

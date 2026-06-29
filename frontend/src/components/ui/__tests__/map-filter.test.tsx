import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { MapFilter } from "../map-filter";
import messages from "../../../../messages/en.json";
import { expect, test, vi } from "vitest";

const mockBasins = [{ value: "MARA", label: "Mara River Basin" }];
const mockWetlands = [{ value: "W1", label: "Mara Wetland" }];

test("renders MapFilter for Wetland and responds to inputs", () => {
  const onBasinChange = vi.fn();
  const onWetlandChange = vi.fn();
  const onHealthFilterChange = vi.fn();

  render(
    <NextIntlClientProvider messages={messages} locale="en">
      <MapFilter
        domain="wetland"
        basins={mockBasins}
        selectedBasin="MARA"
        onBasinChange={onBasinChange}
        wetlandOptions={mockWetlands}
        selectedWetland=""
        onWetlandChange={onWetlandChange}
        selectedHealthFilter="All"
        onHealthFilterChange={onHealthFilterChange}
        selectedIncidentTypes={[]}
        onIncidentTypesChange={vi.fn()}
        selectedDateFrom=""
        onDateFromChange={vi.fn()}
        selectedDateTo=""
        onDateToChange={vi.fn()}
        onClearFilters={vi.fn()}
      />
    </NextIntlClientProvider>
  );

  // Expect Basin selector label
  // expect(screen.getByText("Basin / Region")).toBeInTheDocument();
  // Expect Wetland selector label
  // expect(screen.getByText("Wetland")).toBeInTheDocument();

  // Change health filter
  const critBtn = screen.getByRole("button", { name: "Critical" });
  fireEvent.click(critBtn);
  expect(onHealthFilterChange).toHaveBeenCalledWith("Critical");
});

test("renders MapFilter for Pollution domain", () => {
  const onIncidentTypeChange = vi.fn();
  const onDateFromChange = vi.fn();

  render(
    <NextIntlClientProvider messages={messages} locale="en">
      <MapFilter
        domain="pollution"
        basins={mockBasins}
        selectedBasin="MARA"
        onBasinChange={vi.fn()}
        wetlandOptions={mockWetlands}
        selectedWetland=""
        onWetlandChange={vi.fn()}
        selectedHealthFilter="All"
        onHealthFilterChange={vi.fn()}
        selectedIncidentTypes={[]}
        onIncidentTypesChange={onIncidentTypeChange}
        selectedDateFrom="2026-06-01"
        onDateFromChange={onDateFromChange}
        selectedDateTo=""
        onDateToChange={vi.fn()}
        onClearFilters={vi.fn()}
      />
    </NextIntlClientProvider>
  );

  // Health filters should not render since domain is pollution
  expect(
    screen.queryByRole("button", { name: "Healthy" })
  ).not.toBeInTheDocument();

  // Click date picker trigger to open inputs
  const triggerBtn = screen.getByTestId("date-range-picker-trigger");
  fireEvent.click(triggerBtn);

  // Date input should be present inside the popover
  const dateFromInput = screen.getByTestId("date-picker-start-input");
  expect(dateFromInput).toBeInTheDocument();
  expect(dateFromInput).toHaveValue("2026-06-01");

  // Change input and click apply
  fireEvent.change(dateFromInput, { target: { value: "2026-06-15" } });
  const applyBtn = screen.getByTestId("date-range-picker-apply");
  fireEvent.click(applyBtn);

  expect(onDateFromChange).toHaveBeenCalledWith("2026-06-15");
});

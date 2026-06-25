import { render, screen, fireEvent } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { IncidentDrawer } from "../incident-drawer";
import { vi, test, expect } from "vitest";
import { IncidentSummary } from "@/lib/api";
import messages from "../../../../messages/en.json";

const mockIncident: IncidentSummary = {
  id: 42,
  form_name: "Pollution Reporting Form",
  status: "APPROVED",
  created_at: "2026-06-25T12:00:00Z",
  name: "wa-+256****321",
  answers: [
    { question_id: 2, name: "incident_type", value: "Fish kill", options: [3] },
    {
      question_id: 3,
      name: "incident_description",
      value: "Lots of dead fish floating.",
    },
    {
      question_id: 4,
      name: "photo",
      value: "photo.jpg",
      read_url: "/api/v1/storage/files/media/whatsapp/photo.jpg",
    },
  ],
  geo: { type: "Point", coordinates: [32.5, 0.3] as [number, number] },
};

const renderWithIntl = (ui: React.ReactElement) => {
  return render(
    <NextIntlClientProvider messages={messages} locale="en">
      {ui}
    </NextIntlClientProvider>
  );
};

test("renders null when no incident is passed", () => {
  const { container } = renderWithIntl(
    <IncidentDrawer incident={null} onClose={() => {}} />
  );
  expect(container.firstChild).toBeNull();
});

test("renders incident details correctly", () => {
  renderWithIntl(
    <IncidentDrawer
      incident={mockIncident}
      basinName="Victoria Basin"
      onClose={() => {}}
    />
  );
  expect(
    screen.getByRole("heading", { name: "Fish kill" })
  ).toBeInTheDocument();
  expect(
    screen.getByText(messages.incidentDrawer.critical)
  ).toBeInTheDocument();
  expect(screen.getByText("Victoria Basin")).toBeInTheDocument();
  expect(
    screen.getAllByText("Lots of dead fish floating.")[0]
  ).toBeInTheDocument();
  expect(screen.getByText("wa-+256****321")).toBeInTheDocument();
});

test("renders incident image correctly when read_url is provided", () => {
  renderWithIntl(<IncidentDrawer incident={mockIncident} onClose={() => {}} />);
  const img = screen.getByRole("img");
  expect(img).toHaveAttribute(
    "src",
    "/api/v1/storage/files/media/whatsapp/photo.jpg"
  );
});

test("calls onClose when close button is clicked", () => {
  const onClose = vi.fn();
  renderWithIntl(<IncidentDrawer incident={mockIncident} onClose={onClose} />);
  fireEvent.click(screen.getByText("✕"));
  expect(onClose).toHaveBeenCalled();
});

test("renders image from media_attachment when read_url is provided", () => {
  const incidentWithMediaAttachment: IncidentSummary = {
    ...mockIncident,
    answers: [
      {
        question_id: 2,
        name: "incident_type",
        value: "Fish kill",
        options: [3],
      },
      {
        question_id: 3,
        name: "media_attachment",
        value: undefined,
        options: ["media/whatsapp/5d67145a-9f94-4997-a9a6-8b5bcd8bca23.jpeg"],
        read_url:
          "/api/v1/storage/files/media/whatsapp/5d67145a-9f94-4997-a9a6-8b5bcd8bca23.jpeg",
      },
    ],
  };
  renderWithIntl(
    <IncidentDrawer incident={incidentWithMediaAttachment} onClose={() => {}} />
  );
  const img = screen.getByRole("img");
  expect(img).toHaveAttribute(
    "src",
    "/api/v1/storage/files/media/whatsapp/5d67145a-9f94-4997-a9a6-8b5bcd8bca23.jpeg"
  );
});

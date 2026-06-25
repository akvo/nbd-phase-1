import { render, screen, fireEvent } from "@testing-library/react";
import { IncidentDrawer } from "../incident-drawer";
import { vi, test, expect } from "vitest";
import { IncidentSummary } from "@/lib/api";

const mockIncident: IncidentSummary = {
  id: 42,
  form_name: "Pollution Reporting Form",
  status: "APPROVED",
  submitted_at: "2026-06-25T12:00:00Z",
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

test("renders null when no incident is passed", () => {
  const { container } = render(
    <IncidentDrawer incident={null} onClose={() => {}} />
  );
  expect(container.firstChild).toBeNull();
});

test("renders incident details correctly", () => {
  render(
    <IncidentDrawer
      incident={mockIncident}
      basinName="Victoria Basin"
      onClose={() => {}}
    />
  );
  expect(
    screen.getByRole("heading", { name: "Fish kill" })
  ).toBeInTheDocument();
  expect(screen.getByText("Critical")).toBeInTheDocument();
  expect(screen.getByText("Victoria Basin")).toBeInTheDocument();
  expect(
    screen.getAllByText("Lots of dead fish floating.")[0]
  ).toBeInTheDocument();
  expect(screen.getByText("wa-+256****321")).toBeInTheDocument();
});

test("renders incident image correctly when read_url is provided", () => {
  render(<IncidentDrawer incident={mockIncident} onClose={() => {}} />);
  const img = screen.getByRole("img");
  expect(img).toHaveAttribute(
    "src",
    "/api/v1/storage/files/media/whatsapp/photo.jpg"
  );
});

test("calls onClose when close button is clicked", () => {
  const onClose = vi.fn();
  render(<IncidentDrawer incident={mockIncident} onClose={onClose} />);
  fireEvent.click(screen.getByText("✕"));
  expect(onClose).toHaveBeenCalled();
});

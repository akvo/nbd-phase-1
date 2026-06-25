# LLD — Domain Selector & Differentiated Dashboard View

* **Stage 3 of 3 — Documentation Hierarchy**
* **Owner**: Winston (Architect) / Amelia (Developer)
* **Initiative/Epic**: Domain-Differentiated Portal Dashboard
* **Related PRD**: [domain_selector_dashboard_prd.md](../prd/domain_selector_dashboard_prd.md)
* **Related SDD**: [Final_SDD.md §4.5](../Final_SDD.md#45-wetland-data-portal)
* **Status**: Approved

---

## 1. Type Definitions & Constants

### 1.1 Domain Type (`src/lib/api.ts`)

Add the following TypeScript types alongside the existing `GenericSamplingHistory` and `GenericScoreHistory` interfaces:

```typescript
// Domain literal type — matches backend form_name "Pollution Reporting Form" vs sites
export type MonitoringDomain = "wetland" | "pollution";

// Typed shape for a pollution incident fetched from /api/v1/submissions
export interface IncidentSummary {
  id: string | number;
  form_name: string;
  basin_id?: string;
  site_id?: string;
  geo?: { type: string; coordinates: [number, number] };
  submitted_at?: string;
  status: string;
  description?: string;
  answers: Array<{
    name?: string;
    question_id?: number;
    value?: string;
    options?: Array<string | number>;
    read_url?: string;
  }>;
}
```

> **Why not `any[]`?** TAC-1 requires `selectedDomain` and `dbIncidents` to carry typed contracts. This interface replaces the existing implicit `any[]` for `dbIncidents` in `page.tsx`.

---

## 2. New Component: `DomainSelector`

### 2.1 File: `frontend/src/components/ui/domain-selector.tsx`

**Props Interface:**
```typescript
interface DomainSelectorProps {
  value: MonitoringDomain;
  onChange: (domain: MonitoringDomain) => void;
}
```

**Visual Design:**
- Full-width pill tab container matching the existing health filter toggle pattern (same `flex bg-slate-100 p-1 rounded-lg` shell).
- Two tabs:
  - `Wetland Monitoring` — icon: `🌿` or `Leaf` lucide icon
  - `Pollution Reports` — icon: `⚠️` or `TriangleAlert` lucide icon
- Active tab: `bg-white text-slate-800 shadow`
- Inactive tab: `text-slate-400 hover:text-slate-600`

**Full Component:**
```tsx
"use client";

import React from "react";
import { Leaf, TriangleAlert } from "lucide-react";
import { MonitoringDomain } from "@/lib/api";

interface DomainSelectorProps {
  value: MonitoringDomain;
  onChange: (domain: MonitoringDomain) => void;
}

const DOMAINS: { value: MonitoringDomain; label: string; Icon: React.ElementType }[] = [
  { value: "wetland", label: "Wetland Monitoring", Icon: Leaf },
  { value: "pollution", label: "Pollution Reports", Icon: TriangleAlert },
];

export function DomainSelector({ value, onChange }: DomainSelectorProps) {
  return (
    <div className="flex bg-slate-100 p-1 rounded-lg w-full text-xs font-semibold">
      {DOMAINS.map(({ value: domain, label, Icon }) => (
        <button
          key={domain}
          id={`domain-selector-${domain}`}
          onClick={() => onChange(domain)}
          className={`flex-1 py-1.5 rounded-md text-center transition-all flex items-center justify-center gap-1.5 ${
            value === domain
              ? "bg-white text-slate-800 shadow"
              : "text-slate-400 hover:text-slate-600"
          }`}
          aria-pressed={value === domain}
          aria-label={`Switch to ${label}`}
        >
          <Icon className="w-3 h-3 shrink-0" />
          <span className="truncate">{label}</span>
        </button>
      ))}
    </div>
  );
}
```

**Unit Test spec** (`src/components/ui/__tests__/domain-selector.test.tsx`):
```typescript
import { render, screen, fireEvent } from "@testing-library/react";
import { DomainSelector } from "../domain-selector";

test("renders two domain options", () => {
  render(<DomainSelector value="wetland" onChange={() => {}} />);
  expect(screen.getByLabelText("Switch to Wetland Monitoring")).toBeInTheDocument();
  expect(screen.getByLabelText("Switch to Pollution Reports")).toBeInTheDocument();
});

test("calls onChange with 'pollution' when Pollution Reports is clicked", () => {
  const onChange = vi.fn();
  render(<DomainSelector value="wetland" onChange={onChange} />);
  fireEvent.click(screen.getByLabelText("Switch to Pollution Reports"));
  expect(onChange).toHaveBeenCalledWith("pollution");
});

test("active tab has aria-pressed=true", () => {
  render(<DomainSelector value="pollution" onChange={() => {}} />);
  expect(screen.getByLabelText("Switch to Pollution Reports")).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByLabelText("Switch to Wetland Monitoring")).toHaveAttribute("aria-pressed", "false");
});
```

---

## 3. New Component: `IncidentCard`

### 3.1 File: `frontend/src/components/ui/incident-card.tsx`

**Props Interface:**
```typescript
interface IncidentCardProps {
  incidentTypeName: string;       // e.g. "Fish kill", "Unusual water colour"
  severity: "Critical" | "Elevated" | "Moderate";
  dateReported: string;           // ISO string, formatted to locale date
  description: string;            // truncated to 2 lines via CSS
  basinName?: string;             // optional basin label
}
```

**Severity → colour mapping:**
| Severity | Background | Text | Border |
|---|---|---|---|
| `Critical` | `bg-red-50` | `text-red-700` | `border-red-200` |
| `Elevated` | `bg-amber-50` | `text-amber-700` | `border-amber-200` |
| `Moderate` | `bg-slate-50` | `text-slate-600` | `border-slate-200` |

**Full Component:**
```tsx
"use client";

import React from "react";
import { Card } from "@/components/ui/card";

type Severity = "Critical" | "Elevated" | "Moderate";

interface IncidentCardProps {
  incidentTypeName: string;
  severity: Severity;
  dateReported: string;
  description: string;
  basinName?: string;
}

const SEVERITY_STYLES: Record<Severity, string> = {
  Critical: "bg-red-50 text-red-700 border-red-200",
  Elevated: "bg-amber-50 text-amber-700 border-amber-200",
  Moderate: "bg-slate-50 text-slate-600 border-slate-200",
};

export function IncidentCard({
  incidentTypeName,
  severity,
  dateReported,
  description,
  basinName,
}: IncidentCardProps) {
  const formattedDate = dateReported
    ? new Date(dateReported).toLocaleDateString()
    : "Unknown date";

  return (
    <Card className="p-4 border border-slate-100 hover:border-red-100 hover:shadow-md transition-all flex flex-col gap-2 relative overflow-hidden group cursor-default">
      {/* Header row */}
      <div className="flex justify-between items-start gap-2">
        <h4 className="font-bold text-slate-800 text-sm group-hover:text-red-600 transition-colors leading-tight">
          {incidentTypeName}
        </h4>
        <span
          className={`text-[10px] font-bold tracking-wide uppercase px-2 py-0.5 rounded-md border shrink-0 ${SEVERITY_STYLES[severity]}`}
        >
          {severity}
        </span>
      </div>

      {/* Description — clamped to 2 lines */}
      <p className="text-xs text-slate-500 line-clamp-2 leading-relaxed">
        {description || "No details recorded."}
      </p>

      {/* Footer row */}
      <div className="flex flex-wrap gap-1.5 mt-1">
        <span className="text-[10px] font-bold tracking-wide px-2 py-0.5 rounded-md bg-slate-50 text-slate-500 border border-slate-200 shadow-sm">
          {formattedDate}
        </span>
        {basinName && (
          <span className="text-[10px] font-bold tracking-wide px-2 py-0.5 rounded-md bg-blue-50 text-blue-600 border border-blue-100 shadow-sm">
            {basinName}
          </span>
        )}
      </div>
    </Card>
  );
}
```

**Unit Test spec** (`src/components/ui/__tests__/incident-card.test.tsx`):
```typescript
import { render, screen } from "@testing-library/react";
import { IncidentCard } from "../incident-card";

const base = {
  incidentTypeName: "Fish kill",
  severity: "Critical" as const,
  dateReported: "2026-06-01T10:00:00Z",
  description: "Large-scale fish mortality observed near the river mouth.",
  basinName: "Mara Basin",
};

test("renders incident type name", () => {
  render(<IncidentCard {...base} />);
  expect(screen.getByText("Fish kill")).toBeInTheDocument();
});

test("renders severity badge with correct label", () => {
  render(<IncidentCard {...base} />);
  expect(screen.getByText("Critical")).toBeInTheDocument();
});

test("renders basin name chip when provided", () => {
  render(<IncidentCard {...base} />);
  expect(screen.getByText("Mara Basin")).toBeInTheDocument();
});

test("gracefully handles missing description", () => {
  render(<IncidentCard {...base} description="" />);
  expect(screen.getByText("No details recorded.")).toBeInTheDocument();
});
```

test("gracefully handles missing description", () => {
  render(<IncidentCard {...base} description="" />);
  expect(screen.getByText("No details recorded.")).toBeInTheDocument();
});
```

---

## 3.2 New Component: `IncidentDrawer`

### 3.2.1 File: `frontend/src/components/ui/incident-drawer.tsx`

**Props Interface:**
```typescript
import { IncidentSummary } from "@/lib/api";

interface IncidentDrawerProps {
  incident: IncidentSummary | null;
  basinName?: string;
  onClose: () => void;
}
```

**Visual Design:**
- Right-hand slide-in panel matching `SiteDrawer` layout (`fixed inset-y-0 right-0 z-50 w-full max-w-md bg-white shadow-2xl flex flex-col h-full border-l border-slate-200 animate-slide-in`).
- Close button (`✕`) at the top right.
- Header showing `Incident Type`, `Severity Badge`, and `Basin/Location`.
- Body with scrolling container containing:
  - **Details list**: Submitter ID (masked), Date Reported, Coordinates.
  - **Full Description / Details**.
  - **Photo Gallery**: Finds any answers with `read_url` and renders a clean photo grid using native `<img src={ans.read_url} />` with smooth border, rounded corners, shadow, and lazy-loading.
  - **Questionnaire breakdown**: Table or list of all questions and answers (excluding metadata and empty/unanswered questions).

**Full Component:**

```typescript
"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { IncidentSummary } from "@/lib/api";
import { AlertTriangle, Calendar, MapPin, User, Image as ImageIcon } from "lucide-react";

type Severity = "Critical" | "Elevated" | "Moderate";

interface IncidentDrawerProps {
  incident: IncidentSummary | null;
  basinName?: string;
  onClose: () => void;
}

const SEVERITY_STYLES: Record<Severity, { badge: string; text: string; circle: string }> = {
  Critical: {
    badge: "bg-red-50 text-red-700 border-red-200",
    text: "text-red-600",
    circle: "bg-red-500 text-red-50",
  },
  Elevated: {
    badge: "bg-amber-50 text-amber-700 border-amber-200",
    text: "text-amber-600",
    circle: "bg-amber-500 text-amber-50",
  },
  Moderate: {
    badge: "bg-slate-50 text-slate-600 border-slate-200",
    text: "text-slate-500",
    circle: "bg-slate-500 text-slate-50",
  },
};

export function IncidentDrawer({ incident, basinName, onClose }: IncidentDrawerProps) {
  if (!incident) return null;

  // Resolve severity
  const qIncidentAns = incident.answers?.find(
    (a) => a.name === "incident_type" || a.question_id === 2
  );
  const optionVal = qIncidentAns?.options?.[0];
  let severity: Severity = "Moderate";
  if (optionVal === 3 || optionVal === "3") severity = "Critical";
  else if ([1, "1", 2, "2"].includes(optionVal)) severity = "Elevated";

  const styles = SEVERITY_STYLES[severity];
  const incidentTypeName = qIncidentAns?.value || "Pollution Report";
  const formattedDate = incident.submitted_at
    ? new Date(incident.submitted_at).toLocaleString()
    : "Unknown date";

  const qDetailAns = incident.answers?.find(
    (a) =>
      a.name === "incident_description" ||
      a.name === "details" ||
      a.question_id === 3
  );
  const description = qDetailAns?.value || incident.description || "No details recorded.";

  // Find image answers
  const imageAnswers = incident.answers?.filter(
    (a) => a.read_url && a.read_url.trim() !== ""
  ) || [];

  const coords = incident.geo?.coordinates;

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-white shadow-2xl flex flex-col h-full border-l border-slate-200 animate-slide-in">
      {/* Drawer Header */}
      <div className="p-6 border-b border-slate-200 flex items-center justify-between">
        <div className="flex-1 min-w-0 pr-4">
          <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider flex items-center gap-1">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
            Pollution Incident
          </span>
          <h2 className="text-lg font-bold text-slate-800 truncate mt-0.5">
            {incidentTypeName}
          </h2>
          <p className="text-xs text-slate-500 font-mono mt-0.5">
            ID: {incident.id}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`text-xs font-bold tracking-wide uppercase px-2.5 py-1 rounded-md border shrink-0 ${styles.badge}`}
          >
            {severity}
          </span>
          <Button
            variant="ghost"
            onClick={onClose}
            className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-400 hover:text-slate-600 transition-colors"
          >
            ✕
          </Button>
        </div>
      </div>

      {/* Drawer Body (Scrollable) */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Metadata section */}
        <div className="bg-slate-50 rounded-xl p-4 space-y-3 border border-slate-100 text-xs text-slate-600">
          <div className="flex items-center gap-2.5">
            <Calendar className="w-4 h-4 text-slate-400 shrink-0" />
            <div>
              <span className="font-semibold block text-slate-500">Reported At</span>
              <span>{formattedDate}</span>
            </div>
          </div>
          <div className="flex items-center gap-2.5">
            <User className="w-4 h-4 text-slate-400 shrink-0" />
            <div>
              <span className="font-semibold block text-slate-500">Reporter</span>
              <span>{incident.name || "Anonymous citizen"}</span>
            </div>
          </div>
          {basinName && (
            <div className="flex items-center gap-2.5">
              <MapPin className="w-4 h-4 text-slate-400 shrink-0" />
              <div>
                <span className="font-semibold block text-slate-500">River Basin</span>
                <span>{basinName}</span>
              </div>
            </div>
          )}
          {coords && (
            <div className="flex items-center gap-2.5">
              <MapPin className="w-4 h-4 text-slate-400 shrink-0" />
              <div>
                <span className="font-semibold block text-slate-500">GPS Coordinates</span>
                <span className="font-mono">
                  {coords[1].toFixed(5)}, {coords[0].toFixed(5)}
                </span>
              </div>
            </div>
            {/* Description section */}
        <div className="space-y-2">
          <h3 className="font-bold text-slate-800 uppercase tracking-wider text-xs">
            Description
          </h3>
          <p className="text-sm text-slate-600 bg-slate-50/50 p-4 rounded-xl border border-slate-100 leading-relaxed whitespace-pre-line">
            {description}
          </p>
        </div>

        {/* Photos section */}
        {imageAnswers.length > 0 && (
          <div className="space-y-2">
            <h3 className="font-bold text-slate-800 uppercase tracking-wider text-xs flex items-center gap-1.5">
              <ImageIcon className="w-4 h-4 text-slate-500" />
              Attached Media ({imageAnswers.length})
            </h3>
            <div className="grid grid-cols-1 gap-4">
              {imageAnswers.map((img, i) => (
                <div
                  key={img.question_id ?? i}
                  className="relative rounded-xl overflow-hidden border border-slate-200 shadow-sm bg-slate-100 aspect-video group"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={img.read_url}
                    alt={`Incident report photo ${i + 1}`}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    loading="lazy"
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Full answers list */}
        {incident.answers && incident.answers.length > 0 && (
          <div className="space-y-2">
            <h3 className="font-bold text-slate-800 uppercase tracking-wider text-xs">
              Questionnaire Answers
            </h3> Answers
            </h3>
            <div className="border border-slate-100 rounded-xl overflow-hidden divide-y divide-slate-100 text-xs">
              {incident.answers
                .filter((ans) => ans.value !== undefined && ans.value !== null && ans.value !== "")
                .map((ans, idx) => (
                  <div key={ans.question_id ?? idx} className="p-3 bg-white flex justify-between gap-4">
                    <span className="text-slate-500 font-medium shrink-0">{ans.name || `Question ${ans.question_id}`}</span>
                    <span className="text-slate-800 text-right">{String(ans.value)}</span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
```

### 3.3 Unit Test spec (`src/components/ui/__tests__/incident-drawer.test.tsx`)

```typescript
import { render, screen, fireEvent } from "@testing-library/react";
import { IncidentDrawer } from "../incident-drawer";

const mockIncident = {
  id: 42,
  form_name: "Pollution Reporting Form",
  status: "APPROVED",
  submitted_at: "2026-06-25T12:00:00Z",
  name: "wa-+256****321",
  answers: [
    { question_id: 2, name: "incident_type", value: "Fish kill", options: [3] },
    { question_id: 3, name: "incident_description", value: "Lots of dead fish floating." },
    { question_id: 4, name: "photo", read_url: "/api/v1/storage/files/media/whatsapp/photo.jpg" }
  ],
  geo: { type: "Point", coordinates: [32.5, 0.3] }
};

test("renders null when no incident is passed", () => {
  const { container } = render(<IncidentDrawer incident={null} onClose={() => {}} />);
  expect(container.firstChild).toBeNull();
});

test("renders incident details correctly", () => {
  render(<IncidentDrawer incident={mockIncident} basinName="Victoria Basin" onClose={() => {}} />);
  expect(screen.getByText("Fish kill")).toBeInTheDocument();
  expect(screen.getByText("CRITICAL")).toBeInTheDocument();
  expect(screen.getByText("Victoria Basin")).toBeInTheDocument();
  expect(screen.getByText("Lots of dead fish floating.")).toBeInTheDocument();
  expect(screen.getByText("wa-+256****321")).toBeInTheDocument();
});

test("renders incident image correctly when read_url is provided", () => {
  render(<IncidentDrawer incident={mockIncident} onClose={() => {}} />);
  const img = screen.getByRole("img");
  expect(img).toHaveAttribute("src", "/api/v1/storage/files/media/whatsapp/photo.jpg");
});

test("calls onClose when close button is clicked", () => {
  const onClose = vi.fn();
  render(<IncidentDrawer incident={mockIncident} onClose={onClose} />);
  fireEvent.click(screen.getByText("✕"));
  expect(onClose).toHaveBeenCalled();
});
```

---

## 4. Modified: `page.tsx` — Domain State & Wiring

### 4.1 New State Variable

```typescript
// Add alongside existing useState declarations (line ~158)
const [selectedDomain, setSelectedDomain] = useState<MonitoringDomain>("wetland");
```

### 4.2 Domain Switch Handler

```typescript
const handleDomainChange = (domain: MonitoringDomain) => {
  setSelectedDomain(domain);
  // UAC-6: close SiteDrawer when switching to pollution domain
  if (domain === "pollution") {
    setSelectedSite(null);
  }
};
```

### 4.3 Wrap `mapMarkers` in `useMemo` (TAC-2)

Replace the existing direct `mapMarkers` array computation with a memoized version:

```typescript
const mapMarkers = useMemo(() => {
  if (selectedDomain === "wetland") {
    return filteredSites.map((site) => {
      const coords = site.geom?.coordinates;
      const position: [number, number] = coords ? [coords[1], coords[0]] : [0, 0];
      const ikAdjustedScore = site.status?.ik_adjusted_score ?? 0.5;
      return {
        position,
        popupText: `${site.name} (${site.status?.health_class || "N/A"})`,
        type: "site" as const,
        status: site.status?.health_class,
        code: site.code,
        name: site.name,
        score: Math.round(ikAdjustedScore * 100),
        description: site.description || "No signal details recorded.",
      };
    });
  }

  // Pollution domain
  return filteredIncidents.map((incident) => {
    const coords = incident.geo?.coordinates;
    const position: [number, number] = coords ? [coords[1], coords[0]] : [0, 0];
    const qIncidentAns = incident.answers?.find(
      (a: any) => a.name === "incident_type" || a.question_id === 2
    );
    const optionVal = qIncidentAns?.options?.[0];
    let severity = "Moderate";
    if (optionVal === 3 || optionVal === "3") severity = "Critical";
    else if ([1, "1", 2, "2"].includes(optionVal)) severity = "Elevated";

    const incidentTypeName = qIncidentAns?.value || "Pollution Report";
    const formattedDate = incident.submitted_at
      ? new Date(incident.submitted_at).toLocaleDateString()
      : "Unknown date";

    return {
      position,
      popupText: `Incident: ${incidentTypeName} (${severity})`,
      type: "incident" as const,
      status: severity,
      name: incidentTypeName,
      description: incident.description || "No details recorded.",
      additionalInfo: `Reported on: ${formattedDate}`,
    };
  });
}, [selectedDomain, filteredSites, filteredIncidents]);
```

### 4.4 Filter Toggles — Domain-Aware Labels

```typescript
// Replace static array ["All", "Critical", "At risk", "Healthy"] with:
const filterOptions =
  selectedDomain === "wetland"
    ? ["All", "Critical", "At risk", "Healthy"]
    : ["All", "Critical", "Elevated"];
```

Apply in JSX:
```tsx
{filterOptions.map((filter) => (
  <button
    key={filter}
    onClick={() => setSelectedHealthFilter(filter)}
    className={`flex-1 py-1.5 rounded-md text-center transition-all ${
      selectedHealthFilter === filter
        ? "bg-white text-slate-800 shadow"
        : "text-slate-400 hover:text-slate-600"
    }`}
  >
    {filter}
  </button>
))}
```

> **Note**: When domain changes, reset `selectedHealthFilter` to `"All"` to prevent an invalid filter state (e.g., "At risk" in pollution domain):
```typescript
const handleDomainChange = (domain: MonitoringDomain) => {
  setSelectedDomain(domain);
  setSelectedHealthFilter("All"); // reset filter on domain switch
  if (domain === "pollution") setSelectedSite(null);
};
```

### 4.5 List Section Header

```tsx
<span className="text-slate-500 font-bold text-xs uppercase tracking-wider">
  {selectedDomain === "wetland"
    ? `Monitoring Sites (${filteredSites.length})`
    : `Pollution Incidents (${filteredIncidents.length})`}
</span>
```

### 4.6 Conditional List Rendering

Replace the existing site card `filteredSites.map(...)` block with a domain-branched render:

```tsx
{selectedDomain === "wetland" ? (
  // --- EXISTING site cards (no changes to this block) ---
  filteredSites.length > 0 ? (
    filteredSites.map((site) => { /* ...existing site card JSX... */ })
  ) : (
    <div className="text-sm text-slate-400 italic py-8 text-center">
      No active stations matching filters.
    </div>
  )
) : (
  // --- NEW pollution incident cards ---
  filteredIncidents.length > 0 ? (
    filteredIncidents.map((incident, idx) => {
      const qIncidentAns = incident.answers?.find(
        (a: any) => a.name === "incident_type" || a.question_id === 2
      );
      const optionVal = qIncidentAns?.options?.[0];
      let severity: "Critical" | "Elevated" | "Moderate" = "Moderate";
      if (optionVal === 3 || optionVal === "3") severity = "Critical";
      else if ([1, "1", 2, "2"].includes(optionVal)) severity = "Elevated";

      const qDetailAns = incident.answers?.find(
        (a: any) => a.name === "incident_description" || a.question_id === 3
      );
      const activeBasin = basins.find((b) => b.id === incident.basin_id);

      return (
        <IncidentCard
          key={incident.id ?? idx}
          incidentTypeName={qIncidentAns?.value || "Pollution Report"}
          severity={severity}
          dateReported={incident.submitted_at || ""}
          description={qDetailAns?.value || incident.description || ""}
          basinName={activeBasin?.name}
        />
      );
    })
  ) : (
    <div className="text-sm text-slate-400 italic py-8 text-center">
      No pollution incidents reported in this basin.
    </div>
  )
)}
```

### 4.7 `DomainSelector` Placement in JSX

Insert immediately after the opening `<div className="p-4 border-b ...">` container, **above** the basin dropdown:

```tsx
{/* Domain selector — above basin dropdown */}
<DomainSelector value={selectedDomain} onChange={handleDomainChange} />

{/* Basin selector */}
{SHOW_BASIN_SELECTOR && (
  <Dropdown ... />
)}
```

### 4.8 Import Additions for `page.tsx`

```typescript
import { MonitoringDomain } from "@/lib/api";
import { DomainSelector } from "@/components/ui/domain-selector";
import { IncidentCard } from "@/components/ui/incident-card";
import { useMemo } from "react"; // add to existing React import
```

---

## 5. Pollution Filter Logic for Incident List

The existing `filteredIncidents` computation already resolves severity from `incident.answers`. The domain-aware filter toggle ("All / Critical / Elevated") must feed into this computation.

**Current filter logic in `filteredIncidents`** (lines ~258-293 of `page.tsx`) already maps `selectedHealthFilter` to severity. The only change needed is ensuring the `"At risk"` and `"Healthy"` branches do **not** fire in the Pollution domain (handled automatically since those options are not rendered as tabs when `selectedDomain === "pollution"`).

No logic change is needed to `filteredIncidents` itself — the tab rendering change (section 4.4) prevents stale filter values.

---

## 6. Verification Plan

### 6.1 Unit Tests

| Test File | Tests Added |
|---|---|
| `src/components/ui/__tests__/domain-selector.test.tsx` | Renders 2 tabs; calls `onChange`; `aria-pressed` correct |
| `src/components/ui/__tests__/incident-card.test.tsx` | Renders type, severity, date, basin; handles empty description |

Run with:
```bash
./dc.sh exec frontend yarn test
```

### 6.2 Manual QA Checklist

| # | Scenario | Expected |
|---|---|---|
| 1 | Open portal fresh | "Wetland Monitoring" tab active, site markers on map, site cards in list |
| 2 | Click "Pollution Reports" | Incident markers on map, incident cards in list, header says "Pollution Incidents (N)" |
| 3 | With SiteDrawer open, switch to Pollution | Drawer closes |
| 4 | Switch basin while on Pollution domain | Incident list updates, map updates |
| 5 | Use health filter "Critical" on Pollution domain | Only Critical incidents shown |
| 6 | Use health filter "Elevated" on Pollution domain | Only Elevated incidents shown |
| 7 | Switch back to Wetland | Site cards re-render, filter resets to "All" |
| 8 | Empty basin (no incidents) | "No pollution incidents reported in this basin." |
| 9 | Mobile viewport | DomainSelector fits within panel width, truncation is readable |

### 6.3 Regression Guard

Confirm zero regressions on the existing site-card feature:
```bash
./dc.sh exec frontend yarn test --run
```

Expected: all existing tests pass.

---

## 7. Accessibility Notes (WCAG 2.1 AA — SDD §4.5.1)

- `DomainSelector` buttons use `aria-pressed` to communicate toggle state to screen readers.
- `DomainSelector` buttons have descriptive `aria-label` (`"Switch to Wetland Monitoring"` / `"Switch to Pollution Reports"`).
- Severity badge in `IncidentCard` always includes a **text label** alongside any colour — never colour-only (satisfies WCAG SC 1.4.1).
- `IncidentCard` uses semantic `<h4>` for incident type name.

---

## 8. Forward-Compatibility Note

When the **Decoupled Analysis Layer** (`domain` column migration) is eventually shipped:
- The backend will supply `domain: "wetland" | "pollution"` on site and submission API responses.
- The `selectedDomain` state in `page.tsx` can optionally be initialised or cross-validated from the API `domain` field.
- `DomainSelector` and `IncidentCard` require **zero changes** — their props contracts are already domain-aware.
- The `MonitoringDomain` type in `api.ts` matches the planned backend `MonitoringDomain` enum (`WETLAND = "wetland"`, `POLLUTION = "pollution"`).

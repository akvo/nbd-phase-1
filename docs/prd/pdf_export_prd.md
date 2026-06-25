# PRD — [FE Mobile] Task 6: PDF Export Trigger

> **Stage 2 of 3 — Documentation Hierarchy**
> Owner: PM (John) + Design Lead (Sally) | Target Location: `docs/prd/pdf_export_prd.md`
> Status: `Proposed`

---

## 1. Overview & Goal

**Problem Statement**:
Users visiting site detail views (especially on mobile devices) do not have a direct way to export the displayed metrics, data cards, and tables for offline usage, printing, or sharing. To satisfy the offline reporting requirement, the Next.js frontend needs a robust trigger to export a clean, formatted PDF of the active site detail view.

**Core Metric**:
100% success rate in generating print-ready PDFs from the site detail drawer on both desktop and mobile web views, formatting all visible metrics, raw data tables, qualitative grids, and maps (if available).

---

## 2. User Stories & Flows

### User Persona
- **Field Officer / Citizen Reporter**: Needs to export and print a clear PDF report of a wetland site to share with local communities or archive offline, even on a basic mobile device.

### User Journey
1. **Trigger**: The user scrolls to the bottom of a site's detail drawer view.
2. **Action**: The user taps a prominent blue button labeled "Export detailed report (PDF)" (or localized Swahili equivalent if supported).
3. **Response**: The application triggers a native print layout that prompts the user to save as a PDF or send to a connected printer, styled to present exactly what is on the screen formatted as a clean report.

---

## 3. Requirements (Scope Guardrails)

### Must-Have
- **Export Button**: A styled CTA button (`Export detailed report (PDF)`) placed at the bottom of `SiteDrawer`.
- **Responsive Print Styling**: CSS print rules (`@media print`) that format the drawer contents to fill a standard A4/Letter page. It must hide interactive UI controls (e.g., Close `x` button, print trigger button itself) and ensure grid layouts/cards are flattened into a single-column layout on mobile.
- **Data Completeness**: The PDF must capture all currently rendered data cards (physico-chemical grid, raw data tables, qualitative grids).
- **Map Export**: Include the map in the PDF view (if rendered).

### Nice-to-Have
- Kiswahili translation for the button and print headers.
- Custom header showing the generation timestamp and source platform URL.

### Out of Scope
- Server-side PDF generation endpoints or external PDF-parsing APIs.
- Dedicated offline database caching of reports.

---

## 4. Technical Design

### Print Trigger Logic
When the export button is clicked, the application triggers:
```typescript
window.print();
```
To control the print output, specific CSS rules are defined inside the CSS layer to optimize page-breaks, hide utility elements, and style the drawer's content when printing:
```css
@media print {
  body * {
    visibility: hidden;
  }
  #site-drawer-print-area, #site-drawer-print-area * {
    visibility: visible;
  }
  #site-drawer-print-area {
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
  }
  .no-print {
    display: none !important;
  }
}
```

---

## 5. Acceptance Criteria

- **UAC 6.1 (Export Action)**: Given the user reaches the bottom of the detail view, when they tap the blue "Export detailed report (PDF)" button, then the Next.js application triggers the browser's print utility to save/print the page.
- **TAC 6.1 (Clean Print Styles)**: Ensure standard print dialog displays ONLY the contents of the detail view card deck. Close buttons, drawer backdrops, and navigation panels must be excluded.
- **TAC 6.2 (Mobile Respect)**: Print layout must automatically adapt to smaller device screens, reflowing flex and grid elements to fit the page without overflow.

---

## 6. Edge Cases & Errors

- **Maps Loading**: If the map is in a loading or unrendered state, the PDF will display the container with a loading placeholder or the fallback static thumbnail.
- **Multi-page Spans**: Page break rules (`page-break-inside: avoid;`) must be set on individual metric cards to prevent a card from splitting awkwardly across two pages.

---

## 7. Epic & Ballpark Estimation

- **Estimated Effort**: Simple to Medium.
- **Component Breakdown**:
  - Add CTA Button: 0.5h
  - Implement `@media print` CSS classes & wrap print wrapper in `SiteDrawer`: 1.5h
  - Verification & layout adjustments on Mobile Safari/Chrome: 1h
- **Ballpark Estimate**: ~3.0h

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Writing style

All prose written for this repository — SDD content, client responses, summaries — must follow `STYLE.md`. Read it before drafting or revising any document text. It is the binding voice for anything that will reach the client.

## What this repository is

This is a **documentation-only repository** for the Solution Design Document (SDD) of the NBD assignment *"Technical Support to Implement Citizen-Led Data Generation and Management Activities"*. The platform itself is built in a separate codebase; nothing in here is compiled, tested, or deployed. There are no build, lint, or test commands.

The deliverable is a single SDD that goes to the client (Nile Basin Discourse). Everything in this repo exists to produce, revise, or respond to comments on that document.

## Directory roles (and what is canonical)

The three top-level documentation directories are not interchangeable — they have different lifecycles:

- **`project-docs/`** — client-supplied inputs, immutable. The Revised Inception Report (April 2026) is the authoritative source for assignment scope, success indicators, citizen-reporting form (Annex 1), wetland health report card template (Annex 2), and pilot-site context. Treat anything here as read-only ground truth; cite from it, do not rewrite it.
- **`design-docs/`** — iterating drafts. `solution-design-technical.md` is the **canonical source of truth** for the SDD; `solution-design-technical.docx` is a manually exported snapshot. `solution-design-summary.md` is a partner/funder-facing summary derived from the technical doc. `ui-design-brief.md` is the brief handed to UI designers.
- **`final-docs/`** — versions sent to the client. The PDF here is the latest shipped revision. `client-it-comments-response.md` is the point-by-point response to NBD IT comments on that PDF, **structured as ready-to-paste content** for the next revision (v0.2) of `design-docs/solution-design-technical.md`.

The flow is: `project-docs/` (inputs) → `design-docs/solution-design-technical.md` (canonical markdown) → manual export to `.docx`/`.pdf` → `final-docs/` (delivered).

## When editing the SDD

- Edit `design-docs/solution-design-technical.md` as the primary source. Do **not** edit the `.docx` or `.pdf` files directly — they are exports.
- When the user references a client comment, check `final-docs/client-it-comments-response.md` first. Its "Ready-to-paste replacement" blocks are written in the SDD's voice and are the intended text for the next revision; lift them into `solution-design-technical.md` rather than re-drafting.
- The platform is positioned as a **general citizen-led data platform** whose first use case is wetland monitoring. The client IT team specifically pushed back on framing that confines the scope to wetland monitoring alone — preserve the generic-vs-wetland-specific distinction in any new content.
- Two transboundary pilots only: **Mara** (Kenya/Tanzania) and **Sio-Siteko** (Kenya/Uganda). Site IDs follow `NBD-MARA-001` / `NBD-SIO-001`. This identifier is the platform's interoperability key and shows up in every layer (KoboCollect form, GEE outputs, lab QA, portal API).

## Architectural decisions baked into the SDD

These are the load-bearing decisions in the document — keep them coherent across edits:

- **Three layers:** Data Collection (USSD / WhatsApp / KoboCollect) → Admin/Processing (Ingest · Clean · Approve · Score) → Wetland Data Portal (public).
- **Tech stack:** FastAPI (Python) backend, Next.js (portal + admin), PostgreSQL + PostGIS, Leaflet.js (maps), ECharts (charts), KoboToolbox (cloud, multi-tenant free tier — *not* self-hosted; the cloud version is the chosen path), Google Earth Engine for Sentinel 1&2 + CHIRPS, Africa's Talking for USSD + WhatsApp Business (Kenya-only channel, used by citizen reporters), Docker, GitHub + Actions.
- **Scoring pipeline:** parameter-group scores (physico-chemical, catchment, ecological) → composite average → **fuzzy-logic adjustment** using the FGD-derived indigenous-knowledge signal → health class A–E → traffic light Green/Yellow/Red → management actions surfaced on the portal.
- **Two roles in the admin layer:** Reviewer and Admin (strict superset). SSO via Google / Microsoft; no platform-managed passwords.
- **Open-source first**, except Africa's Talking (commercial SaaS) and GEE (non-commercial free tier — the commercial-use boundary is documented in §4.7.1 of the response doc).

## Do not fabricate implementation details

Stick to what is documented in `project-docs/`, `design-docs/solution-design-technical.md`, or what the user has explicitly stated. Do **not** invent:

- **Cadences and frequencies** — e.g., "every 10 minutes", "pulled hourly", "synced nightly" — unless the source doc gives a specific number. If a number is needed for an argument, propose it explicitly as a proposal, do not assert it as fact.
- **Protocols and transport details** — e.g., "OIDC · per login", "REST · per session", "HTTP webhook · per upload" — beyond what the SDD §6 integration table actually says.
- **Geographic scope** — channel scope is specific. USSD + WhatsApp via Africa's Talking is **Kenya only** (citizen reporter channel). KoboCollect via KoboToolbox is **Tanzania, Kenya, Uganda** (citizen scientist channel). Do not say "all three countries" for AT, do not say "Kenya only" for Kobo.
- **Version numbers, API surface details, code paths** that have not been chosen or named yet.
- **Cost figures, SLA percentages, retention windows** beyond those that are already in the SDD or the integration table.

When something genuinely needs a number to be useful (e.g., NFR targets), say so plainly and label it as a proposal so it can be reviewed. Do not bury it as if it were already a decision.

## Editing diagrams

The five diagrams in `final-docs/diagrams/` come as paired files: `NN-name.svg` and `NN-name.html` (HTML embeds the SVG inline as a wrapper for browser preview).

**The user edits the HTML file directly.** When they ask for a diagram change, or you need to modify one:

1. **Read the `.html` file first** to capture the user's current state. Edits made in the HTML (text changes, layout tweaks, removed labels) are the source of truth.
2. **Edit the `.html` in place** using targeted `Edit` calls. Never regenerate the HTML wrapper from the SVG — that wipes the user's edits.
3. **After HTML edits, sync the SVG** by extracting the `<svg>…</svg>` block from the HTML and writing it to the `.svg` file (with an `<?xml version="1.0" encoding="UTF-8"?>` prepended). This keeps both files consistent without re-templating.

Do not generate a new HTML wrapper or rewrite the SVG from scratch unless the user explicitly asks for a redraw.

## Gitignored noise

`.claude/settings.local.json`, `.playwright-mcp/`, and `.superpowers/brainstorm/*/state/` are excluded by `.gitignore`. The `.superpowers/brainstorm/` directory contains transient brainstorm session state from earlier design work and is not part of the deliverable.

## Development environment

For local development, use ngrok to expose the API for Africa's Talking and WhatsApp callbacks:

```bash
ngrok http --url=nbd.ngrok.dev 3000
```

This tunnels local port 3000 to `nbd.ngrok.dev`, which is configured as the callback URL for Africa's Talking (USSD/WhatsApp) during development.

# Nile Basin Wetland Monitoring Platform (Phase 1)

This repository contains the source code and design documentation for the Nile Basin Discourse (NBD) platform designed for **Technical Support to Implement Citizen-Led Data Generation and Management Activities**.

---

## 🏗️ Project Architecture & Tech Stack

The application is structured as a multi-container stack orchestrated via Docker Compose:

- **Frontend**: Next.js application, proxying API calls to the backend.
- **Backend**: FastAPI application (Python) handling data ingestion, pipelines, and calculations.
- **Background Worker**: A separate Python container running scheduled background tasks natively via APScheduler.
- **Database**: PostgreSQL with PostGIS extensions for spatial data.
- **Proxy**: Nginx serving as the frontend and API gateway.
- **Admin Console**: PGAdmin4 for checking database tables in development.

---

## 📍 Spatial Infrastructure Hierarchy

All environmental data, sampling records, and pollution reports collected by the platform are anchored to exactly one level of the geographic hierarchy:
1. **Basin** (`basins` table): Watershed boundaries (MultiPolygon).
2. **Wetland** (`wetlands` table): Wetland zones belonging to a Basin (Polygon).
3. **Site** (`sites` table): Fixed sampling points belonging to a Wetland (Point).

For more detailed technical specifications, refer to [spatial_infrastructure_lld.md](docs/lld/spatial_infrastructure_lld.md).

---

## 📁 Repository Structure

```text
.
├── backend/            # FastAPI python source code & Dockerfile
├── frontend/           # Next.js app source code & Dockerfile
├── db/                 # PostgreSQL initialization script structure
├── pgadmin4/           # Pre-configured server profiles for PGAdmin4
├── docs/               # Platform schemas, user roles, API contracts
├── project-docs/       # Reference requirements and inception reports (read-only)
├── design-docs/        # solution-design-technical.md (SDD source of truth)
├── final-docs/         # Client-delivered PDF snapshots and SVG diagrams
├── dc.sh               # CLI helper wrapper script for Docker Compose
├── docker-compose.yml  # Base docker-compose configuration
├── nginx.conf          # Nginx gateway reverse-proxy configuration
└── README.md           # This file
```

---

## 🚀 Getting Started

### 📋 Prerequisites

Ensure you have the following installed:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS / Linux / Windows)
- `bash` (for running the CLI helper)

### ⚙️ Environment Configuration

Copy the example environment file and configure variables:

```bash
cp .env.example .env
```

Review and adjust the database credentials and app settings inside `.env` if necessary.

#### NFS Local Storage Configuration (Local Development)

The platform uses a self-hosted Network File System (NFS) mounted directory for storing media files and exports:

1. The local storage folder is located at `./storage` in the root directory and is mounted to `/app/storage` inside the backend containers.
2. Set the `STORAGE_DIR` in `.env` to `/app/storage` (as configured inside the container).
3. Set the `SECRET_KEY` in `.env` to a secure cryptographic secret (used for generating HMAC-SHA256 URL signatures).
4. Uploaded media is streamed asynchronously and saved under `media/{pipeline}/{uuid}.{ext}` (e.g., `media/whatsapp/f47ac10b-58cc-4372-a567-0e02b2c3d479.jpg`).

### 📱 Ingestion Pipelines

- **USSD Ingestion**: Stateless endpoint `/api/v1/ussd` handling Africa's Talking session menus.
- **WhatsApp Ingestion**: Endpoint `/api/v1/whatsapp/webhook` running a stateful chatbot with asynchronous, non-blocking media streaming to local storage.

### 🏃 Running Locally

Use the wrapper CLI script `./dc.sh` (modeled after IDH-IDC style) to run compose commands securely using the base configuration and developer overrides:

```bash
# Start all containers in the background
./dc.sh up -d

# Tail container logs
./dc.sh logs

# Stop and clean up containers
./dc.sh down
```

Once running, the services will be available at:

- **Wetland Portal (Frontend & Gateway)**: [http://localhost:3000](http://localhost:3000)
- **API Documentation (FastAPI Swagger)**: [http://localhost:3000/api/docs](http://localhost:3000/api/docs)
- **PGAdmin 4 Panel**: [http://localhost:5050](http://localhost:5050) (Login: `dev@akvo.org` / `password`)

---

## 🛠️ Seeders & Maintenance Scripts

You can run these scripts inside the backend container for setup and maintenance:

- **Interactive User Seeder**: Seed new local user credentials securely.

  ```bash
  ./dc.sh exec backend python app/scripts/create_user.py
  ```

- **KoboToolbox Submissions Sync**: Manually trigger Kobo survey sync to pull latest submissions.

  ```bash
  ./dc.sh exec backend python app/scripts/sync_kobo.py
  ```

- **Database Reference Seeder**: Seeds spatial reference basins/sub-counties and form blueprints.

  ```bash
  ./dc.sh exec backend python app/seeds/seeder.py
  ```

---

## 📝 Questionnaire Customisation & Scoring/Moderation Constraints

When modifying, extending, or creating form blueprints, specific rules must be followed to maintain compatibility with the platform's automated moderation and scoring engine pipelines:

### 1. Form Type Assignments
The database `Form.type` field determines which ingestion pipeline or scoring rule applies:
- **`1` (`CITIZEN_REPORTER`)**: Citizen pollution reports (USSD/WhatsApp). Mapped visually but not mathematically scored.
- **`2` (`CITIZEN_SCIENTIST`)**: **[Triggers Scoring Engine]** Monthly structured citizen wetland sampling records containing physico-chemical parameters.
- **`3` (`INDIGENOUS_KNOWLEDGE`)**: Community Focus Group Discussions (FGD). Aggregated into the Indigenous Knowledge (IK) Signal for soft fuzzy-logic adjustments.
- **`4` (`LAB_QA`)**: Professional lab control reports. Triggers auto-reconciliation check logs against nearby Type 2 data.
- **`5` (`EXTERNAL_SATELLITE`)**: Google Earth Engine climate and Sentinel overlays.

### 2. Core Mapped Fields for Type 2 (Scoring)
The backend status moderation logic (`PATCH /api/v1/submissions/{id}/status`) and WQI scoring engine rely on **exact question identifier names** (lowercased) in the form JSON structure:
- **`ph`**: Triggers pH quality ratings ($q_{\text{pH}}$) and is required (non-null).
- **`do`**: Triggers Dissolved Oxygen quality ratings ($q_{\text{DO}}$) and is required (non-null).
- **`temp`**: Triggers Water Temperature logging and is required (non-null).
- **`invasive_percent`**: Triggers invasive macrophyte density ratings for the Ecological Group Score (defaults to `0.0` if omitted).
- **`water_level`**: Triggers water level mapping for the Catchment Group Score (looks for option codes `"HIGH"`, `"MEDIUM"`, `"LOW"`; defaults to `"MEDIUM"` if omitted).

### 3. Modifying & Extending Blueprints
- **Blueprint Renaming**: You can safely change display labels or question orders in form blueprints. However, if you modify the machine-name identifiers of the core questions (`ph`, `temp`, `do`, `invasive_percent`, `water_level`), you **must** update the string matches inside [submission_router.py](backend/app/routers/submission_router.py) to prevent `HTTP 400` validation failures.
- **Adding New Parameters**: Ingesting new structured water quality parameters (e.g. salinity) will require an Alembic database migration to add target columns to the `sampling_records` table, updating the router extraction logic, and adjusting the WQI weights ($W_n$) in the scoring service.

---

## 📘 Design and Solution Design Document (SDD)

- The canonical source of truth for the Solution Design Document is located in [final-docs/Final SDD.pdf](final-docs/Final%20SDD.pdf) and [design-docs/solution-design-technical.md](design-docs/solution-design-technical.md).
- Visual system architecture diagrams are stored under [final-docs/diagrams/](final-docs/diagrams/).


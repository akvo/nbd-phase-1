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

## 📝 Questionnaire Customisation & Moderation Constraints

When modifying or extending form blueprints (such as the **Monthly Wetland Sampling** form), the following constraints must be respected to maintain system moderation functionality:

- **Core Mapped Fields**: The backend status moderation logic (`PATCH /api/v1/submissions/{id}/status`) relies on exact question identifier matches (`ph`, `temp`, `do`, `invasive_percent`, `water_level`) to extract values and dynamically map them to the structured `sampling_records` table on approval.
- **Blueprint Renaming**: You can safely change display labels or question orders in form blueprints. However, if you modify the machine-name identifiers of the core five questions in the form json, you must update the string matches inside [submission_router.py](backend/app/routers/submission_router.py).
- **Adding New Parameters**: Ingesting new structured water quality parameters (e.g. salinity) will require an Alembic database migration to add target columns to the `sampling_records` table and updating the router extraction logic to save them.

---

## 📘 Design and Solution Design Document (SDD)

- The canonical source of truth for the Solution Design Document is located in [design-docs/solution-design-technical.md](design-docs/solution-design-technical.md).
- Visual system architecture diagrams are stored under [final-docs/diagrams/](final-docs/diagrams/).

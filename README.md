# Nile Basin Wetland Monitoring Platform (Phase 1)

This repository contains the source code and design documentation for the Nile Basin Discourse (NBD) platform designed for **Technical Support to Implement Citizen-Led Data Generation and Management Activities**.

---

## 🏗️ Project Architecture & Tech Stack

The application is structured as a multi-container stack orchestrated via Docker Compose:

*   **Frontend**: Next.js application, proxying API calls to the backend.
*   **Backend**: FastAPI application (Python) handling data ingestion, pipelines, and calculations.
*   **Background Worker**: A separate Python container running scheduled background tasks natively via APScheduler.
*   **Database**: PostgreSQL with PostGIS extensions for spatial data.
*   **Proxy**: Nginx serving as the frontend and API gateway.
*   **Admin Console**: PGAdmin4 for checking database tables in development.

---

## 📁 Repository Structure

```
.
├── backend/            # FastAPI python source code & Dockerfile
├── frontend/           # Next.js app source code & Dockerfile
├── db/                 # PostgreSQL initialization script structure
├── pgadmin4/           # Pre-configured server profiles for PGAdmin4
├── docs/               # Platform schemas, user roles, API contracts
├── project-docs/       # Reference requirements and inception reports (read-only)
├── design-docs/        # solution-design-technical.md (Canonical SDD source of truth)
├── final-docs/         # Client-delivered PDF snapshots and SVG system diagrams
├── dc.sh               # CLI helper wrapper script for Docker Compose
├── docker-compose.yml  # Base docker-compose configuration
├── nginx.conf          # Nginx gateway reverse-proxy configuration
└── README.md           # This file
```

---

## 🚀 Getting Started

### 📋 Prerequisites

Ensure you have the following installed:
*   [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS / Linux / Windows)
*   `bash` (for running the CLI helper)

### ⚙️ Environment Configuration

Copy the example environment file and configure variables:

```bash
cp .env.example .env
```

Review and adjust the database credentials and app settings inside `.env` if necessary.

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
*   **Wetland Portal (Frontend & Gateway)**: [http://localhost:3000](http://localhost:3000)
*   **API Documentation (FastAPI Swagger)**: [http://localhost:3000/api/docs](http://localhost:3000/api/docs)
*   **PGAdmin 4 Panel**: [http://localhost:5050](http://localhost:5050) (Login: `dev@akvo.org` / `password`)

---

## 📘 Design and Solution Design Document (SDD)

*   The canonical source of truth for the Solution Design Document is located in [design-docs/solution-design-technical.md](file:///Users/galihpratama/Sites/nbd-phase-1/design-docs/solution-design-technical.md).
*   Visual system architecture diagrams are stored under [final-docs/diagrams/](file:///Users/galihpratama/Sites/nbd-phase-1/final-docs/diagrams/).

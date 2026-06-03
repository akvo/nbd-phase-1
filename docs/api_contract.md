# API JSON Contract Specification (v1): Nile Basin Wetland Monitoring Platform

## 1. Document Introduction and API Philosophy

### 1.1 Mission Statement
The NBD Citizen-Led Data Platform is a transboundary wetland monitoring system designed to formalise ecological intelligence in the Mara (Kenya/Tanzania) and Sio-Siteko (Kenya/Uganda) basins. By synthesising citizen-reported pollution events, monthly community sampling, and indigenous knowledge (IK) with Earth Observation data, the platform provides a structured digital channel for regional resource management.

### 1.2 Design Standards
The API adheres to RESTful architectural principles, utilising JSON as the primary exchange format. Spatial data is served via the GeoJSON standard (RFC 7946) to ensure seamless integration with GIS tools. All site identifiers utilise a persistent, structured format (e.g., `NBD-MARA-001`) to maintain referential integrity across all data layers. All specifications are provided in English (United Kingdom).

### 1.3 Protocol and Base URL
All communications must be conducted over HTTPS.
* **Base URL**: `https://portal.nbd.org/api/v1`

### 1.4 Version Control & Stability
* **Support Window**: The `v1` contract is stable and will be supported for a minimum of 12 months following the release of any subsequent major version (`v2.0`).
* **Deprecation**: Breaking changes will result in a major version increment in the URI path (e.g., `/api/v2/`).

---

## 2. Trust Boundaries and Authentication Architecture

### 2.1 Access Tier Definition
Access is segmented into three trust zones to protect data integrity and privacy.

| Trust Zone | Target Audience | Authentication Method |
| :--- | :--- | :--- |
| **Public** | General Public, Portal Viewers | None (Read-Only) |
| **Partner** | Academic Partners (Shadow Sampling), NDF Officials | SSO (OIDC) or JWT (via Email fallback) |
| **Admin / Processing** | NBD Secretariat, Akvo Operations | SSO (OIDC: Google/Microsoft) with MFA |

### 2.2 Authentication Mechanism
Authentication is implemented via OpenID Connect (OIDC). Successful authentication via Google or Microsoft providers returns a JSON Web Token (JWT). This token must be included as a Bearer token in the `Authorization` header for all non-public requests.

```http
Authorization: Bearer <JWT_TOKEN>
```

### 2.3 PII Protection Layer
Personally Identifiable Information (PII), specifically reporter phone numbers, is strictly confined to the Admin/Processing layer and the underlying PostgreSQL database.
* **Public Tier Constraint**: Public endpoints must never return phone numbers or raw individual submission IDs.
* **Data Scrubbing**: All incident reports served via the public API are aggregated by sub-county and date to ensure anonymity.

---

## 3. Public v1 API: Read-Only Wetland Intelligence (GET)

### 3.1 GET /api/v1/sites
* **Objective**: Returns a list of all active monitoring sites including country, basin, and current Health Class (A–E) for the public portal map and list views.
* **Query Parameters**:
  * `basin` (Optional): Filter by basin (Enum: `Mara`, `Sio-Siteko`).
  * `health_class` (Optional): Multi-select (Enum: `A`, `B`, `C`, `D`, `E`).

#### Response Payload Example
```json
[
  {
    "site_id": "NBD-MARA-001",
    "name": "Lower Mara Bridge",
    "basin": "Mara",
    "country": "Tanzania",
    "coordinates": {
      "type": "Point",
      "coordinates": [34.5212, -1.4589]
    },
    "current_health_class": "C"
  }
]
```

### 3.2 GET /api/v1/sites/{site_id}
* **Objective**: Returns comprehensive metadata and geometry for a specific site in GeoJSON format.
* **Path Parameters**:
  * `site_id` (Required): String identifier (e.g., `NBD-MARA-001`).

#### GeoJSON Feature Example
```json
{
  "type": "Feature",
  "id": "NBD-MARA-001",
  "geometry": {
    "type": "Point",
    "coordinates": [34.5212, -1.4589]
  },
  "properties": {
    "name": "Lower Mara Bridge",
    "basin": "Mara",
    "country": "Tanzania",
    "health_class": "C"
  }
}
```

### 3.3 GET /api/v1/sites/{site_id}/scores
* **Objective**: Returns historical health scores, group means, and specific Water Quality Index (WQI) sub-metrics for ECharts trend visualisation.
* **Query Parameters**:
  * `date_from` (Optional): ISO 8601 string.
  * `date_to` (Optional): ISO 8601 string.

#### WQI Sub-metric Response Detail
```json
{
  "site_id": "NBD-MARA-001",
  "history": [
    {
      "sampling_period": "2026-06",
      "group_means": {
        "physico_chemical": 0.16,
        "catchment_hydrological": 0.65,
        "ecological": 0.45
      },
      "wqi_details": {
        "total_wqi": 84.23,
        "parameters": [
          { "label": "pH", "weight_wn": 0.3704, "quality_rating_qn": 53.33 },
          { "label": "DO", "weight_wn": 0.6297, "quality_rating_qn": 102.40 }
        ]
      },
      "status": {
        "composite_score": 0.638,
        "ik_adjusted_score": 0.55,
        "traffic_light": "Yellow",
        "class": "C"
      },
      "management_actions": [
        {
          "label": "Establish Silt Traps",
          "description": "Install vegetative filters along the edges of agricultural plots to catch sediment."
        },
        {
          "label": "Construct Tertiary Wetlands",
          "description": "Encourage man-made wetlands at the edge of settlement zones to treat greywater."
        }
      ]
    }
  ]
}
```

### 3.4 GET /api/v1/incidents
* **Objective**: Returns pollution reports aggregated by `sub_county_name`. PII is scrubbed for the interactive map.
* **Query Parameters**:
  * `basin` (Optional): Enum (`Mara`, `Sio-Siteko`).
  * `type` (Optional): Multi-select Enum (`water_colour`, `smell`, `animal_kills`, `level_high`, `level_low`, `storm_event`).

#### Response Payload Example
```json
[
  {
    "incident_id": "INC-2026-05-001",
    "incident_type": "water_colour",
    "basin": "Mara",
    "sub_county": "Butiama",
    "status": "Approved",
    "reported_at": "2026-05-28T10:30:00Z",
    "coordinates": {
      "type": "Point",
      "coordinates": [34.567812, -1.234567]
    }
  }
]
```

### 3.5 GET /api/v1/sites/{site_id}/external/{source}
* **Objective**: Retrieves Google Earth Engine (GEE) processed satellite or climate data joined to the monitoring site.
* **Path Parameters**:
  * `site_id` (Required): String identifier.
  * `source` (Required): Enum (`sentinel-ndvi`, `chirps-rainfall`).

#### Response Payload Example
```json
{
  "site_id": "NBD-MARA-001",
  "provenance": {
    "source_name": "Google Earth Engine / Sentinel-2",
    "version": "v1.0",
    "collection_date": "2026-05-01"
  },
  "data_points": [
    { "date": "2026-05-01", "value": 0.7251 },
    { "date": "2026-04-01", "value": 0.6812 }
  ]
}
```

### 3.6 GET /api/v1/sites/{site_id}/unified-feed
* **Objective**: Provides a chronologically sorted "timeline" feed of all activities associated with a site.
* **Technical Logic**: This feed synthesises records from sampling events, external dataset updates, and incident reports. Incident reports are included in a specific site's feed via a backend spatial join, filtering for incidents reported within the geographical boundaries of the site's parent wetland polygon.

#### Response Payload Example
```json
{
  "site_id": "NBD-MARA-001",
  "feed": [
    {
      "timestamp": "2026-06-15T09:00:00Z",
      "type": "sampling_event",
      "data": {
        "health_class": "B",
        "score": 0.61
      }
    },
    {
      "timestamp": "2026-06-12T14:20:00Z",
      "type": "incident_report",
      "data": {
        "incident_type": "level_high",
        "sub_county": "Butiama"
      }
    }
  ]
}
```

---

## 4. Data Ingestion Layer: Webhooks and Form Intake (POST)

### 4.1 Africa’s Talking Webhooks
Ingests real-time reports from USSD (`*123#`) and WhatsApp.

* **Endpoint**: `POST /api/v1/ingest/pollution`
* **Headers**:
  * `X-Idempotency-Key` (Required): Client-provided token for request deduplication.
* **Payload Requirements**:
  * `channel`: Enum (`USSD`, `WhatsApp`).
  * `incident_type`: Integer (`1`: Murkier, `2`: Smell, `3`: Animal kills, `4`: High level, `5`: Low level).
  * `sub_county_name`: String (User-selected; geocoded server-side).
  * `reporter_id`: String (Hashed representation of MSISDN).
* **Server Behavior**: Returns `200 OK` only after persistence. If a duplicate key is detected, the server returns the cached success response without re-processing.

#### Submission Payload Example (WhatsApp)
```json
{
  "channel": "WhatsApp",
  "reporter_id": "HASHED_PHONE_ID",
  "incident_type": 3,
  "sub_county_name": "Butiama",
  "text_comment": "Observed near the bridge.",
  "media_attachments": [
    { "type": "photo", "url": "https://storage.nbd.org/media/photo_001.jpg" }
  ]
}
```

### 4.2 KoboToolbox Background Pull Worker
* **Mechanism**: A background worker polls the Kobo REST API every 60 minutes, using a watermark cursor on `submission_time` to fetch new structured sampling records offline-submitted by Citizen Scientists.

### 4.3 Admin Webforms Ingestion

#### POST /api/v1/lab-results
Captures shadow sampling data (BOD, Nitrate, Mercury) provided by academic partners.
* **Role Requirement**: `Partner` or `Admin`.

```json
{
  "site_id": "NBD-MARA-001",
  "sampling_period": "2026-Q2",
  "results": {
    "biochemical_oxygen_demand": 4.2,
    "orthophosphate": 0.15,
    "nitrate": 1.8,
    "mercury": 0.002
  }
}
```

#### POST /api/v1/fgd-records
Captures qualitative Indigenous Knowledge signals from Monthly Barazas (Focus Group Discussions).
* **Role Requirement**: `Reviewer` or `Admin`.

```json
{
  "wetland_id": "Mara",
  "period": "2026-06",
  "participant_count": 12,
  "dimensions": {
    "fish_abundance": "MODERATELY_DECLINED",
    "water_clarity": "MUCH_WORSE",
    "vegetation_cover": "PARTIALLY_LOST"
  }
}
```

---

## 5. Admin and Processing Layer: State-Mutating Endpoints (POST / PUT / DELETE)

### 5.1 Data Moderation Workflow
All citizen submissions enter as `Pending`. Approving a record triggers the automated scoring engine.

* **POST /api/v1/moderation/{record_id}/approve**
  * Approves the pending record and triggers scoring calculation.
  * **Role Requirement**: `Reviewer` or `Admin`.
* **POST /api/v1/moderation/{record_id}/reject**
  * Rejects the record, archiving it and excluding it from portal scores.
  * **Role Requirement**: `Reviewer` or `Admin`.

### 5.2 Site and User Management

* **POST /api/v1/sites**
  * Create new monitoring sites with GeoJSON point coordinates.
  * **Role Requirement**: `Admin`.
  * **Payload Schema**:
    ```json
    {
      "site_id": "NBD-MARA-002",
      "name": "Upper Mara Gorge",
      "basin": "Mara",
      "country": "Kenya",
      "geometry": {
        "type": "Point",
        "coordinates": [34.612345, -1.123456]
      },
      "metadata": {
        "description": "Rocky gorge area.",
        "active": true
      }
    }
    ```
* **PUT /api/v1/sites/{site_id}**
  * Updates details of an existing site.
  * **Role Requirement**: `Admin`.
* **DELETE /api/v1/sites/{site_id}**
  * Removes a monitoring site and soft-deletes associated records.
  * **Role Requirement**: `Admin`.
* **POST /api/v1/users/invite**
  * Triggers the OIDC invitation flow for new administrators.
  * **Role Requirement**: `Admin`.
  * **Payload Schema**:
    ```json
    {
      "email": "user@nbd.org",
      "role": "Reviewer"
    }
    ```

### 5.3 Audit Logging Mandate
All state-mutating requests (`POST`, `PUT`, `DELETE`) are logged.
* **Actor ID**: Must record the OIDC Subject (`sub`) claim.
* **Response**: Successful mutations return `200 OK` or `204 No Content` including a unique `audit_id` in the response body or headers.

---

## 6. Data Model and Schema Definitions

### 6.1 SamplingRecord (KoboToolbox Intake)
```json
{
  "site_id": "NBD-MARA-001",
  "status": "Approved",
  "moderated_by": "user_sub_id_123",
  "moderated_at": "2026-06-15T10:00:00Z",
  "water_quality": {
    "ph": 7.8,
    "temperature_c": 23.25,
    "dissolved_oxygen_mg_l": 4.77
  },
  "ecological": {
    "invasive_macrophyte_percent": 25,
    "cpue": {
      "target_species": "Tilapia",
      "catch_count": 15,
      "effort_hours": 4
    }
  }
}
```

### 6.2 FGDRecord (IK Signal)
```json
{
  "wetland_id": "Mara",
  "ik_signals": {
    "fish_abundance": 0.6,
    "water_clarity": 1.0,
    "vegetation_cover": 0.4
  },
  "calculated_ik_signal": 0.67
}
```

### 6.3 HealthScore (Fuzzy Logic Output)
Health Classes:
* **A**: `0.8 - 1.0`
* **B**: `0.6 - 0.8`
* **C**: `0.4 - 0.6`
* **D**: `0.2 - 0.4`
* **E**: `0.0 - 0.2`

```json
{
  "site_id": "NBD-MARA-001",
  "raw_composite_score": 0.638,
  "ik_signal_input": 0.67,
  "final_adjusted_score": 0.55,
  "health_class": "C",
  "traffic_light": "Yellow"
}
```

### 6.4 ManagementAction
```json
{
  "site_id": "NBD-MARA-001",
  "type": "Yellow",
  "short_label": "Establish Silt Traps",
  "description": "Install vegetative filters along the edges of agricultural plots to catch sediment and nutrient runoff..."
}
```

---

## 7. Operational Standards: Errors and Rate Limiting

### 7.1 Error Handling
The API utilises standard HTTP semantics for error reporting.

| Code | Meaning | Context |
| :--- | :--- | :--- |
| **400** | Bad Request | Validation failure (e.g., pH outside 2–10 range). |
| **401** | Unauthorised | Missing or expired JWT. |
| **403** | Forbidden | Accessing Admin endpoints with a Reviewer role. |
| **429** | Too Many Requests | Rate limit exceeded. |

#### Error Response Body
```json
{
  "error": true,
  "code": 400,
  "message": "Value for ph (11.0) exceeds permissible range (2-10)."
}
```

### 7.2 Rate Limiting and Required Headers
* **Policy**: 60 requests per minute per IP address for all public endpoints.
* **Required Headers**:
  * `Content-Type`: `application/json`
  * `X-Content-Type-Options`: `nosniff`
  * `X-Frame-Options`: `DENY`

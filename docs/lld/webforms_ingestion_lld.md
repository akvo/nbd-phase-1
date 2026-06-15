# LLD — Dynamic Web Forms Data Ingestion (akvo-react-form)

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Tech Lead / Winston (Architect) | Target Location: `docs/lld/webforms_ingestion_lld.md` | References: `docs/prd/webforms_ingestion_prd.md`, `docs/lld/admin_layout_lld.md`, `docs/lld/dynamic_datapoints_lld.md`
> Status: `Under Review`

---

## 1. Overview & Scope

### Component / Module
Dynamic Form integration using the `akvo-react-form` React component in the admin dashboard panel, complemented by backend routers processing FGD (Focus Group Discussion) qualitative signals and Lab QA quantitative results.

### PRD References
- **FR-001** (Render dynamic web forms on "+ Add New" action)
- **FR-002** (FGD endpoint `/api/v1/internal/fgd` calculating averaged IK signal)
- **FR-003** (Lab QA endpoint `/api/v1/internal/lab-qa` saving academic metrics)

---

## 2. Component Design & Frontend Integration

### Frontend Routing & Page Integration
Inside the Admin Data View ([data/page.tsx](/frontend/src/app/admin/data/page.tsx)), clicking the "+ Add new" action button redirects the user to `/admin/data/new/{formId}` (dynamic segment routing).

We will create a Next.js dynamic page:
- **Path**: `frontend/src/app/admin/data/new/[formId]/page.tsx`
- **Implementation**:
```typescript
'use client';

import React, { useState, useEffect, use } from 'react';
import { useRouter } from 'next/navigation';
import AkvoReactForm from 'akvo-react-form';
import { apiClient } from '@/lib/api';

export default function NewFormPage({ params }: { params: Promise<{ formId: string }> }) {
  const router = useRouter();
  const { formId } = use(params);
  const [blueprint, setBlueprint] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.get(`/forms/${formId}/blueprint`)
      .then(res => setBlueprint(res.data))
      .finally(() => setLoading(false));
  }, [formId]);

  const handleFinish = async (values: any) => {
    let endpoint = '/internal/submit';
    if (formId === 'fgd') endpoint = '/internal/fgd';
    else if (formId === 'lab-qa') endpoint = '/internal/lab-qa';

    await apiClient.post(endpoint, { ...values, form_id: formId });
    router.push('/admin/data');
  };

  if (loading) return <div className="p-8">Loading Form blueprint...</div>;

  return (
    <div className="max-w-3xl mx-auto bg-white p-6 rounded-xl border border-slate-200 shadow-sm my-6">
      <h2 className="text-xl font-bold text-slate-800 mb-6">Submit {formId.toUpperCase()} Data</h2>
      {blueprint && <AkvoReactForm form={blueprint} onFinish={handleFinish} />}
    </div>
  );
}
```

---

## 3. Backend Routing & Payload Processing

A new router file `backend/app/routers/internal_router.py` will expose the following endpoints:

### 3.1 FGD Submission Endpoint
- **Path**: `POST /api/v1/internal/fgd`
- **Logic**:
  1. Receives the dynamic JSON payload containing answers for fish abundance, water clarity, and vegetation cover.
  2. Maps dropdown selection values to numeric weights:
     - `GOOD` / `INCREASED` / `HIGH` = `1.0`
     - `MODERATE` / `STABLE` / `MEDIUM` = `0.5`
     - `POOR` / `DECLINED` / `LOW` = `0.0`
  3. Computes the average:
     $$\text{IK Signal} = \frac{\text{Fish Weight} + \text{Clarity Weight} + \text{Vegetation Weight}}{3}$$
  4. Inserts a record in `datapoint` with:
     - `wetland_id` = provided `wetland_id`
     - `status` = `'APPROVED'`
     - `submitted_by` = current authenticated user ID
  5. Inserts computed `ik_signal` into the answers/calculated attributes table.

### 3.2 Lab QA Submission Endpoint
- **Path**: `POST /api/v1/internal/lab-qa`
- **Logic**:
  1. Validates presence of `site_id` and `sampling_period` (e.g. `"2026-Q2"`).
  2. Inserts a record in `datapoint` with:
     - `site_id` = provided `site_id`
     - `status` = `'APPROVED'`
  3. Saves the academic parameters (BOD, Nitrate, Mercury) as `answers` linked to the created `datapoint_id`.

### 3.3 Generic Submission Endpoint
- **Path**: `POST /api/v1/internal/submit`
- **Logic**:
  1. Receives payload containing `form_id`, geo anchor (`basin_id`, `wetland_id`, or `site_id`), and answers collection.
  2. Creates a `datapoint` with:
     - `form_id` = `form_id`
     - `basin_id` / `wetland_id` / `site_id` = provided anchor
     - `status` = `'PENDING'` (requires moderation)
  3. Iterates over answers list and saves each dynamic question answer as a row in the `answer` (EAV) table.


### 3.4 Question Type Mapping & Media Uploads
To fully support all Akvo-React-Form field types, `resolve_answers_and_anchors` parses and maps question values to correct database columns in the `Answer` model:
- **`number`**: Placed in `Answer.value` (float).
- **`cascade`**: Stored as a list of hierarchical strings in `Answer.options`, and the terminal/last element is stored in `Answer.name`.
- **`multiple_option`**: Stored as a list of selected values in `Answer.options`.
- **`image`, `signature`, `attachment`**: Checked for base64 encoded data URLs (e.g. `data:image/` or `data:application/`). If present, decodes the payload, uploads the binary file to local NFS storage using `StorageService`, and stores the relative path in `Answer.name`.
- **`geo`, `geotrace`, `geoshape`**: Coordinates list/dict serialized as JSON strings and stored in `Answer.name`.
- **All other types**: Stored as strings in `Answer.name`.

---


## 4. Verification Plan

### Automated Tests
- **Backend**:
  - Test `/api/v1/internal/fgd` calculation accuracy (asserting calculated IK signal value is exactly `0.5` when inputting `["GOOD", "POOR", "MODERATE"]`).
  - Test `/api/v1/internal/lab-qa` fails with `400` if `site_id` is missing.
  - Test `/api/v1/internal/submit` correctly parses options and sets `status` to `'PENDING'`.
- **Frontend**:
  - Mock `<AkvoReactForm>` component and assert `onFinish` triggers the correct API endpoint calls.

### Manual Verification
- Deploy to test env, fill out a mock FGD form, and verify that the database record is inserted directly with `'APPROVED'` status and the mathematically calculated average.
- Submit a generic form and check that the submission goes to the moderator's `Pending` queue.

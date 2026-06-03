# PRD — Secure Cloud Storage Provisioning

> **Stage 2 of 3 — Documentation Hierarchy**
> Owner: DevOps/Winston | Target Location: `docs/prd/cloud_storage_prd.md` | References: `docs/product_brief.md`
> Status: `In Review`

---

## 1. Overview

**One-liner**:
Establish a secure, compliant, private Google Cloud Storage (GCS) infrastructure using the Google Cloud Web Console to store citizen photo assets from KoboCollect.

**Brief / Problem Reference**:
Ref: `docs/product_brief.md`, `docs/user_roles_rbac.md`

**What we are building** (What):
A secure private cloud storage bucket located in `europe-west1` with all public access strictly blocked, accompanied by a dedicated IAM Service Account with scoped bucket permissions and JSON credential management via GCP Secret Manager.

**Why now** (Strategic context):
Kenya, Uganda, and Tanzania enforce strict data protection acts (DPA 2019/2022). Since Google Cloud lacks a physical East African region, we must provision data storage in `europe-west1` (Belgium) because EU GDPR equivalence satisfies cross-border transfer compliance criteria for these countries.

---

## 2. Goals & Success Metrics

| Goal | Success Metric | Baseline | Target | Owner |
|------|---------------|----------|--------|-------|
| Prevent data leaks of citizen photos | Direct public URL requests to objects | N/A | 100% block rate (HTTP 403) | Security Lead |
| Compliance with cross-border transfer laws | Bucket residency validation | N/A | Located in `europe-west1` | DevOps Lead |
| Least-privilege IAM management | Service account privilege scope | Global | Bucket-specific access only | DevOps Lead |

**Anti-Goals**:
- We are not deploying infrastructure as code (Terraform) in this phase; setup is explicitly directed to be manual via the GCP Web Console UI.
- We will not configure multi-region or dual-region replication due to cost constraints and strict sovereignty/residency constraints.

---

## 3. Target Users & Personas

| Persona | Job-to-be-Done | Key Frustration | v1 Priority |
|---------|---------------|-----------------|-------------|
| DevOps Engineer | Securely set up cloud buckets manually | Complexity in navigating console settings | Primary |
| Application Developer | Access photos securely via signed URLs | Storing credentials in plain text code | Secondary |

---

## 4. User Stories

| ID | User Story | Priority (MoSCoW) | FR Reference |
|----|-----------|-------------------|--------------|
| US-001 | As a **DevOps Engineer**, I want to manually configure GCS via the GCP Web Console so that the storage is running in a compliant region with public access disabled. | Must Have | FR-001, FR-002, FR-003 |
| US-002 | As a **Developer**, I want a dedicated Service Account credentials key stored in Secret Manager so that my application can read and write files without committing credentials to Git. | Must Have | FR-004, FR-005 |

---

## 5. Functional Requirements

| ID | Requirement | User Story | Priority |
|----|-------------|------------|----------|
| FR-001 | The bucket MUST be created in the `europe-west1` (Belgium) region. | US-001 | Must Have |
| FR-002 | Public Access Prevention MUST be set to "Enforced" to block all public access to the bucket. | US-001 | Must Have |
| FR-003 | Access control MUST be set to "Uniform" to enforce bucket-level IAM policies and prevent ACL override. | US-001 | Must Have |
| FR-004 | A Service Account MUST be created with no global roles, but granted `Storage Object Admin` strictly on the bucket itself. | US-002 | Must Have |
| FR-005 | The Service Account private JSON key MUST be generated and uploaded to GCP Secret Manager. | US-002 | Must Have |

---

## 6. Non-Functional Requirements

| Category | Requirement | Metric |
|----------|-------------|--------|
| **Privacy** | Public requests to raw GCS URLs | HTTP 403 Forbidden |
| **Security** | Secrets Storage | AES-256 encrypted at rest in GCP Secret Manager |
| **Security** | Credential rotation | Manual rotation support through Secret Manager versions |

---

## 7. Step-by-Step GCP Console Web UI Setup Guide

### 7.1. Create the Private GCS Bucket
1. In the Google Cloud Console, navigate to the **Cloud Storage > Buckets** page.
2. Click **Create** at the top of the page.
3. **Name your bucket**: Enter a unique name, e.g., `nbd-storage`. Click **Continue**.
4. **Choose where to store your data**:
   - Location type: Select **Region**.
   - Region: Select **europe-west1 (Belgium)**.
   - Click **Continue**.
5. **Choose a storage class**: Select **Standard**. Click **Continue**.
6. **Choose how to control access to objects**:
   - Access control: Select **Fine-grained**. (ensures bucket-level IAM policies are enforced).
   - Check the box for **Enforce public access prevention on this bucket**.
   - Click **Continue**.
7. **Choose how to protect object data**: Leave settings as default (Google-managed encryption key).
8. Click **Create**. If prompted with a pop-up warning that public access will be prevented, click **Confirm**.

---

### 7.2. Create the IAM Service Account
1. In the Google Cloud Console, navigate to **IAM & Admin > Service Accounts**.
2. Click **Create Service Account** at the top of the page.
3. Enter service account details:
   - **Service account name**: `nbd-gcs-writer`.
   - **Service account ID**: Automatically generated (e.g., `nbd-gcs-writer`).
   - **Service account description**: Scoped read/write access to citizen photos bucket.
4. Click **Create and Continue**.
5. **Grant this service account access to project**: Leave this blank! (We grant scoped permissions at the bucket level instead of the project level to respect least-privilege). Click **Continue**.
6. Click **Done**.

---

### 7.3. Grant Service Account Bucket Permissions
1. Navigate back to **Cloud Storage > Buckets**.
2. Click on the name of the bucket you created (`nbd-storage`).
3. Select the **Permissions** tab.
4. Under the **View by principals** section, click **Grant Access**.
5. In the **New principals** field, paste the full email address of the service account you created (e.g., `nbd-gcs-writer@[PROJECT_ID].iam.gserviceaccount.com`).
6. In the **Select a role** dropdown, select **Cloud Storage > Storage Object Admin**.
7. Click **Save**.

---

### 7.4. Generate Private Key and Configure Credential Storage

1. Navigate back to **IAM & Admin > Service Accounts**.
2. Click on the email address of the service account you created (`nbd-gcs-writer`).
3. Select the **Keys** tab.
4. Click the **Add Key** dropdown and select **Create new key**.
5. Choose **JSON** as the key type and click **Create**. The key file (e.g., `[PROJECT_ID]-[KEY_ID].json`) will download automatically to your computer. Keep this file secure temporarily.

Select one of the following integration strategies depending on your target environment:

#### Option A: Local Development (Similar to other Akvo projects)
To run the stack locally via Docker Compose without pulling keys from Secret Manager:
1. Create a secure credentials directory inside your workspace root:
   ```bash
   mkdir -p credentials
   ```
   *(Note: This directory is ignored by Git via `.gitignore` to prevent secret leakage).*
2. Place the downloaded JSON key file into that directory (e.g., `./credentials/nbd-service-account.json`).
3. Add the following variable to your local `.env` file:
   ```env
   GOOGLE_APPLICATION_CREDENTIALS=/credentials/nbd-service-account.json
   ```
4. Update `docker-compose.override.yml` to mount the credentials folder and inject the environment variable into the backend service:
   ```yaml
   services:
     backend:
       environment:
         - GOOGLE_APPLICATION_CREDENTIALS=/credentials/nbd-service-account.json
       volumes:
         - ./credentials:/credentials:ro
   ```

#### Option B: Production (GCP Secret Manager)
For secure cloud container environments (e.g., Cloud Run or GKE):
1. Navigate to **Security > Secret Manager** in the console.
2. Click **Create Secret** at the top.
3. **Name**: Enter `gcs-sa-key`.
4. Under **Secret value**, click **Upload File** and select the JSON key file you just downloaded.
5. Click **Create Secret**.
6. **Securely delete** the downloaded JSON key file from your local computer's storage.

---

### 7.5. Grant Application Instance Access to the Secret (Production Only)
To allow your production application container running on GCP (e.g. Cloud Run, GKE, or Compute Engine) to read this secret:
1. In Secret Manager, click on the secret `gcs-sa-key`.
2. Select the **Permissions** tab.
3. Click **Grant Access**.
4. In **New principals**, enter the service account identity under which your application instance runs (e.g., the default Compute Engine service account or a custom app runner service account).
5. In **Select a role**, choose **Secret Manager > Secret Manager Secret Accessor**.
6. Click **Save**.

---

## 8. Scope

**In Scope**:
- Creating a single-region bucket in `europe-west1`.
- Blocking public access (Public Access Prevention) and setting Uniform access.
- Binding service account strictly at the bucket level.
- Storing the JSON key securely in Secret Manager.

**Explicitly Out of Scope**:
- Terraform code or CLI-based scripting for provisioning.
- Deploying cross-region failovers or CDN/Load Balancer proxies in front of the bucket.

---

## 9. Assumptions & Constraints

- **Assumptions**: The user has full admin access to the target GCP Console Project to create resources, service accounts, and secrets.
- **Constraints**: No East African GCP region exists; hence `europe-west1` is used.

---

## 10. Verification Plan

- Attempt to fetch any uploaded item anonymously using a direct web URL (e.g., `https://storage.googleapis.com/nbd-storage/nonexistent.jpg`).
- Verify that it returns `HTTP 403 Forbidden` (UAC 1.1).
- Verify that the service account JSON key is retrieveable only by authorized identities using Secret Manager version accesses.

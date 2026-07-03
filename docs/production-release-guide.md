# Production Release Guide

> **Audience**: Release managers, tech leads, and repository admins.
> **Purpose**: End-to-end guide for deploying NBD Phase 1 to the production cluster using GitHub Releases.

---

## Overview

Production deployments are **gated** — no code reaches the live cluster without a designated reviewer explicitly approving it via the GitHub UI.

```text
Merge PRs to main          → Auto-deploys to TEST cluster (deploy.yml)
Publish a GitHub Release   → Triggers PRODUCTION deployment (release.yml)
                             ↳ Pauses for reviewer approval
                             ↳ Deploys only after approval
```

---

## Release Process (Per Release)

### Step 1 — Prepare the Codebase

1. Ensure all feature PRs are reviewed, approved, and merged into `main`.
2. Verify the test cluster environment (auto-deployed from `main`) is stable and has been signed off by QA.

---

### Step 2 — Create the Release and Tag on GitHub

1. Go to your repository on GitHub.
2. In the right-hand sidebar, click on **Releases** (or go directly to `https://github.com/akvo/nbd-phase-1/releases`).
3. Click the **Draft a new release** button.
4. Click the **Choose a tag** dropdown menu.
5. Type your version tag name (e.g., `v1.0.0`) and click **Create new tag: v1.0.0 on publish**.
   > ✅ **Tag naming convention**: Always use `v`-prefixed semantic versioning:
   >
   > - `v1.0.0` — major release
   > - `v1.1.0` — minor release (new features, backwards compatible)
   > - `v1.1.1` — patch release (bug fixes only)
6. Ensure the **Target** branch is set to `main`.
7. Add a **Release title** (e.g., `v1.0.0 — Initial Production Release`).
8. Click **Generate release notes** to automatically compile changes from merged PRs, or write description manually:

   ```markdown
   ## Features

   - Feature A description (#PR_NUMBER)
   - Feature B description (#PR_NUMBER)

   ## Bug Fixes

   - Fix description (#PR_NUMBER)

   ## Breaking Changes

   - None
   ```

9. Click **Publish release**.

---

### Step 4 — Monitor the Deployment Pipeline

1. Go to **Actions** → select the `Deploy to Production Cluster` workflow run.
2. Watch the **Run Tests** job complete (all backend and frontend tests must pass).
3. After tests pass, the **Build and Push** job will be **waiting for approval** — a yellow banner appears:
   > _"Waiting for review — This deployment is waiting for a review."_

---

### Step 5 — Approve the Production Deployment

**As a reviewer** (you must be in the required reviewers list):

1. Open the workflow run in **Actions**.
2. Click the yellow **"Review deployments"** button.
3. Check the box next to `Production`.
4. Review the release notes and confirm the tag is correct.
5. Click **Approve and deploy**.

> The workflow will then proceed to:
>
> - Build Docker images for `nginx`, `frontend`, `backend`, and `worker`
> - Push images to Google Container Registry (production)
> - Roll out Kubernetes deployments in the production cluster

---

### Step 6 — Verify the Production Deployment

1. Monitor the **Rollout to Production Server** job in GitHub Actions until all 4 rollout steps show ✅.
2. Verify the production environment is healthy:
   - Open the production URL and confirm the app loads correctly.
   - Check the API health endpoint.
   - Spot-check key features from the release notes.

---

## Part 3 — Rejecting a Deployment

If you find a critical issue after publishing the release but **before approving**:

1. Go to **Actions** → open the waiting `Deploy to Production Cluster` run.
2. Click **"Review deployments"**.
3. Click **Reject**.
4. Add a comment explaining the reason.
5. The deployment is cancelled. Fix the issue on `main`, then create a new patch release (e.g., `v1.0.1`).

---

## Part 4 — Rollback Procedure

If a production deployment has been approved and rolled out but causes critical issues:

1. **Immediately** notify the team and contact **DevOps Support** to request an emergency rollback.
2. Provide DevOps with the **last stable version tag** (e.g., `v1.0.0`) to restore.
3. Once the environment is rolled back, create a `hotfix/` branch, resolve the issue, and initiate a new release cycle (e.g., `v1.0.2`).

---

## Quick Reference

| Action                        | Who                 | Where                |
| ----------------------------- | ------------------- | -------------------- |
| Merge PRs to main             | Developer           | GitHub Pull Requests |
| Validate on test cluster      | QA / Developer      | Test environment URL |
| Create Tag & Publish Release  | Release Manager     | GitHub → Releases    |
| Approve production deployment | Designated Reviewer | GitHub → Actions     |
| Verify production health      | QA / Developer      | Production URL       |
| Rollback (emergency)          | DevOps Support      | Kubernetes Cluster   |

---

## Related Files

| File                                                                | Purpose                                             |
| ------------------------------------------------------------------- | --------------------------------------------------- |
| [`.github/workflows/release.yml`](../.github/workflows/release.yml) | Production deployment workflow definition           |
| [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml)   | Test cluster deployment (triggered on push to main) |
| [`docs/prd/deployment_prd.md`](prd/deployment_prd.md)               | Full requirements and architecture documentation    |
| [`ci/test.sh`](../ci/test.sh)                                       | Test runner script used in CI                       |

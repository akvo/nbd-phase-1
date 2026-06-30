# PRD — Form Blueprint Export Utility

## 1. Overview & Goal

- **Problem Statement**: Administrators modify and design forms within the workspace form editor, which saves them in the local relational database. Currently, there is no way to export these form definitions to deploy them to other platforms (like KoboToolbox) or version-control them in repository files. To import a form structure into KoboToolbox, it must be compiled into either a specialized JSON schema or an XLSForm (Excel workbook with `survey`, `choices`, and `settings` worksheets). Additionally, cascade selection datasets (like spatial basins, counties, and sites) are huge and should be managed as external CSV attachments (`select_one_from_file`) rather than being hardcoded in every single form.
- **Goal**: Create an API endpoint and a CLI script to export a form blueprint from our database into:
  1. A standard JSON representation matching our frontend `FormBlueprintResponse` schema.
  2. A KoboToolbox-compliant XLSForm (Excel spreadsheet).
- **Core Metric**: 100% success rate in uploading exported XLSForms to KoboToolbox without validation errors.

---

## 2. Requirements (Scope Guardrails)

### Must-Have

- **JSON Export Endpoint**:
  - `GET /api/v1/forms/{form_id}/export/json`: Returns the full blueprint JSON payload matching the `FormBlueprintResponse` schema.
- **XLSForm Excel Export**:
  - `GET /api/v1/forms/{form_id}/export/xlsform`: Generates and downloads a `.xlsx` file containing the three required XLSForm sheets:
    - **`survey`**: `type`, `name`, `label`, `required`, `hint`, `relevant` (dependencies), and `constraint`.
    - **`choices`**: `list_name`, `name`, `label` for multiple-choice select questions.
    - **`settings`**: `form_title`, `form_id`, `version`, `default_language`.
- **Shared Cascade Selection CSV Export**:
  - An endpoint/script to download a shared cascade select CSV file containing the spatial hierarchical datasets (e.g. `counties`, `subcounties`, `basins`, `wetlands`, `sites`) so they can be loaded externally on Kobo using the `select_one_from_file` mechanism.
- **Frontend Export Actions**:
  - Add download action buttons/dropdown options in the Form Management dashboard (`frontend/src/app/admin/resources/forms/page.tsx`) to allow administrators to directly trigger and download the JSON or XLSForm file for any form in the list.

### Nice-to-Have

- A CLI management command (e.g. `./dc.sh exec backend python -m app.scripts.export_form --form-id <id> --format <json|xlsform>`) to perform the export directly to a local file.

### Out of Scope

- Importing XLSForm Excel files _into_ our database (this is export-only).
- Styling the Kobo layout (colors, grids) beyond the default XLSForm standard structure.

---

## 3. XLSForm Mapping Architecture

### XLSForm Sheet Structures

#### 1. `survey` Sheet

| type                   | name                  | label::English (en) | label::Swahili (sw) | required | relevant | hint                         |
| :--------------------- | :-------------------- | :------------------ | :------------------ | :------- | :------- | :--------------------------- |
| `begin_group`          | `group_water_quality` | Water Quality       | Ubora wa Maji       |          |          |                              |
| `integer`              | `temp`                | Temperature         | Joto                | yes      |          | Water temperature in Celsius |
| `select_one option_ph` | `ph_level`            | pH Level            | Kiwango cha pH      | yes      |          |                              |
| `end_group`            |                       |                     |                     |          |          |                              |

#### 2. `choices` Sheet

| list_name   | name       | label::English (en) | label::Swahili (sw) |
| :---------- | :--------- | :------------------ | :------------------ |
| `option_ph` | `acidic`   | Acidic              | Asidi               |
| `option_ph` | `neutral`  | Neutral             | Kawaida             |
| `option_ph` | `alkaline` | Alkaline            | Alikalini           |

#### 3. `settings` Sheet

| form_title                | form_id                   | version | default_language |
| :------------------------ | :------------------------ | :------ | :--------------- |
| Physico-Chemical Sampling | physico_chemical_sampling | 1       | English (en)     |

---

## 4. Shared External Cascade Files

If a question uses a cascade dataset (like select county, select site):

- Instead of generating thousands of rows in the `choices` sheet, the XLSForm type will be set to:
  - `select_one_from_file spatial_cascade.csv`
- The system will provide an export endpoint `GET /api/v1/reference/spatial-cascade/csv` that generates `spatial_cascade.csv` with columns:
  - `list_name`, `name`, `label`, `parent_key`
- This allows all forms in Kobo to share a single external resource file for geographic selection lists.

---

## 5. Acceptance Criteria

### User Acceptance Criteria (UAC)

- **Given** an administrator has configured a form with custom text, integer, and select questions,
  - **When** they click "Export to XLSForm" in the dashboard,
  - **Then** a valid Excel `.xlsx` file downloads.
  - **When** the Excel file is uploaded to the official [KoboToolbox XLSForm validator](https://xlsform.org/),
  - **Then** the validator reports "XLSForm is valid!".

### Technical Acceptance Criteria (TAC)

- The XLSForm exporter must format headers correctly with language locales (e.g. `label::English (en)` and `label::Swahili (sw)`).
- Excel sheets must be built using `openpyxl` or `pandas` inside the Python backend.

---

## 6. Ballpark Estimation

- **Component Breakdown**:
  - **JSON Export API**: ~2h (Simple)
  - **XLSForm Exporter Logic (`openpyxl` mappings)**: ~8h (Complex)
  - **Shared Cascade CSV Endpoint**: ~3h (Medium)
  - **CLI Command Wrapper**: ~2h (Simple)
  - **Frontend Export Actions (dashboard download buttons)**: ~3h (Medium)
- **Total Estimate**: ~2.5 - 3.5 developer days.

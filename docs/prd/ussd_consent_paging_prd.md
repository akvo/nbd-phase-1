# PRD — USSD Consent Paging

> **Stage 2 of 3 — Documentation Hierarchy**
> Owner: PM + Winston (Architect) | Target Location: `docs/prd/ussd_consent_paging_prd.md`
> Status: `Approved`

---

## 1. Overview & Goal

**Problem Statement**:
The USSD channel has a strict character display limit (160 characters per screen). Because of this, the data terms and conditions text must be split into multiple pages. 
Currently, the system prompts the user to accept (reply `1`) or decline (reply `2`) the terms immediately. If a user tries to view more terms by replying with `98`, the backend fails to parse the choice and terminates the session as a rejection. If they attempt to reply with `1` from subsequent pages, it is not processed, and they cannot proceed.

**Core Metric**:
* USSD data terms drop-off reduction.
* 100% success rate for users proceeding to report after reading paginated terms.

---

## 2. User Journey & Flows

### Traversal Sequence (English)
1. **Screen 1 (Language selection)**:
   - User dials the USSD code.
   - Menu:
     ```text
     CON Choose Language / Chagua Lugha:
     1. English
     2. Kiswahili
     ```
   - User inputs `1` (English).

2. **Screen 2 (Consent Page 1)**:
   - Menu:
     ```text
     CON Welcome to NBD Wetland Watch. This platform collects environmental incident reports. Your report is saved anonymously.
     98. View More
     2. Decline
     ```
   - User inputs `98` (View More).

3. **Screen 3 (Consent Page 2)**:
   - Menu:
     ```text
     CON Data usage is restricted to monitoring programs. By proceeding, you agree to these terms.
     1. Accept & Start Reporting
     0. Back
     ```
   - User inputs `1` (Accept).

4. **Screen 4 (First Dynamic Question)**:
   - Session continues to dynamic questions (e.g., Incident Type selection).

---

### Traversal Sequence (Kiswahili)
1. **Screen 1 (Language selection)**:
   - User inputs `2` (Kiswahili).

2. **Screen 2 (Consent Page 1)**:
   - Menu:
     ```text
     CON Karibu kwenye NBD Wetland Watch. Jukwaa hili linakusanya taarifa za matukio ya mazingira. Ripoti yako inahifadhiwa bila jina.
     98. Angalia zaidi
     2. Kataa masharti
     ```
   - User inputs `98` (Angalia zaidi).

3. **Screen 3 (Consent Page 2)**:
   - Menu:
     ```text
     CON Matumizi ya data yamezuiliwa kwa mipango ya ufuatiliaji. Kwa kuendelea, unakubali masharti haya.
     1. Kubali na Anza kuripoti
     0. Rudi nyuma
     ```
   - User inputs `1` (Kubali).

---

## 3. Requirements (Scope Guardrails)

### Must-Have
* **Multi-Page State Support**: Track consent paging depth based on `98` and `0` inputs.
* **Non-Blocking Flow**: Users must be able to reply `1` (Accept) on Screen 2 directly OR on Screen 3 after paging, and successfully start reporting.
* **Back Button support (`0`)**: Allow users to go back to Consent Page 1 from Consent Page 2.
* **Input Stream Cleansing**: Before traversing dynamic questions, strip out any paging segments (`98` / `0`) from the inputs array to prevent index shifting on answers.

### Out of Scope
* Dynamically paging the terms text from a database table (hardcoded pages in the router config are acceptable for this static legal gate).

---

## 4. Acceptance Criteria

| ID     | Scenario | Expected Output |
| ------ | -------- | --------------- |
| AC-001 | User inputs `1*1` (English -> Accept directly) | Proceed to dynamic questions |
| AC-002 | User inputs `1*98` (English -> View More) | Display Consent Page 2 |
| AC-003 | User inputs `1*98*1` (English -> View More -> Accept) | Proceed to dynamic questions |
| AC-004 | User inputs `1*98*0` (English -> View More -> Back) | Display Consent Page 1 |
| AC-005 | User inputs `1*98*0*1` (English -> View More -> Back -> Accept) | Proceed to dynamic questions |
| AC-006 | User inputs Swahili options (`2*98*1`) | Proceed to dynamic questions using Swahili translations |

---

## 5. Epic & Ballpark Estimation

* **Task**: Refactor `ussd_router.py` to process inputs sequence for consent paging, update tests.
* **Complexity**: Simple/Medium.
* **Ballpark Estimate**: 0.5 dev days.

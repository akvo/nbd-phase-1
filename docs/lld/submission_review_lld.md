# LLD — Submission Review Screen (USSD & WhatsApp)

> **Stage 3 of 3 — Documentation Hierarchy**
> Owner: Winston (Architect) / Amelia (Developer) | Target Location: `docs/lld/submission_review_lld.md`
> Initiative/Epic: Submission Review Screen

---

## 1. USSD Flow Implementation (`backend/app/routers/ussd_router.py`)

### 1.1 Redo Session Handling
Since USSD via Africa's Talking sends the full history of session inputs concatenated by `*`, when a user selects `"2"` (Redo), the subsequent string continues to grow. To clear previous answers and restart the form, we will check if the parts array contains the redo choice:
- If a redo action `"2"` is detected in the input trail, we split the trail and discard everything before the redo action, restarting the traversal from the language selection step.

### 1.2 Final Review Screen Prompt
When the question traversal loop successfully completes (all active questions answered), we check if a final confirmation choice is present in `parts[input_idx]`:
- **If not present**:
  - Traverse the answers to compile a summary string of the questions and chosen labels/options.
  - Return a `CON` response:
    ```
    CON Confirm details / Hakikisha maelezo:
    [Summary text of questions and answers]
    1. Confirm / Thibitisha
    2. Redo / Anza tena
    ```
- **If present**:
  - Read `user_input = parts[input_idx]`.
  - If `"1"` (Confirm): Save the `Datapoint` and `Answer` models, commit to the database, and return `END Thank you...`.
  - If `"2"` (Redo): Do not save anything. Restart the form flow.

---

## 2. WhatsApp Flow Implementation (`backend/app/services/whatsapp_service.py`)

### 2.1 Transition to `CONFIRMATION` State
In `process_whatsapp_message`, when `next_q` is `None` (all dynamic questions completed):
- Instead of calling `_save_report` and deleting the session immediately, transition the session state:
  ```python
  session.state = "CONFIRMATION"
  db.commit()
  ```
- Send a summary message detailing the reporter's answers, followed by the confirmation choices:
  ```
  Please review your report details:
  [Summary of question-answer pairs]

  Reply *1* to Confirm
  Reply *2* to Redo
  ```

### 2.2 Processing `CONFIRMATION` State Input
Add a new state handling block in `process_whatsapp_message` for `state == "CONFIRMATION"`:
- Read `text_body`.
- If `text_body == "1"`:
  - Save report: call `_save_report(...)`.
  - Delete session: `db.delete(session)`.
  - Commit: `db.commit()`.
  - Send the thank-you message.
- If `text_body == "2"`:
  - Clear answers: `session.answers = {}`.
  - Reset state to `DYNAMIC_QUESTION`.
  - Find the first active question and set `session.current_question_id`.
  - Commit: `db.commit()`.
  - Send confirmation of reset and prompt the first question.
- If any other input is received, re-send the summary and confirmation options.

---

## 3. Translation Utilities
Ensure Kiswahili translations are correctly used for the final prompts. Add translation mappings for:
- "Confirm details" / "Hakikisha maelezo"
- "Confirm" / "Thibitisha"
- "Redo" / "Anza tena"

---

## 4. Verification & Testing Plan

### Automated Pytest Suite
Update/create tests in `backend/tests/` to verify:
1. **USSD Review Flow**:
   - Send inputs matching all questions. Verify that the final response is `CON` containing the summary and choices.
   - Send final `1` input. Verify that the `Datapoint` is created in the database and response is `END`.
   - Send final `2` input. Verify that no `Datapoint` is created.
2. **WhatsApp Review Flow**:
   - Move WhatsApp session to `CONFIRMATION`. Verify the summary prompt is sent.
   - Send `1`. Verify session is deleted and `Datapoint` is created.
   - Send `2`. Verify session answers are cleared and state transitions back to `DYNAMIC_QUESTION`.

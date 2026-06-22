from typing import List, Dict, Any
from app.models.form import Question


def is_question_active(question: Question, answers: Dict[str, Any]) -> bool:
    """Evaluate if a question is active based on its dependency skip-logic."""
    if not question.dependency:
        return True

    # dependency_rule defaults to "AND" if not provided or empty
    rule = (question.dependency_rule or "AND").upper()
    matches = []

    for dep in question.dependency:
        dep_id = dep.get("id")
        dep_val = dep.get("value")

        # Check in answers using string ID or original key
        ans = answers.get(dep_id)
        if ans is None and dep_id is not None:
            ans = answers.get(str(dep_id))

        if ans is None:
            matches.append(False)
            continue

        # Check if the answer matches the dependency value
        # Handle list options or single option values
        # (e.g. string/int comparison)
        if isinstance(ans, list):
            match = any(str(v) == str(dep_val) for v in ans)
        else:
            match = str(ans) == str(dep_val)
        matches.append(match)

    if not matches:
        return True

    if rule == "OR":
        return any(matches)
    return all(matches)


def get_active_questions(
    questions: List[Question], answers: Dict[str, Any]
) -> List[Question]:
    """
    Filter the list of questions returning only those that satisfy skip logic.
    """
    active = []
    for q in questions:
        if is_question_active(q, answers):
            active.append(q)
    return active

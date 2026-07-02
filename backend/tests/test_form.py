import jwt
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User
from app.config.auth import JWT_SECRET, JWT_ALGORITHM

client = TestClient(app)


def get_auth_headers(
    db_session, email="admin_form_test@nbd.org", role="Admin"
):
    user = db_session.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, role=role, is_active=True)
        db_session.add(user)
        db_session.commit()
    token = jwt.encode({"email": email}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def test_create_form(db_session):
    headers = get_auth_headers(db_session)
    form_data = {
        "name": "Physico-Chemical Sampling Form",
        "type": 1,
        "status": 1,
    }
    response = client.post("/api/v1/forms", json=form_data, headers=headers)
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["name"] == "Physico-Chemical Sampling Form"
    assert res_data["version"] == 1
    assert "uuid" in res_data
    form_id = res_data["id"]

    # Get form
    response = client.get(f"/api/v1/forms/{form_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Physico-Chemical Sampling Form"


def test_create_full_blueprint_hierarchy(db_session):
    headers = get_auth_headers(db_session)
    # 1. Create a form
    form_data = {"name": "Wetland Survey", "type": 1, "status": 1}
    form_res = client.post("/api/v1/forms", json=form_data, headers=headers)
    assert form_res.status_code == 201
    form_id = form_res.json()["id"]

    # 2. Create a Question Group under this form
    group_data = {
        "form_id": form_id,
        "name": "water_quality",
        "label": "Water Quality Parameters",
        "order": 1,
        "repeatable": False,
    }
    group_res = client.post(
        "/api/v1/question-groups", json=group_data, headers=headers
    )
    assert group_res.status_code == 201
    group_id = group_res.json()["id"]

    # 3. Create a Question under the group
    question_data = {
        "form_id": form_id,
        "question_group_id": group_id,
        "name": "ph_level",
        "label": "pH Level",
        "order": 1,
        "type": "number",
        "required": True,
        "validation_min": 2.0,
        "validation_max": 10.0,
    }
    q_res = client.post(
        "/api/v1/questions", json=question_data, headers=headers
    )
    assert q_res.status_code == 201
    q_id = q_res.json()["id"]

    # 4. Create an Option under the question (choices type)
    option_data = {
        "question_id": q_id,
        "order": 1,
        "label": "Neutral pH",
        "value": "neutral",
    }
    opt_res = client.post("/api/v1/options", json=option_data, headers=headers)
    assert opt_res.status_code == 201


def test_soft_deletion_and_conditional_uniqueness(db_session):
    headers = get_auth_headers(db_session)
    # Create Form
    form_res = client.post(
        "/api/v1/forms",
        json={"name": "Constraint Form", "type": 1},
        headers=headers,
    )
    form_id = form_res.json()["id"]

    # Create Group 1
    g1_res = client.post(
        "/api/v1/question-groups",
        json={"form_id": form_id, "name": "bio_indicators"},
        headers=headers,
    )
    assert g1_res.status_code == 201
    g1_id = g1_res.json()["id"]

    # Try creating duplicate active Group with same name under Form -> Fail
    g2_res = client.post(
        "/api/v1/question-groups",
        json={"form_id": form_id, "name": "bio_indicators"},
        headers=headers,
    )
    assert g2_res.status_code == 400

    # Soft delete Group 1
    del_res = client.delete(
        f"/api/v1/question-groups/{g1_id}", headers=headers
    )
    assert del_res.status_code == 200

    # Try recreating Group now that Group 1 is deleted -> Succeed
    g3_res = client.post(
        "/api/v1/question-groups",
        json={"form_id": form_id, "name": "bio_indicators"},
        headers=headers,
    )
    assert g3_res.status_code == 201


def test_publish_form_snapshot(db_session):
    headers = get_auth_headers(db_session)
    # Create form, group, question
    form_res = client.post(
        "/api/v1/forms",
        json={"name": "Publish Form", "type": 1},
        headers=headers,
    )
    form_id = form_res.json()["id"]

    g_res = client.post(
        "/api/v1/question-groups",
        json={"form_id": form_id, "name": "grp"},
        headers=headers,
    )
    g_id = g_res.json()["id"]

    client.post(
        "/api/v1/questions",
        json={
            "form_id": form_id,
            "question_group_id": g_id,
            "name": "q1",
            "label": "Question 1",
            "type": "text",
        },
        headers=headers,
    )

    # Publish Form
    pub_res = client.post(f"/api/v1/forms/{form_id}/publish", headers=headers)
    assert pub_res.status_code == 200
    res_data = pub_res.json()
    assert res_data["version"] == 1
    assert "schema" in res_data
    # The snapshot contains the dynamic layout
    assert len(res_data["schema"]["question_group"]) == 1


def test_form_update_move_question_and_delete_group(db_session):
    headers = get_auth_headers(db_session)

    # 1. Create a form
    form_res = client.post(
        "/api/v1/forms",
        json={"name": "Form Move Test", "type": 1},
        headers=headers,
    )
    assert form_res.status_code == 201
    form_id = form_res.json()["id"]

    # 2. Create Group A
    g_a_res = client.post(
        "/api/v1/question-groups",
        json={"form_id": form_id, "name": "group_a", "label": "Group A"},
        headers=headers,
    )
    assert g_a_res.status_code == 201
    g_a_id = g_a_res.json()["id"]

    # 3. Create Group B
    g_b_res = client.post(
        "/api/v1/question-groups",
        json={"form_id": form_id, "name": "group_b", "label": "Group B"},
        headers=headers,
    )
    assert g_b_res.status_code == 201
    g_b_id = g_b_res.json()["id"]

    # 4. Create Question under Group A
    q_res = client.post(
        "/api/v1/questions",
        json={
            "form_id": form_id,
            "question_group_id": g_a_id,
            "name": "water_color",
            "label": "Water Color",
            "type": "text",
        },
        headers=headers,
    )
    assert q_res.status_code == 201
    q_id = q_res.json()["id"]

    # 5. Move Question to Group B and Delete Group A via PUT forms/{form_id}
    # Payload excludes Group A, and puts "water_color" question under Group B
    update_data = {
        "name": "Form Move Test",
        "type": 1,
        "languages": ["en"],
        "translations": [],
        "question_group": [
            {
                "id": g_b_id,
                "name": "group_b",
                "label": "Group B",
                "question": [
                    {
                        "id": q_id,
                        "name": "water_color",
                        "label": "Water Color",
                        "type": "text",
                    }
                ],
            }
        ],
    }

    put_res = client.put(
        f"/api/v1/forms/{form_id}", json=update_data, headers=headers
    )
    assert put_res.status_code == 200

    # 6. Verify Group A is soft-deleted
    from app.models.form import QuestionGroup, Question

    group_a_db = (
        db_session.query(QuestionGroup)
        .filter(QuestionGroup.id == g_a_id)
        .first()
    )
    assert group_a_db is not None
    assert group_a_db.deleted_at is not None

    # 7. Verify Question "water_color" is active and relocated to Group B
    q_db = db_session.query(Question).filter(Question.id == q_id).first()
    assert q_db is not None
    assert q_db.deleted_at is None
    assert q_db.question_group_id == g_b_id


def test_form_update_group_and_question_reordering(db_session):
    headers = get_auth_headers(db_session)

    # 1. Create a form
    form_res = client.post(
        "/api/v1/forms",
        json={"name": "Form Reorder Test", "type": 1},
        headers=headers,
    )
    assert form_res.status_code == 201
    form_id = form_res.json()["id"]

    # 2. Create Group A and Group B
    g_a_res = client.post(
        "/api/v1/question-groups",
        json={
            "form_id": form_id,
            "name": "group_a",
            "label": "Group A",
            "order": 1,
        },
        headers=headers,
    )
    g_b_res = client.post(
        "/api/v1/question-groups",
        json={
            "form_id": form_id,
            "name": "group_b",
            "label": "Group B",
            "order": 2,
        },
        headers=headers,
    )
    g_a_id = g_a_res.json()["id"]
    g_b_id = g_b_res.json()["id"]

    # 3. Create Questions under Group A
    q1_res = client.post(
        "/api/v1/questions",
        json={
            "form_id": form_id,
            "question_group_id": g_a_id,
            "name": "q1",
            "label": "Question 1",
            "type": "text",
            "order": 1,
        },
        headers=headers,
    )
    q2_res = client.post(
        "/api/v1/questions",
        json={
            "form_id": form_id,
            "question_group_id": g_a_id,
            "name": "q2",
            "label": "Question 2",
            "type": "text",
            "order": 2,
        },
        headers=headers,
    )
    q1_id = q1_res.json()["id"]
    q2_id = q2_res.json()["id"]

    # 4. Perform PUT to swap group order, and swap question order in Group A
    update_data = {
        "name": "Form Reorder Test",
        "type": 1,
        "languages": ["en"],
        "translations": [],
        "question_group": [
            {
                "id": g_b_id,
                "name": "group_b",
                "label": "Group B",
                "order": 1,
                "question": [],
            },
            {
                "id": g_a_id,
                "name": "group_a",
                "label": "Group A",
                "order": 2,
                "question": [
                    {
                        "id": q2_id,
                        "name": "q2",
                        "label": "Question 2",
                        "type": "text",
                        "order": 1,
                    },
                    {
                        "id": q1_id,
                        "name": "q1",
                        "label": "Question 1",
                        "type": "text",
                        "order": 2,
                    },
                ],
            },
        ],
    }

    put_res = client.put(
        f"/api/v1/forms/{form_id}", json=update_data, headers=headers
    )
    assert put_res.status_code == 200

    # 5. Verify database values have been updated correctly
    from app.models.form import QuestionGroup, Question

    g_a_db = (
        db_session.query(QuestionGroup)
        .filter(QuestionGroup.id == g_a_id)
        .first()
    )
    g_b_db = (
        db_session.query(QuestionGroup)
        .filter(QuestionGroup.id == g_b_id)
        .first()
    )
    assert g_a_db.order == 2
    assert g_b_db.order == 1

    q1_db = db_session.query(Question).filter(Question.id == q1_id).first()
    q2_db = db_session.query(Question).filter(Question.id == q2_id).first()
    assert q1_db.order == 1  # Updated to index order in the payload
    assert q2_db.order == 0  # Updated to index order in the payload

from unittest.mock import patch
from sqlalchemy.orm import Session
from app.models.user import User
from app.scripts.create_user import main


@patch("app.scripts.create_user.input")
@patch("app.scripts.create_user.getpass.getpass")
@patch("app.scripts.create_user.SessionLocal")
def test_create_user_script_success(
    mock_session_local, mock_getpass, mock_input, db_session: Session
):
    # Setup SessionLocal mock to return our test db_session
    mock_session_local.return_value = db_session

    # Clean existing users
    db_session.query(User).delete()
    db_session.commit()

    # Configure mock responses:
    # 1st input: Email
    # 2nd input: Role Choice ("1" for Admin)
    # 3rd input: Organization
    mock_input.side_effect = ["test_user@nbd-wetland.org", "1", "My Org"]

    # getpass side effects:
    # 1st getpass: Password
    # 2nd getpass: Confirm Password
    mock_getpass.side_effect = ["securepassword123", "securepassword123"]

    # Run main script function
    main()

    # Assert user created in db
    created_user = (
        db_session.query(User)
        .filter(User.email == "test_user@nbd-wetland.org")
        .first()
    )
    assert created_user is not None
    assert created_user.role == "Admin"
    assert created_user.organization == "My Org"
    assert created_user.password_hash is not None
    assert created_user.is_active is True

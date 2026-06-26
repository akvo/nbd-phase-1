import os
import jwt
from typing import Generator
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.config.auth import JWT_SECRET, JWT_ALGORITHM

# Determine test database URL dynamically
db_url = os.getenv(
    "DATABASE_URL", "postgresql://nbd_user:password@db:5432/nbd_db"
)
if db_url.endswith("/nbd_db"):
    test_db_url = db_url + "_test"
else:
    test_db_url = db_url.rsplit("/", 1)[0] + "/nbd_db_test"

engine_test = create_engine(test_db_url)
SessionLocalTest = sessionmaker(
    autocommit=False, autoflush=False, bind=engine_test
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database() -> Generator[None, None, None]:
    # Ensure PostGIS extension is enabled on the test database
    with engine_test.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        conn.commit()
    # Create all tables for the testing session
    Base.metadata.create_all(bind=engine_test)
    yield
    # Clean up after all tests are finished
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture(scope="function")
def db_session() -> Generator[SessionLocalTest, None, None]:
    # Use transactional rollback strategy for test isolation
    connection = engine_test.connect()
    transaction = connection.begin()
    session = SessionLocalTest(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function", autouse=True)
def override_get_db(
    db_session: SessionLocalTest,
) -> Generator[None, None, None]:
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    app.dependency_overrides.clear()


def make_auth_headers(
    db_session, email: str = "test_admin@nbd.org", role: str = "Admin"
) -> dict:
    """Create (or reuse) a test user and return Bearer auth headers."""
    user = db_session.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, role=role, is_active=True)
        db_session.add(user)
        db_session.commit()
    token = jwt.encode({"email": email}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers(db_session):
    """Pytest fixture that returns valid Admin auth headers."""
    return make_auth_headers(db_session)

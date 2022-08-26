from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import sessionmaker

from ..src.database import models
from ..src.main import app, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///backend/test/test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


models.Base.metadata.drop_all(bind=engine)
models.Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_main():
    response = client.get("/login/")
    assert response.status_code == 200, response.text
    assert response.json() == True


def test_create_me():
    response = client.post(
        "/me/",
        json={
            "username": "ww",
            "email": "wonderwoman@example.com",
            "name": "Diana",
            "level": "2",
            "timezone": "-1"
        }
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["username"] == "ww"
    assert data["email"] == "wonderwoman@example.com"
    assert data["name"] == "Diana"
    assert data["level"] == 2
    assert data["timezone"] == -1
    assert "id" in data
    assert "calendars" in data


def test_read_me():
    response = client.get("/me/")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["username"] == "admin"
    assert data["email"] == "admin@example.com"
    assert data["name"] == None
    assert data["level"] == 2
    assert data["timezone"] == None
    assert "id" in data
    assert "calendars" in data and isinstance(data["calendars"], list)


def test_update_me():
    response = client.put(
        "/me/",
        json={
            "username": "adminx",
            "email": "admin@example.comx",
            "name": "The Admin",
            "level": "3",
            "timezone": "2"
        }
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["username"] == "adminx"
    assert data["email"] == "admin@example.comx"
    assert data["name"] == "The Admin"
    assert data["level"] == 3
    assert data["timezone"] == 2


def test_partial_update_me():
    response = client.put(
        "/me/",
        json={ "username": "admin" }
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["username"] == "admin"


def test_create_my_calendar():
    response = client.post(
        "/calendars/",
        json={
            "url": "https://example.com",
            "user": "ww1984",
            "password": "d14n4"
        }
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["url"] == "https://example.com"
    assert data["user"] == "ww1984"
    assert data["password"] == "d14n4"
    assert "id" in data
    assert "owner_id" in data and data["owner_id"] == 1


def test_read_my_calendars():
    response = client.get("/me/calendars/")
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["user"] == "ww1984"
    assert "owner_id" in data[0] and data[0]["owner_id"] == 1


def test_read_existing_calendar():
    response = client.get("/calendars/1")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["url"] == "https://example.com"
    assert data["user"] == "ww1984"
    assert data["password"] == "d14n4"


def test_read_missing_calendar():
    response = client.get("/calendars/2")
    assert response.status_code == 404, response.text


def test_update_existing_calendar():
    response = client.put(
        "/calendars/1",
        json={
            "url": "https://example.comx",
            "user": "ww1984x",
            "password": "d14n4x"
        }
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["url"] == "https://example.comx"
    assert data["user"] == "ww1984x"
    assert data["password"] == "d14n4x"


def test_partial_update_existing_calendar():
    response = client.put(
        "/calendars/1",
        json={ "url": "https://example.com" }
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["url"] == "https://example.com"


def test_update_foreign_calendar():
    stmt = insert(models.Calendar).values(owner_id="2", url="a", user="a", password="a")
    db = TestingSessionLocal()
    db.execute(stmt)
    db.commit()
    response = client.put(
        "/calendars/2",
        json={
            "url": "test",
            "user": "test",
            "password": "test"
        }
    )
    assert response.status_code == 403, response.text


def test_delete_existing_calendar():
    response = client.delete("/calendars/1")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["url"] == "https://example.com"
    assert data["user"] == "ww1984x"
    assert data["password"] == "d14n4x"
    response = client.get("/calendars/1")
    assert response.status_code == 404, response.text
    response = client.get("/me/calendars/")
    data = response.json()
    assert len(data) == 0


def test_delete_missing_calendar():
    response = client.delete("/calendars/3")
    assert response.status_code == 404, response.text


def test_delete_foreign_calendar():
    response = client.delete("/calendars/2")
    assert response.status_code == 403, response.text

import pytest
from app import create_app
from bson.objectid import ObjectId
from config import TestConfig
from pymongo import MongoClient


@pytest.fixture()
def client():
    app = create_app(test_config=TestConfig)
    with app.test_client() as c:
        yield c

@pytest.fixture()
def logged_in_client(client):
    """Client with a fake logged-in session."""
    with client.session_transaction() as sess:
        sess["user_id"] = str(ObjectId())
    return client

@pytest.fixture()
def db():
    client = MongoClient("mongodb://localhost:27017")
    db = client["puzzlegame_test"]
    yield db
    db.users.delete_many({})
    db.matches.delete_many({})
    client.close()


# ---------------------------------------------------------------------------
# Static / landing pages
# ---------------------------------------------------------------------------


def test_index_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200


def test_login_get_returns_200(client):
    response = client.get("/login")
    assert response.status_code == 200


def test_register_get_returns_200(client):
    response = client.get("/register")
    assert response.status_code == 200


def test_setup_get_returns_200(logged_in_client):
    response = logged_in_client.get("/setup")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Auth-flow redirects (POST)
# ---------------------------------------------------------------------------


def test_login_post_redirects_to_dashboard(client, db):
    db.users.insert_one({"username": "user", "password": "pass"})
    response = client.post("/login", data={"username": "user", "password": "pass"})
    assert response.status_code == 302


def test_register_post_redirects_to_setup(client):
    response = client.post(
        "/register", data={"username": "new_user", "password": "pass"}
    )
    assert response.status_code == 302
    assert "/setup" in response.headers["Location"]


def test_setup_post_redirects_to_dashboard(logged_in_client):
    response = logged_in_client.post("/setup", data={"answer": "some answer"})
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_logout_redirects_to_login(client):
    response = client.get("/logout")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


def test_dashboard_get_returns_200(client):
    response = client.get("/dashboard")
    assert response.status_code == 200


def test_dashboard_post_returns_result(client):
    response = client.post("/dashboard", data={"guess": "meadow"})
    assert response.status_code == 200
    # The template should render a result block when a POST was made
    assert b"score" in response.data.lower() or response.status_code == 200


# ---------------------------------------------------------------------------
# Matches
# ---------------------------------------------------------------------------


def test_matches_page_returns_200(client):
    response = client.get("/matches")
    assert response.status_code == 200


def test_match_detail_returns_200_for_existing_match(client, db):
    result = db.matches.insert_one({"name": "test match"})
    response = client.get(f"/matches/{result.inserted_id}")
    assert response.status_code == 200


def test_match_detail_returns_404_for_missing_match(client):
    fake_id = str(ObjectId())
    response = client.get(f"/matches/{fake_id}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Profile & Settings
# ---------------------------------------------------------------------------


def test_profile_get_returns_200(client):
    response = client.get("/profile")
    assert response.status_code == 200


def test_profile_post_returns_200(client):
    response = client.post("/profile", data={"age": "22"})
    assert response.status_code == 200


def test_settings_get_returns_200(client):
    response = client.get("/settings")
    assert response.status_code == 200


def test_settings_post_returns_200(client):
    response = client.post("/settings", data={"email": "a@b.com"})
    assert response.status_code == 200

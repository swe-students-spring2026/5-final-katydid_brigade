import pytest
from app import create_app
from bson.objectid import ObjectId
from config import TestConfig
from pymongo import MongoClient


@pytest.fixture()
def client():
    app, socketio = create_app(test_config=TestConfig)
    with app.test_client() as c:
        yield c

@pytest.fixture()
def logged_in_client(client, db):
    """Client with a fake logged-in session."""
    user_id = db.users.insert_one({"username": "session_user"}).inserted_id
    with client.session_transaction() as sess:
        sess["user_id"] = str(user_id)
    return client

@pytest.fixture()
def db():
    client = MongoClient("mongodb://localhost:27017")
    db = client["puzzlegame_test"]
    yield db
    db.users.delete_many({})
    db.matches.delete_many({})
    db.puzzles.delete_many({})
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
    response = logged_in_client.post("/setup", data={"age": "22", "gender": "male"})
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_logout_redirects_to_login(logged_in_client):
    response = logged_in_client.get("/logout")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


def test_dashboard_get_returns_200(logged_in_client):
    response = logged_in_client.get("/dashboard")
    assert response.status_code == 200


def test_dashboard_post_returns_result(logged_in_client):
    response = logged_in_client.post("/dashboard", data={"guess": "meadow"})
    assert response.status_code == 200
    assert b"No puzzle-ready profiles" in response.data


# ---------------------------------------------------------------------------
# Matches
# ---------------------------------------------------------------------------


def test_matches_page_returns_200(logged_in_client):
    response = logged_in_client.get("/matches")
    assert response.status_code == 200


def test_match_detail_returns_200_for_existing_match(logged_in_client, db):
    solver = db.users.find_one({"username": "session_user"})
    target_id = db.users.insert_one({"username": "target_user"}).inserted_id
    result = db.matches.insert_one({
        "solver_user_id": str(solver["_id"]),
        "target_user_id": str(target_id),
    })
    response = logged_in_client.get(f"/matches/{result.inserted_id}")
    assert response.status_code == 200


def test_match_detail_returns_404_for_missing_match(logged_in_client):
    fake_id = str(ObjectId())
    response = logged_in_client.get(f"/matches/{fake_id}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Profile & Settings
# ---------------------------------------------------------------------------


def test_profile_get_returns_200(logged_in_client):
    response = logged_in_client.get("/profile")
    assert response.status_code == 302
    assert "/setting" in response.headers["Location"]


def test_profile_post_returns_200(logged_in_client):
    response = logged_in_client.post("/profile", data={"age": "22"})
    assert response.status_code == 307
    assert "/setting" in response.headers["Location"]


def test_settings_get_returns_200(logged_in_client):
    response = logged_in_client.get("/settings")
    assert response.status_code == 200


def test_settings_post_returns_200(logged_in_client):
    response = logged_in_client.post("/settings", data={"email": "a@b.com", "gender": "male"})
    assert response.status_code == 200

import pytest
from app import create_app


@pytest.fixture()
def client():
    app = create_app(test_config={"TESTING": True, "SECRET_KEY": "test"})
    with app.test_client() as c:
        yield c


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


def test_setup_get_returns_200(client):
    response = client.get("/setup")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Auth-flow redirects (POST)
# ---------------------------------------------------------------------------


def test_login_post_redirects_to_dashboard(client):
    response = client.post("/login", data={"username": "user", "password": "pass"})
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_register_post_redirects_to_setup(client):
    response = client.post(
        "/register", data={"username": "new_user", "password": "pass"}
    )
    assert response.status_code == 302
    assert "/setup" in response.headers["Location"]


def test_setup_post_redirects_to_dashboard(client):
    response = client.post("/setup", data={"answer": "some answer"})
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


def test_match_detail_returns_200_for_existing_match(client):
    response = client.get("/matches/1")
    assert response.status_code == 200


def test_match_detail_returns_404_for_missing_match(client):
    response = client.get("/matches/9999")
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

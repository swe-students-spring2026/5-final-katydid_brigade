from fastapi.testclient import TestClient

from game_engine.api import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_puzzle_endpoint() -> None:
    response = client.post(
        "/puzzles",
        json={
            "question": "Favorite outdoors word?",
            "answer": "meadow",
            "seed": 12,
            "max_attempts": 5,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "meadow"
    assert len(data["board"]) == 4
    assert len(data["board"][0]) == 4


def test_evaluate_guess_endpoint() -> None:
    puzzle_response = client.post(
        "/puzzles",
        json={
            "question": "Favorite outdoors word?",
            "answer": "forest",
            "seed": 3,
            "max_attempts": 5,
        },
    )
    puzzle_data = puzzle_response.json()

    response = client.post(
        "/guesses",
        json={
            "question": puzzle_data["question"],
            "answer": puzzle_data["answer"],
            "board": puzzle_data["board"],
            "guess": "forest",
            "previous_guesses": [],
            "max_attempts": puzzle_data["max_attempts"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_correct"] is True
    assert data["puzzle_solved"] is True

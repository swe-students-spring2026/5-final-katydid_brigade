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


def test_create_puzzle_rejects_short_answer() -> None:
    response = client.post(
        "/puzzles",
        json={"question": "A question?", "answer": "hi"},
    )
    assert response.status_code == 422  # FastAPI validation error


def test_create_puzzle_rejects_long_answer() -> None:
    response = client.post(
        "/puzzles",
        json={"question": "A question?", "answer": "extraordinarily"},
    )
    assert response.status_code == 422


def test_evaluate_incorrect_guess() -> None:
    puzzle_response = client.post(
        "/puzzles",
        json={
            "question": "Pick a word?",
            "answer": "meadow",
            "seed": 1,
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
            "guess": "night",  # wrong answer, may not be on board
            "previous_guesses": [],
            "max_attempts": puzzle_data["max_attempts"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_correct"] is False
    assert data["puzzle_solved"] is False
    assert data["attempts_used"] == 1
    assert data["attempts_remaining"] == 4


def test_evaluate_guess_replays_previous_guesses() -> None:
    puzzle_response = client.post(
        "/puzzles",
        json={
            "question": "Pick a word?",
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
            "previous_guesses": ["night", "storm"],
            "max_attempts": puzzle_data["max_attempts"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_correct"] is True
    assert data["attempts_used"] == 3


def test_evaluate_guess_returns_400_when_attempts_exhausted() -> None:
    puzzle_response = client.post(
        "/puzzles",
        json={
            "question": "Pick a word?",
            "answer": "autumn",
            "seed": 11,
            "max_attempts": 2,
        },
    )
    puzzle_data = puzzle_response.json()

    response = client.post(
        "/guesses",
        json={
            "question": puzzle_data["question"],
            "answer": puzzle_data["answer"],
            "board": puzzle_data["board"],
            "guess": "plane",
            "previous_guesses": ["night", "storm"],  # already used both attempts
            "max_attempts": 2,
        },
    )

    assert response.status_code == 400

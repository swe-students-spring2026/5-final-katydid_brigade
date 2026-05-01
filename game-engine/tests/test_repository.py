from dataclasses import dataclass
from datetime import datetime, timezone

from game_engine import BogglePuzzle, MongoCompatibleGameRepository, PuzzleSession


@dataclass
class FakeInsertResult:
    inserted_id: str


class FakeCollection:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.documents: list[dict] = []

    def insert_one(self, document: dict) -> FakeInsertResult:
        inserted_id = f"{self.prefix}-{len(self.documents) + 1}"
        stored = dict(document)
        stored["_id"] = inserted_id
        self.documents.append(stored)
        return FakeInsertResult(inserted_id=inserted_id)


def test_save_puzzle_serializes_board_for_mongodb() -> None:
    repository = MongoCompatibleGameRepository(
        puzzles_collection=FakeCollection("puzzle"),
        attempts_collection=FakeCollection("attempt"),
        matches_collection=FakeCollection("match"),
    )
    puzzle = BogglePuzzle.from_answer(
        question="Where would you go on a weekend trip?",
        answer="harbor",
        seed=9,
    )
    created_at = datetime(2026, 4, 28, tzinfo=timezone.utc)

    record = repository.save_puzzle(
        owner_user_id="user-17",
        puzzle=puzzle,
        created_at=created_at,
    )

    assert record.puzzle_id == "puzzle-1"
    assert isinstance(record.board, list)
    assert isinstance(record.board[0], list)


def test_save_result_and_create_match_for_correct_guess() -> None:
    puzzles = FakeCollection("puzzle")
    attempts = FakeCollection("attempt")
    matches = FakeCollection("match")
    repository = MongoCompatibleGameRepository(
        puzzles_collection=puzzles,
        attempts_collection=attempts,
        matches_collection=matches,
    )
    puzzle = BogglePuzzle.from_answer(
        question="Pick a place word",
        answer="meadow",
        seed=4,
    )
    saved_puzzle = repository.save_puzzle(owner_user_id="target-2", puzzle=puzzle)
    session = PuzzleSession(puzzle=puzzle)
    result = session.submit_guess("meadow")

    attempt, match = repository.save_result_and_create_match(
        puzzle_id=saved_puzzle.puzzle_id,
        guesser_user_id="solver-8",
        target_user_id="target-2",
        result=result,
    )

    assert attempt.attempt_id == "attempt-1"
    assert match is not None
    assert match.match_id == "match-1"
    assert matches.documents[0]["solver_user_id"] == "solver-8"
    assert matches.documents[0]["target_user_id"] == "target-2"


def test_save_result_without_match_for_incorrect_guess() -> None:
    repository = MongoCompatibleGameRepository(
        puzzles_collection=FakeCollection("puzzle"),
        attempts_collection=FakeCollection("attempt"),
        matches_collection=FakeCollection("match"),
    )
    puzzle = BogglePuzzle.from_answer(
        question="Favorite color word?",
        answer="violet",
        seed=6,
    )
    session = PuzzleSession(puzzle=puzzle)
    result = session.submit_guess("planet")

    attempt, match = repository.save_result_and_create_match(
        puzzle_id="puzzle-10",
        guesser_user_id="solver-11",
        target_user_id="target-12",
        result=result,
    )

    assert attempt.is_correct is False
    assert match is None

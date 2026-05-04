"""MongoDB-friendly persistence helpers for the Boggle game engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from .boggle import BogglePuzzle, GuessResult


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InsertOneResultLike(Protocol):
    """Small protocol matching the part of pymongo's insert result that we use."""

    inserted_id: Any


class InsertableCollection(Protocol):
    """Small protocol for mongo-like collections used by the repository."""

    def insert_one(self, document: dict[str, Any]) -> InsertOneResultLike:
        ...


@dataclass(frozen=True)
class PuzzleRecord:
    """Serializable puzzle payload for the puzzles collection."""

    owner_user_id: str
    question: str
    answer: str | None
    board: list[list[str]]
    max_attempts: int
    questions: list[str] | None = None
    answers: list[str] | None = None
    puzzle_type: str = "boggle"
    created_at: datetime | None = None
    puzzle_id: Any | None = None

    @classmethod
    def from_puzzle(
        cls,
        owner_user_id: str,
        puzzle: BogglePuzzle,
        created_at: datetime | None = None,
        puzzle_id: Any | None = None,
    ) -> "PuzzleRecord":
        return cls(
            owner_user_id=owner_user_id,
            question=puzzle.question,
            answer=puzzle.answer,
            board=[[cell for cell in row] for row in puzzle.board],
            max_attempts=puzzle.max_attempts,
            questions=list(puzzle.questions),
            answers=list(puzzle.answers),
            created_at=created_at or _utc_now(),
            puzzle_id=puzzle_id,
        )

    def to_document(self) -> dict[str, Any]:
        document = {
            "owner_user_id": self.owner_user_id,
            "question": self.question,
            "answer": self.answer,
            "questions": self.questions or [],
            "answers": self.answers or ([] if self.answer is None else [self.answer]),
            "board": self.board,
            "max_attempts": self.max_attempts,
            "puzzle_type": self.puzzle_type,
            "created_at": self.created_at or _utc_now(),
        }
        if self.puzzle_id is not None:
            document["_id"] = self.puzzle_id
        return document


@dataclass(frozen=True)
class AttemptRecord:
    """Serializable guess-attempt payload for the attempts collection."""

    puzzle_id: Any
    guesser_user_id: str
    guess: str
    is_correct: bool
    is_on_board: bool
    attempts_used: int
    attempts_remaining: int
    puzzle_solved: bool
    created_at: datetime | None = None
    attempt_id: Any | None = None

    @classmethod
    def from_guess_result(
        cls,
        puzzle_id: Any,
        guesser_user_id: str,
        result: GuessResult,
        created_at: datetime | None = None,
        attempt_id: Any | None = None,
    ) -> "AttemptRecord":
        return cls(
            puzzle_id=puzzle_id,
            guesser_user_id=guesser_user_id,
            guess=result.guess,
            is_correct=result.is_correct,
            is_on_board=result.is_on_board,
            attempts_used=result.attempts_used,
            attempts_remaining=result.attempts_remaining,
            puzzle_solved=result.puzzle_solved,
            created_at=created_at or _utc_now(),
            attempt_id=attempt_id,
        )

    def to_document(self) -> dict[str, Any]:
        document = {
            "puzzle_id": self.puzzle_id,
            "guesser_user_id": self.guesser_user_id,
            "guess": self.guess,
            "is_correct": self.is_correct,
            "is_on_board": self.is_on_board,
            "attempts_used": self.attempts_used,
            "attempts_remaining": self.attempts_remaining,
            "puzzle_solved": self.puzzle_solved,
            "created_at": self.created_at or _utc_now(),
        }
        if self.attempt_id is not None:
            document["_id"] = self.attempt_id
        return document


@dataclass(frozen=True)
class MatchRecord:
    """Serializable match payload for the matches collection."""

    solver_user_id: str
    target_user_id: str
    puzzle_id: Any
    status: str = "matched"
    matched_at: datetime | None = None
    match_id: Any | None = None

    def to_document(self) -> dict[str, Any]:
        document = {
            "solver_user_id": self.solver_user_id,
            "target_user_id": self.target_user_id,
            "puzzle_id": self.puzzle_id,
            "status": self.status,
            "matched_at": self.matched_at or _utc_now(),
        }
        if self.match_id is not None:
            document["_id"] = self.match_id
        return document


class MongoCompatibleGameRepository:
    """Store puzzle, attempt, and match records in mongo-like collections."""

    def __init__(
        self,
        puzzles_collection: InsertableCollection,
        attempts_collection: InsertableCollection,
        matches_collection: InsertableCollection,
    ) -> None:
        self._puzzles = puzzles_collection
        self._attempts = attempts_collection
        self._matches = matches_collection

    def save_puzzle(
        self,
        owner_user_id: str,
        puzzle: BogglePuzzle,
        created_at: datetime | None = None,
    ) -> PuzzleRecord:
        record = PuzzleRecord.from_puzzle(
            owner_user_id=owner_user_id,
            puzzle=puzzle,
            created_at=created_at,
        )
        inserted = self._puzzles.insert_one(record.to_document())
        return PuzzleRecord(
            owner_user_id=record.owner_user_id,
            question=record.question,
            answer=record.answer,
            board=record.board,
            max_attempts=record.max_attempts,
            questions=record.questions,
            answers=record.answers,
            puzzle_type=record.puzzle_type,
            created_at=record.created_at,
            puzzle_id=inserted.inserted_id,
        )

    def save_puzzle_result(
        self,
        puzzle_id: Any,
        guesser_user_id: str,
        result: GuessResult,
        created_at: datetime | None = None,
    ) -> AttemptRecord:
        record = AttemptRecord.from_guess_result(
            puzzle_id=puzzle_id,
            guesser_user_id=guesser_user_id,
            result=result,
            created_at=created_at,
        )
        inserted = self._attempts.insert_one(record.to_document())
        return AttemptRecord(
            puzzle_id=record.puzzle_id,
            guesser_user_id=record.guesser_user_id,
            guess=record.guess,
            is_correct=record.is_correct,
            is_on_board=record.is_on_board,
            attempts_used=record.attempts_used,
            attempts_remaining=record.attempts_remaining,
            puzzle_solved=record.puzzle_solved,
            created_at=record.created_at,
            attempt_id=inserted.inserted_id,
        )

    def create_match(
        self,
        solver_user_id: str,
        target_user_id: str,
        puzzle_id: Any,
        matched_at: datetime | None = None,
        status: str = "matched",
    ) -> MatchRecord:
        record = MatchRecord(
            solver_user_id=solver_user_id,
            target_user_id=target_user_id,
            puzzle_id=puzzle_id,
            status=status,
            matched_at=matched_at or _utc_now(),
        )
        inserted = self._matches.insert_one(record.to_document())
        return MatchRecord(
            solver_user_id=record.solver_user_id,
            target_user_id=record.target_user_id,
            puzzle_id=record.puzzle_id,
            status=record.status,
            matched_at=record.matched_at,
            match_id=inserted.inserted_id,
        )

    def save_result_and_create_match(
        self,
        puzzle_id: Any,
        guesser_user_id: str,
        target_user_id: str,
        result: GuessResult,
        created_at: datetime | None = None,
    ) -> tuple[AttemptRecord, MatchRecord | None]:
        attempt = self.save_puzzle_result(
            puzzle_id=puzzle_id,
            guesser_user_id=guesser_user_id,
            result=result,
            created_at=created_at,
        )
        match = None
        if result.is_correct:
            match = self.create_match(
                solver_user_id=guesser_user_id,
                target_user_id=target_user_id,
                puzzle_id=puzzle_id,
                matched_at=created_at,
            )
        return attempt, match

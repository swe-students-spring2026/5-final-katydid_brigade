"""HTTP API for the Boggle game engine."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .boggle import BogglePuzzle, GuessResult, PuzzleSession

app = FastAPI(title="Game Engine", version="0.1.0")


class QuestionAnswerRequest(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=5, max_length=10)


class CreatePuzzleRequest(BaseModel):
    question: str | None = Field(default=None, min_length=1)
    answer: str | None = Field(default=None, min_length=5, max_length=10)
    question_answers: list[QuestionAnswerRequest] | None = None
    seed: int | None = None
    max_attempts: int = Field(default=5, ge=1, le=10)


class PuzzleResponse(BaseModel):
    question: str
    answer: str | None = None
    questions: list[str]
    answers: list[str]
    board: list[list[str]]
    max_attempts: int


class EvaluateGuessRequest(BaseModel):
    question: str = Field(default="Combined profile puzzle", min_length=1)
    answer: str | None = Field(default=None, min_length=5, max_length=10)
    questions: list[str] = Field(default_factory=list)
    answers: list[str] = Field(default_factory=list)
    board: list[list[str]]
    guess: str = Field(min_length=5, max_length=10)
    previous_guesses: list[str] = Field(default_factory=list)
    max_attempts: int = Field(default=5, ge=1, le=10)


class GuessResultResponse(BaseModel):
    guess: str
    is_correct: bool
    is_on_board: bool
    attempts_used: int
    attempts_remaining: int
    puzzle_solved: bool
    message: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/puzzles", response_model=PuzzleResponse)
def create_puzzle(payload: CreatePuzzleRequest) -> PuzzleResponse:
    try:
        if payload.question_answers is not None:
            puzzle = BogglePuzzle.from_question_answers(
                question_answers=(
                    (item.question, item.answer) for item in payload.question_answers
                ),
                seed=payload.seed,
                max_attempts=payload.max_attempts,
            )
        elif payload.question is not None and payload.answer is not None:
            puzzle = BogglePuzzle.from_answer(
                question=payload.question,
                answer=payload.answer,
                seed=payload.seed,
                max_attempts=payload.max_attempts,
            )
        else:
            raise ValueError("Provide either one question and answer, or 10 question_answers.")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return PuzzleResponse(
        question=puzzle.question,
        answer=puzzle.answer,
        questions=list(puzzle.questions),
        answers=list(puzzle.answers),
        board=[list(row) for row in puzzle.board],
        max_attempts=puzzle.max_attempts,
    )


@app.post("/guesses", response_model=GuessResultResponse)
def evaluate_guess(payload: EvaluateGuessRequest) -> GuessResultResponse:
    try:
        puzzle = BogglePuzzle(
            question=payload.question,
            answer=payload.answer,
            board=tuple(tuple(cell for cell in row) for row in payload.board),
            max_attempts=payload.max_attempts,
            questions=tuple(payload.questions),
            answers=tuple(payload.answers),
        )
        session = PuzzleSession(puzzle=puzzle)
        _replay_previous_guesses(session, payload.previous_guesses)
        result = session.submit_guess(payload.guess)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return GuessResultResponse(**_guess_result_to_dict(result))


def _replay_previous_guesses(session: PuzzleSession, previous_guesses: list[str]) -> None:
    for previous_guess in previous_guesses:
        session.submit_guess(previous_guess)


def _guess_result_to_dict(result: GuessResult) -> dict[str, str | bool | int]:
    return {
        "guess": result.guess,
        "is_correct": result.is_correct,
        "is_on_board": result.is_on_board,
        "attempts_used": result.attempts_used,
        "attempts_remaining": result.attempts_remaining,
        "puzzle_solved": result.puzzle_solved,
        "message": result.message,
    }

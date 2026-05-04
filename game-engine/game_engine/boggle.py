"""Boggle puzzle generation and guess evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Iterable

BOARD_SIZE = 4
COMBINED_ANSWER_COUNT = 10
MIN_WORD_LENGTH = 5
MAX_WORD_LENGTH = 10
MAX_ATTEMPTS = 5
_FILLER_LETTERS = "eeeeeeeeaaaaiiiioooonnnnrrrsssttttllccddmmuugghhbbffyywwkkvxpzjq"


def normalize_word(word: str) -> str:
    """Validate and normalize a player-provided word."""
    normalized = word.strip().lower()
    if not normalized.isalpha():
        raise ValueError("Words must contain letters only.")
    if not MIN_WORD_LENGTH <= len(normalized) <= MAX_WORD_LENGTH:
        raise ValueError(
            f"Words must be between {MIN_WORD_LENGTH} and {MAX_WORD_LENGTH} letters."
        )
    return normalized


def generate_boggle_board(answer: str, seed: int | None = None) -> tuple[tuple[str, ...], ...]:
    """Create a 4x4 Boggle board containing the provided answer."""
    normalized_answer = normalize_word(answer)
    rng = random.Random(seed)
    path = _build_random_path(rng, len(normalized_answer))
    if path is None:
        raise RuntimeError("Could not generate a Boggle board for the provided answer.")

    board = [[rng.choice(_FILLER_LETTERS) for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    for (row, column), letter in zip(path, normalized_answer):
        board[row][column] = letter
    return tuple(tuple(row) for row in board)


def generate_combined_boggle_board(
    answers: Iterable[str],
    seed: int | None = None,
) -> tuple[tuple[str, ...], ...]:
    """Create one board containing exactly 10 answer words.

    A 4x4 board cannot reliably contain 10 arbitrary profile answers, so the
    combined board uses one row per answer and keeps each answer traceable from
    left to right.
    """
    normalized_answers = normalize_answers(answers)
    rng = random.Random(seed)
    columns = max(len(answer) for answer in normalized_answers)
    board = []
    for answer in normalized_answers:
        row = list(answer)
        row.extend(rng.choice(_FILLER_LETTERS) for _ in range(columns - len(answer)))
        board.append(row)
    return tuple(tuple(row) for row in board)


def normalize_answers(answers: Iterable[str]) -> tuple[str, ...]:
    """Validate and normalize the 10 answer words for a combined puzzle."""
    normalized_answers = tuple(normalize_word(answer) for answer in answers)
    if len(normalized_answers) != COMBINED_ANSWER_COUNT:
        raise ValueError(f"Combined puzzles require exactly {COMBINED_ANSWER_COUNT} answers.")
    if len(set(normalized_answers)) != len(normalized_answers):
        raise ValueError("Combined puzzle answers must be unique.")
    return normalized_answers


def is_word_on_board(board: Iterable[Iterable[str]], word: str) -> bool:
    """Check whether a word can be traced on the Boggle board."""
    normalized_word = normalize_word(word)
    normalized_board = tuple(tuple(cell.lower() for cell in row) for row in board)
    _validate_board_shape(normalized_board)

    for row in range(len(normalized_board)):
        for column in range(len(normalized_board[row])):
            if normalized_board[row][column] != normalized_word[0]:
                continue
            if _search_from_cell(
                normalized_board,
                normalized_word,
                index=0,
                row=row,
                column=column,
                visited={(row, column)},
            ):
                return True
    return False


@dataclass(frozen=True)
class BogglePuzzle:
    """A single daily puzzle tied to another user's answer."""

    question: str
    answer: str | None
    board: tuple[tuple[str, ...], ...]
    max_attempts: int = MAX_ATTEMPTS
    questions: tuple[str, ...] = field(default_factory=tuple)
    answers: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_answer(
        cls,
        question: str,
        answer: str,
        seed: int | None = None,
        max_attempts: int = MAX_ATTEMPTS,
    ) -> "BogglePuzzle":
        normalized_answer = normalize_word(answer)
        board = generate_boggle_board(normalized_answer, seed=seed)
        return cls(
            question=question.strip(),
            answer=normalized_answer,
            board=board,
            max_attempts=max_attempts,
            questions=(question.strip(),),
            answers=(normalized_answer,),
        )

    @classmethod
    def from_question_answers(
        cls,
        question_answers: Iterable[tuple[str, str]],
        seed: int | None = None,
        max_attempts: int = MAX_ATTEMPTS,
    ) -> "BogglePuzzle":
        pairs = tuple((question.strip(), answer) for question, answer in question_answers)
        if len(pairs) != COMBINED_ANSWER_COUNT:
            raise ValueError(f"Combined puzzles require exactly {COMBINED_ANSWER_COUNT} questions.")

        questions = tuple(question for question, _answer in pairs)
        if any(not question for question in questions):
            raise ValueError("Questions cannot be blank.")

        answers = normalize_answers(answer for _question, answer in pairs)
        board = generate_combined_boggle_board(answers, seed=seed)
        return cls(
            question="Combined profile puzzle",
            answer=None,
            board=board,
            max_attempts=max_attempts,
            questions=questions,
            answers=answers,
        )


@dataclass(frozen=True)
class GuessResult:
    """Outcome of a player's guess."""

    guess: str
    is_correct: bool
    is_on_board: bool
    attempts_used: int
    attempts_remaining: int
    puzzle_solved: bool
    message: str


@dataclass
class PuzzleSession:
    """Tracks progress for a player attempting a puzzle."""

    puzzle: BogglePuzzle
    guesses: list[str] = field(default_factory=list)
    solved: bool = False

    def submit_guess(self, guess: str) -> GuessResult:
        if self.solved:
            raise ValueError("Puzzle already solved.")
        if len(self.guesses) >= self.puzzle.max_attempts:
            raise ValueError("No attempts remaining.")

        normalized_guess = normalize_word(guess)
        self.guesses.append(normalized_guess)

        is_on_board = is_word_on_board(self.puzzle.board, normalized_guess)
        correct_answers = self.puzzle.answers or (
            (self.puzzle.answer,) if self.puzzle.answer else ()
        )
        is_correct = normalized_guess in correct_answers
        self.solved = is_correct
        attempts_used = len(self.guesses)
        attempts_remaining = self.puzzle.max_attempts - attempts_used

        if is_correct:
            message = "Correct guess. Create the match."
        elif not is_on_board:
            message = "Guess is not traceable on the board."
        else:
            message = "Valid board word, but not the hidden answer."

        return GuessResult(
            guess=normalized_guess,
            is_correct=is_correct,
            is_on_board=is_on_board,
            attempts_used=attempts_used,
            attempts_remaining=attempts_remaining,
            puzzle_solved=self.solved,
            message=message,
        )


def _validate_board_shape(board: tuple[tuple[str, ...], ...]) -> None:
    if not board:
        raise ValueError("Board must have at least one row.")
    column_count = len(board[0])
    if column_count == 0:
        raise ValueError("Board must have at least one column.")
    if any(len(row) != column_count for row in board):
        raise ValueError("Board rows must all have the same number of columns.")


def _build_random_path(
    rng: random.Random,
    target_length: int,
) -> list[tuple[int, int]] | None:
    starts = [
        (row, column)
        for row in range(BOARD_SIZE)
        for column in range(BOARD_SIZE)
    ]
    rng.shuffle(starts)

    for start in starts:
        path = _walk_path(rng, [start], {start}, target_length)
        if path is not None:
            return path
    return None


def _walk_path(
    rng: random.Random,
    path: list[tuple[int, int]],
    used: set[tuple[int, int]],
    target_length: int,
) -> list[tuple[int, int]] | None:
    if len(path) == target_length:
        return path

    neighbors = [cell for cell in _neighbors(*path[-1]) if cell not in used]
    rng.shuffle(neighbors)

    for next_cell in neighbors:
        result = _walk_path(rng, path + [next_cell], used | {next_cell}, target_length)
        if result is not None:
            return result
    return None


def _neighbors(row: int, column: int) -> list[tuple[int, int]]:
    return _neighbors_for_shape(BOARD_SIZE, BOARD_SIZE, row, column)


def _neighbors_for_shape(
    row_count: int,
    column_count: int,
    row: int,
    column: int,
) -> list[tuple[int, int]]:
    cells = []
    for row_offset in (-1, 0, 1):
        for column_offset in (-1, 0, 1):
            if row_offset == 0 and column_offset == 0:
                continue
            next_row = row + row_offset
            next_column = column + column_offset
            if 0 <= next_row < row_count and 0 <= next_column < column_count:
                cells.append((next_row, next_column))
    return cells


def _search_from_cell(
    board: tuple[tuple[str, ...], ...],
    word: str,
    index: int,
    row: int,
    column: int,
    visited: set[tuple[int, int]],
) -> bool:
    if index == len(word) - 1:
        return True

    for next_row, next_column in _neighbors_for_shape(len(board), len(board[0]), row, column):
        if (next_row, next_column) in visited:
            continue
        if board[next_row][next_column] != word[index + 1]:
            continue

        if _search_from_cell(
            board,
            word,
            index + 1,
            next_row,
            next_column,
            visited | {(next_row, next_column)},
        ):
            return True
    return False

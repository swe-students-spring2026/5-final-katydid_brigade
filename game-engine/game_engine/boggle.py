"""Boggle puzzle generation and guess evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Iterable

BOARD_SIZE = 4
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


def is_word_on_board(board: Iterable[Iterable[str]], word: str) -> bool:
    """Check whether a word can be traced on the Boggle board."""
    normalized_word = normalize_word(word)
    normalized_board = tuple(tuple(cell.lower() for cell in row) for row in board)
    _validate_board_shape(normalized_board)

    for row in range(BOARD_SIZE):
        for column in range(BOARD_SIZE):
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
    answer: str
    board: tuple[tuple[str, ...], ...]
    max_attempts: int = MAX_ATTEMPTS

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
        is_correct = normalized_guess == self.puzzle.answer
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
    if len(board) != BOARD_SIZE:
        raise ValueError(f"Board must have {BOARD_SIZE} rows.")
    if any(len(row) != BOARD_SIZE for row in board):
        raise ValueError(f"Board must have {BOARD_SIZE} columns.")


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
    cells = []
    for row_offset in (-1, 0, 1):
        for column_offset in (-1, 0, 1):
            if row_offset == 0 and column_offset == 0:
                continue
            next_row = row + row_offset
            next_column = column + column_offset
            if 0 <= next_row < BOARD_SIZE and 0 <= next_column < BOARD_SIZE:
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

    for next_row, next_column in _neighbors(row, column):
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

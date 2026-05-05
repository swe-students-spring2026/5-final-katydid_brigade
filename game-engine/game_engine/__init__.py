"""Core package for the Boggle game engine."""

from .boggle import (
    BOARD_SIZE,
    COMBINED_ANSWER_COUNT,
    COMBINED_BOARD_SIZE,
    MAX_ATTEMPTS,
    MAX_WORD_LENGTH,
    MIN_WORD_LENGTH,
    BogglePuzzle,
    GuessResult,
    PuzzleSession,
    generate_boggle_board,
    generate_combined_boggle_board,
    is_word_on_board,
    normalize_answers,
    normalize_word,
)
from .repository import (
    AttemptRecord,
    MatchRecord,
    MongoCompatibleGameRepository,
    PuzzleRecord,
)

__all__ = [
    "BOARD_SIZE",
    "COMBINED_ANSWER_COUNT",
    "COMBINED_BOARD_SIZE",
    "MAX_ATTEMPTS",
    "MAX_WORD_LENGTH",
    "MIN_WORD_LENGTH",
    "BogglePuzzle",
    "GuessResult",
    "PuzzleSession",
    "generate_boggle_board",
    "generate_combined_boggle_board",
    "is_word_on_board",
    "normalize_answers",
    "normalize_word",
    "AttemptRecord",
    "MatchRecord",
    "MongoCompatibleGameRepository",
    "PuzzleRecord",
]

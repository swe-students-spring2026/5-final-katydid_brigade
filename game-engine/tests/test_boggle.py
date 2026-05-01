from game_engine import (
    BogglePuzzle,
    PuzzleSession,
    generate_boggle_board,
    is_word_on_board,
    normalize_word,
)
import pytest


def test_normalize_word_accepts_valid_input() -> None:
    assert normalize_word("  Planet ") == "planet"


@pytest.mark.parametrize("word", ["tree", "encyclopedias", "cat-5", "ice  cream"])
def test_normalize_word_rejects_invalid_input(word: str) -> None:
    with pytest.raises(ValueError):
        normalize_word(word)


def test_generate_boggle_board_contains_answer() -> None:
    board = generate_boggle_board("garden", seed=7)

    assert len(board) == 4
    assert all(len(row) == 4 for row in board)
    assert is_word_on_board(board, "garden")


def test_is_word_on_board_requires_non_reused_path() -> None:
    board = (
        ("a", "b", "c", "d"),
        ("e", "f", "g", "h"),
        ("i", "j", "k", "l"),
        ("m", "n", "o", "p"),
    )

    assert is_word_on_board(board, "afkpo")
    assert not is_word_on_board(board, "abcae")


def test_session_marks_match_on_correct_guess() -> None:
    puzzle = BogglePuzzle.from_answer(
        question="What place would you teleport to?",
        answer="forest",
        seed=5,
    )
    session = PuzzleSession(puzzle=puzzle)

    result = session.submit_guess("forest")

    assert result.is_correct is True
    assert result.puzzle_solved is True
    assert result.attempts_used == 1
    assert result.attempts_remaining == 4


def test_session_tracks_incorrect_guess_that_is_not_on_board() -> None:
    puzzle = BogglePuzzle.from_answer(
        question="Pick a mood word",
        answer="silver",
        seed=3,
    )
    session = PuzzleSession(puzzle=puzzle)

    result = session.submit_guess("planet")

    assert result.is_correct is False
    assert result.is_on_board is False
    assert result.attempts_used == 1
    assert session.solved is False


def test_session_blocks_additional_guesses_after_attempt_limit() -> None:
    puzzle = BogglePuzzle.from_answer(
        question="Best season?",
        answer="autumn",
        seed=11,
    )
    session = PuzzleSession(puzzle=puzzle)

    for guess in ["planet", "flight", "branch", "silver", "pepper"]:
        try:
            session.submit_guess(guess)
        except ValueError:
            break

    with pytest.raises(ValueError, match="No attempts remaining."):
        session.submit_guess("autumn")


def test_session_blocks_guesses_after_solve() -> None:
    puzzle = BogglePuzzle.from_answer(
        question="Favorite nature word?",
        answer="meadow",
        seed=13,
    )
    session = PuzzleSession(puzzle=puzzle)
    session.submit_guess("meadow")

    with pytest.raises(ValueError, match="Puzzle already solved."):
        session.submit_guess("planet")

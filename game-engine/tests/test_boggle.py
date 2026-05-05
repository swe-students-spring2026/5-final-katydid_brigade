from game_engine import (
    BOARD_SIZE,
    BogglePuzzle,
    PuzzleSession,
    generate_boggle_board,
    generate_combined_boggle_board,
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


def test_generate_combined_boggle_board_contains_5_answers() -> None:
    answers = [
        "stone",
        "tones",
        "notes",
        "onset",
        "scent",
    ]

    board = generate_combined_boggle_board(answers, seed=7)

    assert len(board) == 5
    assert all(len(row) == len(board) for row in board)
    assert all(is_word_on_board(board, answer) for answer in answers)
    assert [row[: len(answer)] for row, answer in zip(board, answers)] != [
        tuple(answer) for answer in answers
    ]


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


def test_session_accepts_any_answer_from_combined_puzzle() -> None:
    question_answers = [
        ("Favorite place?", "stone"),
        ("Dream trip?", "tones"),
        ("Best hobby?", "notes"),
        ("Favorite view?", "onset"),
        ("Favorite topic?", "scent"),
    ]
    puzzle = BogglePuzzle.from_question_answers(question_answers, seed=9)
    session = PuzzleSession(puzzle=puzzle)

    result = session.submit_guess("scent")

    assert puzzle.answer is None
    assert len(puzzle.answers) == 5
    assert result.is_correct is True
    assert result.puzzle_solved is True


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


def test_is_word_on_board_returns_true_for_valid_path() -> None:
    # Board where "abcfg" is traceable top-left to bottom-right diagonally
    board = (
        ("a", "b", "c", "d"),
        ("e", "f", "g", "h"),
        ("i", "j", "k", "l"),
        ("m", "n", "o", "p"),
    )
    assert is_word_on_board(board, "abcfg")


def test_is_word_on_board_returns_false_for_non_adjacent_letters() -> None:
    board = (
        ("a", "b", "c", "d"),
        ("e", "f", "g", "h"),
        ("i", "j", "k", "l"),
        ("m", "n", "o", "p"),
    )
    # 'a' is at (0,0) and 'k' is at (2,2) — not adjacent
    assert not is_word_on_board(board, "akbcd")


def test_session_reports_on_board_but_wrong_answer() -> None:
    puzzle = BogglePuzzle.from_answer(
        question="Favorite place?",
        answer="forest",
        seed=3,
    )
    # Find a word that IS traceable on the generated board but is not 'forest'
    session = PuzzleSession(puzzle=puzzle)
    # Submit the answer itself first to confirm the board is valid, then
    # test a word that is on the board
    wrong_word = puzzle.answer  # use answer to confirm path, then test separately

    # More useful: test the case where is_on_board=True, is_correct=False
    # by submitting a word we know is traceable but not the answer.
    # We do this by crafting a minimal board directly.
    # "planet": p(0,0)→l(0,1)→a(0,2)→n(1,2)[diag]→e(2,2)[vert]→t(2,3)[horiz]
    custom_board = (
        ("p", "l", "a", "z"),
        ("z", "z", "n", "z"),
        ("z", "z", "e", "t"),
        ("z", "z", "z", "z"),
    )
    # 'planet' is traceable on this board (p→l→a→n→e→t)
    custom_puzzle = BogglePuzzle(
        question="Favorite place?",
        answer="forest",  # hidden answer is 'forest', not 'planet'
        board=custom_board,
    )
    custom_session = PuzzleSession(puzzle=custom_puzzle)
    result = custom_session.submit_guess("planet")

    assert result.is_on_board is True
    assert result.is_correct is False
    assert result.puzzle_solved is False


def test_generate_boggle_board_has_correct_shape() -> None:
    board = generate_boggle_board("storm", seed=99)
    assert len(board) == BOARD_SIZE
    assert all(len(row) == BOARD_SIZE for row in board)
    assert all(
        isinstance(cell, str) and len(cell) == 1 for row in board for cell in row
    )


def test_boggle_puzzle_from_answer_rejects_short_word() -> None:
    with pytest.raises(ValueError):
        BogglePuzzle.from_answer(question="Test?", answer="hi")


def test_boggle_puzzle_from_answer_rejects_long_word() -> None:
    with pytest.raises(ValueError):
        BogglePuzzle.from_answer(question="Test?", answer="extraordinarily")

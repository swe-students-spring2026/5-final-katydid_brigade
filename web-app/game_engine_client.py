import requests


def create_puzzle(
    engine_url,
    question=None,
    answer=None,
    question_answers=None,
    seed=None,
    max_attempts=5,
):
    payload = {
        "seed": seed,
        "max_attempts": max_attempts,
    }
    if question_answers is not None:
        payload["question_answers"] = question_answers
    else:
        payload["question"] = question
        payload["answer"] = answer

    resp = requests.post(f"{engine_url}/puzzles", json=payload)
    resp.raise_for_status()
    return resp.json()  # {question, answer, board, max_attempts}


def evaluate_guess(
    engine_url,
    question,
    answer,
    board,
    guess,
    previous_guesses=None,
    max_attempts=5,
    questions=None,
    answers=None,
):
    resp = requests.post(f"{engine_url}/guesses", json={
        "question": question,
        "answer": answer,
        "questions": questions or [],
        "answers": answers or [],
        "board": board,
        "guess": guess,
        "previous_guesses": previous_guesses or [],
        "max_attempts": max_attempts,
    })
    resp.raise_for_status()
    return resp.json()  # {is_correct, is_on_board, attempts_remaining, puzzle_solved, ...}

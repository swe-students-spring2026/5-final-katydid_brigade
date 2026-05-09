import requests


def raise_for_game_engine_error(response):
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = response.text

        if isinstance(detail, list):
            messages = []
            for item in detail:
                location = ".".join(str(part) for part in item.get("loc", []))
                message = item.get("msg", "Invalid request")
                messages.append(f"{location}: {message}" if location else message)
            detail = "; ".join(messages)

        if detail:
            raise requests.HTTPError(str(detail), response=response) from error
        raise


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
    raise_for_game_engine_error(resp)
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
    payload = {
        "question": question,
        "questions": questions or [],
        "answers": answers or [],
        "board": board,
        "guess": guess,
        "previous_guesses": previous_guesses or [],
        "max_attempts": max_attempts,
    }
    if answer is not None:
        payload["answer"] = answer

    resp = requests.post(f"{engine_url}/guesses", json=payload)
    raise_for_game_engine_error(resp)
    return resp.json()  # {is_correct, is_on_board, attempts_remaining, puzzle_solved, ...}

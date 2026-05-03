import requests

def create_puzzle(engine_url, question, answer, seed=None, max_attempts=5):
    resp = requests.post(f"{engine_url}/puzzles", json={
        "question": question,
        "answer": answer,
        "seed": seed,
        "max_attempts": max_attempts,
    })
    resp.raise_for_status()
    return resp.json()  # {question, answer, board, max_attempts}

def evaluate_guess(engine_url, question, answer, board, guess, previous_guesses=[], max_attempts=5):
    resp = requests.post(f"{engine_url}/guesses", json={
        "question": question,
        "answer": answer,
        "board": board,
        "guess": guess,
        "previous_guesses": previous_guesses,
        "max_attempts": max_attempts,
    })
    resp.raise_for_status()
    return resp.json()  # {is_correct, is_on_board, attempts_remaining, puzzle_solved, ...}

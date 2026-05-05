"""Flask Web app - backend for Word Game and Matchmaking"""

import itertools
import random
from datetime import date
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_socketio import SocketIO, emit, join_room
from datetime import datetime
from game_engine_client import evaluate_guess, create_puzzle
from pymongo import MongoClient
from bson.objectid import ObjectId

from bson.errors import InvalidId
from bson.objectid import ObjectId
from config import Config
from flask import Flask, Response, flash, g, redirect, render_template, request, session, url_for
from game_engine_client import create_puzzle, evaluate_guess
from pymongo import MongoClient


def create_app(test_config=None):
    app = Flask(__name__)
    socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")


    if test_config:
        if isinstance(test_config, dict):
            app.config.update(test_config)
        else:
            app.config.from_object(test_config)
    else:
        app.config.from_object(Config)

    # ------- database setup -------
    client = MongoClient(app.config["MONGO_URI"], serverSelectionTimeoutMS=5000)
    db = client[app.config["DB_NAME"]]

    SETUP_QUESTIONS = [
        "Favorite music genre?",
        "Dream travel spot?",
        "Favorite hobby?",
        "Favorite food?",
        "Favorite movie type?",
        "Best school subject?",
        "Morning or night?",
        "Favorite season?",
        "Coffee or tea?",
        "Favorite game?",
    ]
    SAMPLE_USERNAME = "sample_match"
    # TODO DEPLOYMENT: remove this hard-coded sample user and seeded puzzle.
    # It exists only so local development always has a puzzle-ready profile.
    SAMPLE_ANSWERS = [
        "melody",
        "island",
        "hiking",
        "noodle",
        "comedy",
        "algebra",
        "sunrise",
        "autumn",
        "coffee",
        "puzzle",
    ]
    PUZZLE_ANSWER_COUNT = 5

    # ------- shared helpers -------
    def get_current_user():
        if "user_id" not in session:
            return None
        return db.users.find_one({"_id": ObjectId(session["user_id"])})

    def profile_image_url(user):
        if user and user.get("profile_image") and user.get("_id"):
            return url_for("profile_image", user_id=str(user["_id"]))
        return ""

    def save_profile_fields():
        update = {
            "name": request.form.get("name", ""),
            "age": int(request.form.get("age") or 0),
            "gender": request.form.get("gender"),
            "contact_info": request.form.get("contact_info", ""),
        }
        if request.form.get("username"):
            update["username"] = request.form.get("username")
        if request.form.get("email"):
            update["email"] = request.form.get("email")
        if request.form.get("new_password"):
            update["password"] = request.form.get("new_password")

        profile_image = request.files.get("profile_image")
        if profile_image and profile_image.filename:
            update["profile_image"] = {
                "data": profile_image.read(),
                "content_type": profile_image.mimetype or "application/octet-stream",
                "filename": profile_image.filename,
            }

        db.users.update_one(
            {"_id": ObjectId(session["user_id"])},
            {"$set": update},
        )

    def save_question_puzzles():
        engine_url = app.config["GAME_ENGINE_URL"]
        question_answers = []

        for i, question in enumerate(SETUP_QUESTIONS, start=1):
            answer = (request.form.get(f"answer_{i}") or "").strip()
            if not answer:
                continue
            question_answers.append({"question": question, "answer": answer})

        if not question_answers:
            return
        if len(question_answers) != len(SETUP_QUESTIONS):
            raise ValueError("Enter all 10 puzzle answers before saving the puzzle.")

        db.users.update_one(
            {"_id": ObjectId(session["user_id"])},
            {"$set": {"question_answers": question_answers}},
        )
        puzzle_data = None
        last_error = None
        for selected_question_answers in iter_puzzle_question_answer_selections(question_answers):
            try:
                puzzle_data = create_puzzle(
                    engine_url,
                    question_answers=selected_question_answers,
                )
                break
            except Exception as error:
                last_error = error

        if puzzle_data is None:
            raise ValueError(
                "Could not generate a 5x5 puzzle from any 5-answer selection. "
                "Try answers with more shared letters."
            ) from last_error

        db.puzzles.replace_one(
            {"owner_user_id": session["user_id"], "question": puzzle_data["question"]},
            {
                "owner_user_id": session["user_id"],
                "question": puzzle_data["question"],
                "answer": puzzle_data.get("answer"),
                "questions": puzzle_data["questions"],
                "answers": puzzle_data["answers"],
                "board": puzzle_data["board"],
                "max_attempts": puzzle_data["max_attempts"],
            },
            upsert=True,
        )

    def attach_profile_questions(user):
        saved_question_answers = {
            item.get("question"): item.get("answer", "")
            for item in user.get("question_answers", [])
        }
        combined_puzzle = db.puzzles.find_one({
            "owner_user_id": session["user_id"],
            "questions": {"$exists": True},
            "answers": {"$exists": True},
        })
        if combined_puzzle:
            existing_answers = dict(zip(
                combined_puzzle.get("questions", []),
                combined_puzzle.get("answers", []),
            ))
        else:
            existing_answers = {}

        existing_puzzles = {
            puzzle["question"]: puzzle
            for puzzle in db.puzzles.find({"owner_user_id": session["user_id"]})
        }
        user["questions"] = [
            {
                "question": question,
                "answer": existing_answers.get(
                    question,
                    saved_question_answers.get(
                        question,
                        existing_puzzles.get(question, {}).get("answer", ""),
                    ),
                ),
            }
            for question in SETUP_QUESTIONS
        ]
        return user

    def iter_puzzle_question_answer_selections(question_answers, seed=None):
        rng = random.Random(seed)
        selections = [
            list(selection)
            for selection in itertools.combinations(question_answers, PUZZLE_ANSWER_COUNT)
        ]
        rng.shuffle(selections)
        return selections

    def select_puzzle_question_answers(question_answers, seed=None):
        return next(iter(iter_puzzle_question_answer_selections(question_answers, seed=seed)))

    def user_profile_for_match(match):
        user_id = session.get("user_id")
        other_user_id = match.get("target_user_id")
        if other_user_id == user_id:
            other_user_id = match.get("solver_user_id")

        try:
            user = db.users.find_one({"_id": ObjectId(other_user_id)})
        except (InvalidId, TypeError):
            user = None

        if not user:
            return None

        user["id"] = str(match["_id"])
        user["questions"] = list(db.puzzles.find({"owner_user_id": str(user["_id"])}))
        return user

    def puzzle_session_keys(puzzle):
        puzzle_id = str(puzzle["_id"])
        return f"puzzle_{puzzle_id}_correct", f"puzzle_{puzzle_id}_guesses"

    def sample_question_answers():
        return [
            {"question": question, "answer": answer}
            for question, answer in zip(SETUP_QUESTIONS, SAMPLE_ANSWERS)
        ]

    def fallback_sample_puzzle():
        board = [
            list("oynoy"),
            list("ldeod"),
            list("hesln"),
            list("mikga"),
            list("cowin"),
        ]
        return {
            "question": "Combined profile puzzle",
            "answer": None,
            "questions": SETUP_QUESTIONS[:PUZZLE_ANSWER_COUNT],
            "answers": SAMPLE_ANSWERS[:PUZZLE_ANSWER_COUNT],
            "board": board,
            "max_attempts": 5,
        }

    def ensure_sample_user():
        sample_user = db.users.find_one({"username": SAMPLE_USERNAME})
        if sample_user is None:
            result = db.users.insert_one({
                "username": SAMPLE_USERNAME,
                "email": "sample@example.com",
                "password": "password",
                "name": "Sample Match",
                "age": 24,
                "gender": "female",
                "contact_info": "sample@example.com",
            })
            sample_user_id = str(result.inserted_id)
        else:
            sample_user_id = str(sample_user["_id"])

        existing_puzzle = db.puzzles.find_one({"owner_user_id": sample_user_id})
        if (
            existing_puzzle
            and len(existing_puzzle.get("board", [])) == 5
            and all(len(row) == 5 for row in existing_puzzle.get("board", []))
            and len(existing_puzzle.get("answers", [])) == PUZZLE_ANSWER_COUNT
            and set(existing_puzzle.get("answers", [])).issubset(set(SAMPLE_ANSWERS))
        ):
            return

        try:
            puzzle_data = create_puzzle(
                app.config["GAME_ENGINE_URL"],
                question_answers=select_puzzle_question_answers(
                    sample_question_answers(),
                    seed=1,
                ),
            )
        except Exception:
            puzzle_data = fallback_sample_puzzle()

        db.puzzles.replace_one(
            {"owner_user_id": sample_user_id, "question": puzzle_data["question"]},
            {
                "owner_user_id": sample_user_id,
                "question": puzzle_data["question"],
                "answer": puzzle_data.get("answer"),
                "questions": puzzle_data["questions"],
                "answers": puzzle_data["answers"],
                "board": puzzle_data["board"],
                "max_attempts": puzzle_data["max_attempts"],
            },
            upsert=True,
        )

    # ------- request hooks -------
    @app.context_processor
    def inject_template_helpers():
        return {"profile_image_url": profile_image_url}

    @app.before_request
    def require_login():
        if not app.config.get("TESTING") and request.endpoint != "static":
            ensure_sample_user()

        g.current_user = None
        user_id = session.get("user_id")
        if user_id:
            try:
                g.current_user = db.users.find_one({"_id": ObjectId(user_id)})
            except InvalidId:
                g.current_user = None
            if g.current_user is None:
                session.clear()

        public_routes = {"index", "login", "register", "static"}
        if request.endpoint in public_routes:
            return None
        if g.current_user is None:
            return redirect(url_for("login"))
        return None

    # ------- home page -------
    @app.route("/")
    def index():
        return render_template("index.html")

    # ------- login page -------
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")

            user = db.users.find_one({"username": username, "password": password})
            if not user:
                flash("Invalid username or password")
                return render_template("login.html")

            session["user_id"] = str(user["_id"])
            return redirect(url_for("dashboard"))
        return render_template("login.html")

    # ------- register page -------
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username")
            email = request.form.get("email")
            password = request.form.get("password")

            if db.users.find_one({"username": username}):
                flash("That username is already taken")
                return redirect(url_for("register"))

            result = db.users.insert_one({
                "username": username,
                "email": email,
                "password": password,
            })

            session["user_id"] = str(result.inserted_id)
            return redirect(url_for("setup"))
        return render_template("register.html")

    # ------- setup page -------
    @app.route("/setup", methods=["GET", "POST"])
    def setup():
        if request.method == "POST":
            save_profile_fields()
            try:
                save_question_puzzles()
            except Exception as error:
                flash(f"Puzzle could not be generated: {error}")
                user = attach_profile_questions(get_current_user() or {})
                user["questions"] = [
                    {
                        "question": question,
                        "answer": request.form.get(f"answer_{i}") or "",
                    }
                    for i, question in enumerate(SETUP_QUESTIONS, start=1)
                ]
                return render_template("setup.html", user=user), 400

            return redirect(url_for("dashboard"))
        user = attach_profile_questions(get_current_user() or {})
        return render_template("setup.html", user=user)

    # ------- dashboard page -------
    @app.route("/dashboard", methods=["GET", "POST"])
    def dashboard():
        engine_url = app.config["GAME_ENGINE_URL"]
        result = None
        outcome = None

        current_user_id = session.get("user_id")
        puzzle_owner_ids = []
        for puzzle_owner_id in db.puzzles.distinct("owner_user_id"):
            try:
                puzzle_owner_ids.append(ObjectId(puzzle_owner_id))
            except (InvalidId, TypeError):
                continue

        match_filter = {"_id": {"$in": puzzle_owner_ids}}
        if current_user_id:
            try:
                match_filter["_id"]["$ne"] = ObjectId(current_user_id)
            except InvalidId:
                pass

        candidate = next(db.users.aggregate([
            {"$match": match_filter},
            {"$sample": {"size": 1}},
        ]), None)

        puzzles = list(db.puzzles.find({"owner_user_id": str(candidate["_id"])})) if candidate else []
        puzzle = puzzles[0] if puzzles else None
        answers = puzzle.get("answers", []) if puzzle else []
        correct_guesses = []
        all_guesses = []
        if puzzle:
            correct_key, guesses_key = puzzle_session_keys(puzzle)
            correct_guesses = session.get(correct_key, [])
            all_guesses = session.get(guesses_key, [])

        if request.method == "POST":
            guess = (request.form.get("guess") or "").strip()
            if puzzle and guess:
                try:
                    outcome = evaluate_guess(
                        engine_url,
                        question=puzzle["question"],
                        answer=puzzle.get("answer"),
                        questions=puzzle.get("questions", []),
                        answers=answers,
                        board=puzzle["board"],
                        guess=guess,
                        previous_guesses=[],
                        max_attempts=puzzle["max_attempts"],
                    )
                    normalized_guess = outcome["guess"]
                    if normalized_guess not in all_guesses:
                        all_guesses.append(normalized_guess)
                    if outcome["is_correct"] and normalized_guess not in correct_guesses:
                        correct_guesses.append(normalized_guess)
                    session[guesses_key] = all_guesses
                    session[correct_key] = correct_guesses
                except Exception as error:
                    outcome = {
                        "is_correct": False,
                        "message": str(error),
                    }

            result = {
                "score": len(correct_guesses),
                "total": len(answers),
                "matched": bool(answers) and len(correct_guesses) == len(answers),
            }

            if result["matched"] and candidate:
                db.matches.insert_one({
                    "solver_user_id": session.get("user_id"),
                    "target_user_id": str(candidate["_id"]),
                    "status": "matched",
                    "matched_at": date.today().isoformat(),
                })
        elif puzzle:
            result = {
                "score": len(correct_guesses),
                "total": len(answers),
                "matched": bool(answers) and len(correct_guesses) == len(answers),
            }

        return render_template(
            "dashboard.html",
            candidate=candidate,
            puzzle=puzzle,
            correct_guesses=correct_guesses,
            all_guesses=all_guesses,
            today=date.today(),
            outcome=outcome,
            result=result,
        )

    # ------- matches page -------
    @app.route("/matches")
    def matches_page():
        user_id = session.get("user_id")
        match_records = list(db.matches.find({
            "$or": [{"solver_user_id": user_id}, {"target_user_id": user_id}]
        }))
        matches = [
            profile
            for profile in (user_profile_for_match(match) for match in match_records)
            if profile
        ]
        return render_template("matches.html", matches=matches)

    # ------- match detail page -------
    @app.route("/matches/<match_id>")
    def match_detail(match_id):
        try:
            match = db.matches.find_one({"_id": ObjectId(match_id)})
        except InvalidId:
            match = None
        if match is None:
            return render_template("404.html"), 404

        profile = user_profile_for_match(match)
        if profile is None:
            return render_template("404.html"), 404
        return render_template("match_detail.html", match=profile)

    # ------- settings page -------
    @app.route("/profile", methods=["GET", "POST"])
    def profile():
        if request.method == "POST":
            return redirect(url_for("settings"), code=307)
        return redirect(url_for("settings"))

    @app.route("/settings", methods=["GET", "POST"])
    @app.route("/setting", methods=["GET", "POST"])
    def settings():
        saved = request.method == "POST"
        if saved:
            save_profile_fields()

        return render_template("settings.html", user=get_current_user() or {}, saved=saved)

    # ------- puzzle questions redirect -------
    @app.route("/settings/puzzle-questions", methods=["GET", "POST"])
    @app.route("/setting/puzzle-questions", methods=["GET", "POST"])
    def puzzle_questions():
        return redirect(url_for("setup"))

    # ------- profile image -------
    @app.route("/users/<user_id>/profile-image")
    def profile_image(user_id):
        try:
            user = db.users.find_one({"_id": ObjectId(user_id)})
        except InvalidId:
            user = None

        image = user.get("profile_image") if user else None
        if not image:
            return Response(status=404)

        return Response(
            image["data"],
            mimetype=image.get("content_type", "application/octet-stream"),
        )

    # ------- logout page -------
    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/matches/<match_id>/chat")
    def chat(match_id):
        if "user_id" not in session:
            return redirect(url_for("login"))
        try:
            match = db.matches.find_one({"_id": ObjectId(match_id)})
        except InvalidId:
            match = None
        if match is None:
            return render_template("404.html"), 404
        messages = list(db.messages.find({"match_id": match_id}))
        return render_template("chat.html", match_id=match_id, messages=messages)

    @socketio.on("send_message")
    def handle_message(data):
        match_id = data.get("match_id")
        text = data.get("text")
        sender_id = session.get("user_id")
        msg = {
            "match_id": match_id,
            "sender_user_id": sender_id,
            "text": text,
            "sent_at": datetime.utcnow().isoformat(),
        }
        db.messages.insert_one(msg)
        msg.pop("_id", None)
        emit("receive_message", msg, to=match_id)

    @socketio.on("join")
    def on_join(data):
        join_room(data["match_id"])

    return app, socketio

app, socketio = create_app()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8000)

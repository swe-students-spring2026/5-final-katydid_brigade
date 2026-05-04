"""Flask Web app - backend for Word Game and Matchmaking"""

import os

from datetime import date
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from game_engine_client import evaluate_guess, create_puzzle
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.errors import InvalidId
from config import Config


def create_app(test_config=None):
    app = Flask(__name__)


    if test_config:
        if isinstance(test_config, dict):
            app.config.update(test_config)
        else:
            app.config.from_object(test_config)
    else:
        app.config.from_object(Config)

    # MongoDB
    client = MongoClient(app.config["MONGO_URI"])
    db = client[app.config["DB_NAME"]]

    # current user
    def get_current_user():
        if "user_id" not in session:
            return None
        return db.users.find_one({"_id": ObjectId(session["user_id"])})

    @app.route("/")
    def index():
        return render_template("index.html")

   # login
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

   # register
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username")
            email = request.form.get("email")
            password = request.form.get("password")

            if db.users.find_one({"username": username}):
                flash("That username is already taken")
                return redirect(url_for("register"))

            db.users.insert_one({
                "username": username,
                "email": email,
                "password": password,
            })

            return redirect(url_for("setup"))
        return render_template("register.html")

    #setup
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

    @app.route("/setup", methods=["GET", "POST"])
    def setup():
        if "user_id" not in session:
            return redirect(url_for("login"))

        if request.method == "POST":
            db.users.update_one(
                {"_id": ObjectId(session["user_id"])},
                {"$set": {
                    "age": int(request.form.get("age") or 0),
                    "gender": request.form.get("gender"),
                    "profile_pic": request.form.get("profile_pic", ""),
                    "contact_info": request.form.get("contact_info", ""),
                }}
            )

            engine_url = app.config["GAME_ENGINE_URL"]

            question_answers = []
            for i, question in enumerate(SETUP_QUESTIONS, start=1):
                answer = request.form.get(f"answer_{i}")
                if answer:
                    question_answers.append({"question": question, "answer": answer})

            if len(question_answers) == len(SETUP_QUESTIONS):
                try:
                    puzzle_data = create_puzzle(
                        engine_url,
                        question_answers=question_answers,
                    )
                    db.puzzles.insert_one({
                        "owner_user_id": session["user_id"],
                        "question": puzzle_data["question"],
                        "answer": puzzle_data["answer"],
                        "questions": puzzle_data["questions"],
                        "answers": puzzle_data["answers"],
                        "board": puzzle_data["board"],
                        "max_attempts": puzzle_data["max_attempts"],
                    })
                except Exception:
                    pass

            return redirect(url_for("dashboard"))
        return render_template("setup.html", questions=SETUP_QUESTIONS)

    # dashboard
    @app.route("/dashboard", methods=["GET", "POST"])
    def dashboard():
        engine_url = app.config["GAME_ENGINE_URL"]
        result = None
        candidate = next(db.users.aggregate([
            {"$match": {"_id": {"$ne": session.get("user_id")}}},
            {"$sample": {"size": 1}}
        ]), None)
            
        puzzles = list(db.puzzles.find({"owner_user_id": str(candidate["_id"])})) if candidate else []
        puzzle = puzzles[0] if puzzles else None
        if candidate and puzzle:
            candidate["questions"] = [
                {"question": question} for question in puzzle.get("questions", [])
            ]

        if request.method == "POST":
            correct_count = 0
            answers = puzzle.get("answers", []) if puzzle else []
            for i, _answer in enumerate(answers, start=1):
                guess = request.form.get(f"answer_{i}")
                previous_guesses = session.get(f"guesses_{i}", [])

                outcome = evaluate_guess(
                    engine_url,
                    question=puzzle["question"],
                    answer=puzzle.get("answer"),
                    questions=puzzle.get("questions", []),
                    answers=answers,
                    board=puzzle["board"],
                    guess=guess,
                    previous_guesses=previous_guesses,
                    max_attempts=puzzle["max_attempts"],
                )

                session.setdefault(f"guesses_{i}", []).append(guess)
                if outcome["is_correct"]:
                    correct_count += 1

            result = {
                "score": correct_count,
                "total": len(answers),
                "matched": bool(answers) and correct_count == len(answers),
            }

            if result["matched"] and candidate:
                db.matches.insert_one({
                    "solver_user_id": session.get("user_id"),
                    "target_user_id": str(candidate["_id"]),
                    "status": "matched",
                    "matched_at": date.today().isoformat(),
                })
        return render_template("dashboard.html", candidate=candidate, today=date.today(), result=result)

    @app.route("/matches")
    def matches_page():
        user_id = session.get("user_id")
        matches = list(db.matches.find({
            "$or": [{"solver_user_id": user_id}, {"target_user_id": user_id}]
        }))
        return render_template("matches.html", matches=matches)

    @app.route("/matches/<match_id>")
    def match_detail(match_id):
        try:
            match = db.matches.find_one({"_id": ObjectId(match_id)})
        except InvalidId:
            match = None
        if match is None:
            return render_template("404.html"), 404
        return render_template("match_detail.html", match=match)

    @app.route("/profile", methods=["GET", "POST"])
    def profile():
        user = get_current_user() or {}
        saved = request.method == "POST"
        return render_template("profile.html", user=user, saved=saved)

    @app.route("/settings", methods=["GET", "POST"])
    def settings():
        saved = request.method == "POST"
        return render_template("settings.html", saved=saved)

    @app.route("/logout")
    def logout():
        return redirect(url_for("login"))

    return app

app = create_app()

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=8000)

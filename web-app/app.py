"""Flask Web app - backend for Word Game and Matchmaking"""

import os
import requests as http

from datetime import date
from ./game_engine/game_engine/game_engine_client import evaluate_guess
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
from config import Config

# generate puzzle

# save answers

# get answers

# find matches

# get matches

def create_app(test_config=None):
    app = Flask(__name__)


    if test_config:
        app.config.update(test_config)
    else:
        app.config.from_object(Config)

    # MongoDB
    client = MongoClient(app.config["MONGO_URI"])
    db = client["katydid_brigade"]

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
        user = get_current_user()
        if not user:
            return redirect(url_for("login"))

        if request.method == "POST":
            db.users.update_one(
                {"_id": user["_id"]},
                {"$set": {
                    "age": int(request.form.get("age")),
                    "gender": request.form.get("gender"),
                    "profile_pic": request.form.get("profile_pic", ""),
                    "contact_info": request.form.get("contact_info", ""),
                }}
            )

            engine_url = app.config["GAME_ENGINE_URL"]

            for i, question in enumerate(SETUP_QUESTIONS, start=1):
                answer = request.form.get(f"answer_{i}")
                puzzle_data = create_puzzle(engine_url, question=question, answer=answer)
                db.puzzles.insert_one({
                    "owner_user_id": session["user_id"],
                    "question": puzzle_data["question"],
                    "answer": puzzle_data["answer"],
                    "board": puzzle_data["board"],
                    "max_attempts": puzzle_data["max_attempts"],
                })
\
            return redirect(url_for("dashboard"))
        return render_template("setup.html", questions=SETUP_QUESTIONS)

    # dashboard
    @app.route("/dashboard", methods=["GET", "POST"])
    def dashboard():
        engine_url = app.config["GAME_ENGINE_URL"]
        result = None

        if request.method == "POST":
            puzzle = db.puzzles.find_one({"date": str(date.today())})
            
            guess = request.form.get("answer_1")  
            previous_guesses = session.get("guesses", [])

            outcome = evaluate_guess(
                engine_url,
                question=puzzle["question"],
                answer=puzzle["answer"],
                board=puzzle["board"],
                guess=guess,
                previous_guesses=previous_guesses,
            )

            session.setdefault("guesses", []).append(guess)

            result = {
                "score": 1 if outcome["is_correct"] else 0,
                "total": 1,
                "matched": outcome["puzzle_solved"],
            }

        candidate = db.users.find_one({"is_candidate": True}) 
        return render_template("dashboard.html", candidate=candidate, today=date.today(), result=result)

    @app.route("/matches")
    def matches_page():
        return render_template("matches.html", matches=matches)

    @app.route("/matches/<int:match_id>")
    def match_detail(match_id):
        match = next((item for item in matches if item["id"] == match_id), None)
        if match is None:
            return render_template("404.html"), 404
        return render_template("match_detail.html", match=match)

    @app.route("/profile", methods=["GET", "POST"])
    def profile():
        saved = request.method == "POST"
        return render_template("profile.html", user=sample_user, saved=saved)

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

"""Flask Web app - backend for Word Game and Matchmaking"""

from datetime import date

from bson.errors import InvalidId
from bson.objectid import ObjectId
from config import Config
from flask import Flask, Response, flash, g, redirect, render_template, request, session, url_for
from game_engine_client import create_puzzle, evaluate_guess
from pymongo import MongoClient


def create_app(test_config=None):
    app = Flask(__name__)

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

        for i, question in enumerate(SETUP_QUESTIONS, start=1):
            answer = request.form.get(f"answer_{i}")
            if not answer:
                continue
            try:
                puzzle_data = create_puzzle(engine_url, question=question, answer=answer)
                db.puzzles.replace_one(
                    {"owner_user_id": session["user_id"], "question": question},
                    {
                        "owner_user_id": session["user_id"],
                        "question": puzzle_data["question"],
                        "answer": puzzle_data["answer"],
                        "board": puzzle_data["board"],
                        "max_attempts": puzzle_data["max_attempts"],
                    },
                    upsert=True,
                )
            except Exception:
                pass

    def attach_profile_questions(user):
        existing_puzzles = {
            puzzle["question"]: puzzle
            for puzzle in db.puzzles.find({"owner_user_id": session["user_id"]})
        }
        user["questions"] = [
            {
                "question": question,
                "answer": existing_puzzles.get(question, {}).get("answer", ""),
            }
            for question in SETUP_QUESTIONS
        ]
        return user

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

    # ------- request hooks -------
    @app.context_processor
    def inject_template_helpers():
        return {"profile_image_url": profile_image_url}

    @app.before_request
    def require_login():
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
            save_question_puzzles()
            return redirect(url_for("dashboard"))
        user = attach_profile_questions(get_current_user() or {})
        return render_template("setup.html", user=user)

    # ------- dashboard page -------
    @app.route("/dashboard", methods=["GET", "POST"])
    def dashboard():
        engine_url = app.config["GAME_ENGINE_URL"]
        result = None

        current_user_id = session.get("user_id")
        match_filter = {}
        if current_user_id:
            try:
                match_filter = {"_id": {"$ne": ObjectId(current_user_id)}}
            except InvalidId:
                match_filter = {}

        candidate = next(db.users.aggregate([
            {"$match": match_filter},
            {"$sample": {"size": 1}},
        ]), None)

        puzzles = list(db.puzzles.find({"owner_user_id": str(candidate["_id"])})) if candidate else []
        if candidate:
            candidate["questions"] = puzzles

        if request.method == "POST":
            correct_count = 0
            for i, puzzle in enumerate(puzzles, start=1):
                guess = request.form.get(f"answer_{i}")
                previous_guesses = session.get(f"guesses_{i}", [])

                outcome = evaluate_guess(
                    engine_url,
                    question=puzzle["question"],
                    answer=puzzle["answer"],
                    board=puzzle["board"],
                    guess=guess,
                    previous_guesses=previous_guesses,
                    max_attempts=puzzle.get("max_attempts", 5),
                )

                session.setdefault(f"guesses_{i}", []).append(guess)
                if outcome["is_correct"]:
                    correct_count += 1

            result = {
                "score": correct_count,
                "total": len(puzzles),
                "matched": correct_count == len(puzzles),
            }

            if correct_count == len(puzzles) and candidate:
                db.matches.insert_one({
                    "solver_user_id": session.get("user_id"),
                    "target_user_id": str(candidate["_id"]),
                    "status": "matched",
                    "matched_at": date.today().isoformat(),
                })
        return render_template("dashboard.html", candidate=candidate, today=date.today(), result=result)

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

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

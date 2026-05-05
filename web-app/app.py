"""Flask Web app - backend for Word Game and Matchmaking"""

import itertools
import random
from datetime import date, datetime
from flask_socketio import SocketIO, emit, join_room

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
            try:
                save_question_puzzles()
            except Exception as error:
                flash(f"Answers saved, but puzzle could not be generated: {error}")
            return redirect(url_for("dashboard"))

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

        exclude_ids = []
        if current_user_id:
            try:
                exclude_ids.append(ObjectId(current_user_id))
            except InvalidId:
                pass

            matched_records = db.matches.find({
                "$or": [
                    {"solver_user_id": current_user_id},
                    {"target_user_id": current_user_id},
                ]
            })
            for m in matched_records:
                other_id = (
                    m.get("target_user_id")
                    if m.get("solver_user_id") == current_user_id
                    else m.get("solver_user_id")
                )
                try:
                    exclude_ids.append(ObjectId(other_id))
                except (InvalidId, TypeError):
                    pass

        match_filter = {"_id": {"$in": puzzle_owner_ids, "$nin": exclude_ids}}

        candidate_id_from_form = request.form.get("candidate_id") if request.method == "POST" else None
        if candidate_id_from_form:
            try:
                candidate = db.users.find_one({"_id": ObjectId(candidate_id_from_form)})
            except (InvalidId, TypeError):
                candidate = None
        else:
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
    
    # ------- chat helpers -------
    def format_timestamp(iso_string):
        """Convert ISO timestamp to a human-readable relative time."""
        try:
            dt = datetime.fromisoformat(iso_string)
            now = datetime.utcnow()
            diff = now - dt
            seconds = diff.total_seconds()
            if seconds < 60:
                return "just now"
            elif seconds < 3600:
                minutes = int(seconds // 60)
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            elif seconds < 86400:
                hours = int(seconds // 3600)
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
            else:
                return dt.strftime("%b %d at %I:%M %p")
        except Exception:
            return iso_string

    def get_chat_partner(match):
        """Given a match document, return the other user's info."""
        user_id = session.get("user_id")
        other_id = match.get("target_user_id")
        if other_id == user_id:
            other_id = match.get("solver_user_id")
        try:
            partner = db.users.find_one({"_id": ObjectId(other_id)})
        except (InvalidId, TypeError):
            partner = None
        return partner

    def enrich_messages(messages):
        """Add sender username and formatted timestamp to each message."""
        enriched = []
        user_cache = {}
        for msg in messages:
            sender_id = msg.get("sender_user_id")
            if sender_id not in user_cache:
                try:
                    user = db.users.find_one({"_id": ObjectId(sender_id)})
                    user_cache[sender_id] = user.get("username", "Unknown") if user else "Unknown"
                except Exception:
                    user_cache[sender_id] = "Unknown"
            enriched.append({
                "text": msg.get("text", ""),
                "sender_username": user_cache[sender_id],
                "sender_user_id": sender_id,
                "sent_at": msg.get("sent_at", ""),
                "sent_at_display": format_timestamp(msg.get("sent_at", "")),
                "is_mine": sender_id == session.get("user_id"),
            })
        return enriched

    def validate_message(text):
        """Validate a chat message before saving."""
        if not text or not text.strip():
            return False, "Message cannot be empty."
        if len(text) > 500:
            return False, "Message cannot exceed 500 characters."
        return True, None

    def get_match_messages(match_id, limit=50, skip=0):
        """Fetch paginated messages for a match."""
        messages = list(
            db.messages.find({"match_id": match_id})
            .sort("sent_at", 1)
            .skip(skip)
            .limit(limit)
        )
        return enrich_messages(messages)

    def user_is_in_match(match):
        """Check if the current user is part of this match."""
        user_id = session.get("user_id")
        return (
            match.get("solver_user_id") == user_id
            or match.get("target_user_id") == user_id
        )

    # ------- chat routes -------
    @app.route("/matches/<match_id>/chat")
    def chat(match_id):
        """Main chat page for a match."""
        try:
            match = db.matches.find_one({"_id": ObjectId(match_id)})
        except InvalidId:
            match = None
        if match is None:
            return render_template("404.html"), 404
        if not user_is_in_match(match):
            return render_template("404.html"), 404

        partner = get_chat_partner(match)
        messages = get_match_messages(match_id)
        total_messages = db.messages.count_documents({"match_id": match_id})

        return render_template(
            "chat.html",
            match_id=match_id,
            messages=messages,
            partner=partner,
            total_messages=total_messages,
        )

    @app.route("/matches/<match_id>/chat/history")
    def chat_history(match_id):
        """API endpoint to load older messages (pagination)."""
        try:
            match = db.matches.find_one({"_id": ObjectId(match_id)})
        except InvalidId:
            return {"error": "Match not found"}, 404
        if match is None or not user_is_in_match(match):
            return {"error": "Unauthorized"}, 403

        skip = int(request.args.get("skip", 0))
        limit = int(request.args.get("limit", 20))
        messages = get_match_messages(match_id, limit=limit, skip=skip)
        return {"messages": messages, "skip": skip, "limit": limit}

    @app.route("/matches/<match_id>/chat/send", methods=["POST"])
    def chat_send(match_id):
        """HTTP fallback endpoint to send a message without WebSocket."""
        try:
            match = db.matches.find_one({"_id": ObjectId(match_id)})
        except InvalidId:
            return {"error": "Match not found"}, 404
        if match is None or not user_is_in_match(match):
            return {"error": "Unauthorized"}, 403

        text = (request.form.get("text") or "").strip()
        valid, error = validate_message(text)
        if not valid:
            return {"error": error}, 400

        sender_id = session.get("user_id")
        msg = {
            "match_id": match_id,
            "sender_user_id": sender_id,
            "text": text,
            "sent_at": datetime.utcnow().isoformat(),
        }
        db.messages.insert_one(msg)
        return {"status": "ok"}

    # ------- socketio events -------
    @socketio.on("join")
    def on_join(data):
        """User joins a chat room for a specific match."""
        match_id = data.get("match_id")
        if not match_id:
            return
        join_room(match_id)
        user_id = session.get("user_id")
        try:
            user = db.users.find_one({"_id": ObjectId(user_id)})
            username = user.get("username", "Someone") if user else "Someone"
        except Exception:
            username = "Someone"
        emit("user_joined", {"username": username, "match_id": match_id}, to=match_id)

    @socketio.on("send_message")
    def handle_message(data):
        """Handle an incoming chat message from a client."""
        match_id = data.get("match_id")
        text = (data.get("text") or "").strip()
        sender_id = session.get("user_id")

        if not match_id or not sender_id:
            emit("error", {"message": "Invalid session."})
            return

        valid, error = validate_message(text)
        if not valid:
            emit("error", {"message": error})
            return

        try:
            match = db.matches.find_one({"_id": ObjectId(match_id)})
        except Exception:
            emit("error", {"message": "Match not found."})
            return

        if match is None or not user_is_in_match(match):
            emit("error", {"message": "You are not part of this match."})
            return

        try:
            sender = db.users.find_one({"_id": ObjectId(sender_id)})
            sender_username = sender.get("username", "Unknown") if sender else "Unknown"
        except Exception:
            sender_username = "Unknown"

        msg = {
            "match_id": match_id,
            "sender_user_id": sender_id,
            "sender_username": sender_username,
            "text": text,
            "sent_at": datetime.utcnow().isoformat(),
        }
        db.messages.insert_one(msg)
        msg.pop("_id", None)
        msg["sent_at_display"] = format_timestamp(msg["sent_at"])
        msg["is_mine"] = False
        emit("receive_message", msg, to=match_id)

    @socketio.on("typing")
    def handle_typing(data):
        """Broadcast typing indicator to the other user in the chat room."""
        match_id = data.get("match_id")
        user_id = session.get("user_id")
        if not match_id or not user_id:
            return
        try:
            user = db.users.find_one({"_id": ObjectId(user_id)})
            username = user.get("username", "Someone") if user else "Someone"
        except Exception:
            username = "Someone"
        emit("user_typing", {"username": username}, to=match_id, include_self=False)

    @socketio.on("stop_typing")
    def handle_stop_typing(data):
        """Broadcast stop typing indicator."""
        match_id = data.get("match_id")
        if not match_id:
            return
        emit("user_stopped_typing", {}, to=match_id, include_self=False)

    return app, socketio


app, socketio = create_app()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8000)

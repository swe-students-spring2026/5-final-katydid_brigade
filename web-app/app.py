from datetime import date

from flask import Flask, redirect, render_template, request, url_for


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY="dev",
    )

    if test_config:
        app.config.update(test_config)

    sample_user = {
        "username": "example_user",
        "profile_pic": "https://placehold.co/160x160?text=Profile",
        "age": 21,
        "gender": "Not set",
        "email": "example_user@example.com",
        "questions": [
            {"question": "Favorite music genre?", "answer": "Jazz"},
            {"question": "Dream travel spot?", "answer": "Germany"},
            {"question": "Favorite hobby?", "answer": "Coding"},
        ],
    }

    daily_candidate = {
        "username": "morgan",
        "profile_pic": "https://placehold.co/160x160?text=Match",
        "age": 22,
        "gender": "Not set",
        "questions": [
            {"question": "Favorite music genre?", "answer": ""},
            {"question": "Dream travel spot?", "answer": ""},
            {"question": "Favorite hobby?", "answer": ""},
            {"question": "Favorite food?", "answer": ""},
            {"question": "Favorite movie type?", "answer": ""},
            {"question": "Best school subject?", "answer": ""},
            {"question": "Morning or night?", "answer": ""},
            {"question": "Favorite season?", "answer": ""},
            {"question": "Coffee or tea?", "answer": ""},
            {"question": "Favorite game?", "answer": ""},
        ],
    }

    matches = [
        {
            "id": 1,
            "username": "morgan",
            "profile_pic": "https://placehold.co/128x128?text=M",
            "age": 22,
            "gender": "Not set",
            "email": "morgan@example.com",
            "questions": [
                {"question": "Favorite music genre?", "answer": "Jazz"},
                {"question": "Dream travel spot?", "answer": "Germany"},
                {"question": "Favorite hobby?", "answer": "Coding"},
            ],
        }
    ]

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            return redirect(url_for("dashboard"))
        return render_template("login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            return redirect(url_for("setup"))
        return render_template("register.html")

    @app.route("/setup", methods=["GET", "POST"])
    def setup():
        if request.method == "POST":
            return redirect(url_for("dashboard"))
        return render_template("setup.html")

    @app.route("/dashboard", methods=["GET", "POST"])
    def dashboard():
        result = None
        if request.method == "POST":
            result = {
                "score": 10,
                "total": 10,
                "matched": True,
            }
        return render_template(
            "dashboard.html",
            candidate=daily_candidate,
            today=date.today(),
            result=result,
        )

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
    app.run(debug=True)

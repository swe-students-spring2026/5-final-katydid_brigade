"""Flask Web app - backend for Word Game and Matchmaking"""

import os

from datetime import date
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
  app.run(host="0.0.0.0", port=8000)

"""Flask Web app - backend for Word Game and Matchmaking"""

import request
from flask import Flask, jsonify, request
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)

# register

# login

# generate puzzle

# save answers

# get answers

# find matches

# get matches

if __name__ == "__main__":
  app = create_aapp()
  app.run(host="0.0.0.0", port=5000,m debug=True)
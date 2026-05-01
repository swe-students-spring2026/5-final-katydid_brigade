This subsystem contains the Boggle-based puzzle engine for the dating game.

Current scope:
- normalize and validate answer words
- generate a 4x4 Boggle board that contains the hidden answer
- evaluate guesses with a 5-attempt limit
- support daily puzzle sessions in the app layer
- serialize puzzle, attempt, and match records for MongoDB storage
- expose the engine as a containerized HTTP service

Run locally:
- install dependencies from `requirements.txt`
- start the API with `uvicorn game_engine.api:app --host 0.0.0.0 --port 8000`

Container:
- build with `docker build -t game-engine ./game-engine`
- run with `docker run -p 8000:8000 game-engine`

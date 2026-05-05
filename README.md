[![Tests](https://github.com/swe-students-spring2026/5-final-katydid_brigade/actions/workflows/tests.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-katydid_brigade/actions/workflows/tests.yml)
[![Event Logger](https://github.com/swe-students-spring2026/5-final-katydid_brigade/actions/workflows/event-logger.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-katydid_brigade/actions/workflows/event-logger.yml)

# Most Puzzling

Most Puzzling is a boggle word game where users answer a set of questions designed by other players, and if their responses match with another user's answers, the two get connected.

## Container Images

- [Game Engine](https://hub.docker.com/r/g1nny2470/bogglebond-game-engine) — Python service that generates boggle word puzzles from user generated information
- [Web App](https://hub.docker.com/r/g1nny2470/bogglebond-web-app) — Flask web application that handles user registration, profile setup, puzzle gameplay, and matchmaking

## Team Member

- [Marcus Song](https://github.com/Marclous)
- [Chen Chen](https://github.com/LoganHund)
- [Chenyu (Ginny) Jiang](https://github.com/ginny1536)
- [Bryce](https://github.com/blin03)

## Running the Project

### Requirements

- [Docker](https://www.docker.com/get-started) and Docker Compose installed
- A [MongoDB Atlas](https://www.mongodb.com/atlas) account with a free cluster (Remember to save your user credentials)

### 1. Clone the repository

```sh
git clone https://github.com/swe-students-spring2026/5-final-katydid_brigade.git
cd 5-final-katydid_brigade
```

### 2. Set up environment variables

Copy the example env file and fill in your values:

```sh
cp .env.example .env
```

Open `.env` and set:

- `MONGO_URI` — your Atlas connection string (see below)
- `SECRET_KEY` — any random secret string

**Getting your Atlas connection string:**
1. Go to your Atlas cluster → **Connect** → **Drivers**
2. Copy the `mongodb+srv://...` URI
3. Replace `<username>` and `<password>` with your Atlas database user credentials 
4. If your password contains special characters (e.g. `>`, `@`, `:`), percent-encode them (e.g. `>` → `%3E`)

### 3. Build and start all containers

```sh
docker compose up --build
```

Then open http://localhost:8000.

### 4. Stop the app

```sh
docker compose down
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `MONGO_URI` | MongoDB Atlas connection string (`mongodb+srv://user:pass@cluster.mongodb.net/`) |
| `DB_NAME` | MongoDB database name (default: `katydid_brigade`) |
| `GAME_ENGINE_URL` | Internal URL of the game engine (default: `http://game-engine:8000`) |
| `SECRET_KEY` | Flask session secret — use a long random string in production |

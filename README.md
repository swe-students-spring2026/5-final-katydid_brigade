[![Tests](https://github.com/swe-students-spring2026/5-final-katydid_brigade/actions/workflows/tests.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-katydid_brigade/actions/workflows/tests.yml)
[![Event Logger](https://github.com/swe-students-spring2026/5-final-katydid_brigade/actions/workflows/event-logger.yml/badge.svg)](https://github.com/swe-students-spring2026/5-final-katydid_brigade/actions/workflows/event-logger.yml)

# Most Puzzling

Most Puzzling is a boggle word game where users answer a set of questions designed by other players, and if their responses match with another user's answers, the two get connected.

## Container Images

- Needs to be added after finishing developing

## Team Member

- [Marcus Song](https://github.com/Marclous)
- [Chen Chen](https://github.com/LoganHund)
- [Chenyu (Ginny) Jiang](https://github.com/ginny1536)
- [Bryce](https://github.com/blin03)

## Running the Project

### Requirements

- [Docker](https://www.docker.com/get-started) and Docker Compose installed

### 1. Clone the repository

```sh
git clone https://github.com/swe-students-spring2026/5-final-katydid_brigade.git
```

### 2. Build and start all containers

```sh
docker compose up --build
```

Then open http://localhost:8000.

### 3. Stop the app 

```sh
docker compose down
```

You can also build and run without Compose:

```sh
docker build -t katydid-web-app .
docker run --rm -p 8000:8000 katydid-web-app
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGO_URI` | `mongodb://mongodb:27017/` | MongoDB connection string |
| `DB_NAME` | `katydid_brigade` | MongoDB database name |
| `GAME_ENGINE_URL` | `http://game-engine:8000` | Internal URL of the game engine |
| `SECRET_KEY` | `changeme` | Flask session secret key — change in production |

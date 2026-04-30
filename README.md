# Final Project

An exercise to put to practice software development teamwork, subsystem communication, containers, deployment, and CI/CD pipelines. See [instructions](./instructions.md) for details.

[google docs link](https://docs.google.com/document/d/1WeUMGPfgl9XSXB4mm2ZGT3RHffOebC95FUaW_X-auVc/edit?tab=t.0)

## Run the web app with Docker

Build and start the container:

```sh
docker compose up --build
```

Then open http://localhost:8000.

To stop the app, press `Ctrl+C`, then run:

```sh
docker compose down
```

You can also build and run without Compose:

```sh
docker build -t katydid-web-app .
docker run --rm -p 8000:8000 katydid-web-app
```

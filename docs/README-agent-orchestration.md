# Master Chief (chief orchestrator) - README

This directory contains scaffolding for a minimal orchestrator ("Master Chief") that coordinates two AI agents: a marketing agent and a schedule planner. The stack uses Python + FastAPI and Redis.

Quick start (docker-compose - recommended)
1. Create a .env with the following values (optional):
   GITHUB_REPO=Wmoi53/multiply
   GITHUB_TOKEN=ghp_xxx
2. Run:
   docker-compose up --build
3. POST tasks to the orchestrator:
   curl -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d '{"type":"marketing_brief","agent_label":"marketing","payload":{"topic":"Multiply v1","audience":"devs"}}'

Notes
- Outputs: by default the agents will create GitHub issues if GITHUB_TOKEN and GITHUB_REPO are provided; otherwise outputs are written to the outputs/ directory.
- Task persistence: lightweight queue in Redis and simple file outputs. For production consider adding durable state (SQLite/Postgres) and proper retry/backoff.
- The chief agent is labeled "Master Chief" in the code and docs.

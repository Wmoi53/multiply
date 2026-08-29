from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, Field
import uuid
import os
import json
import redis.asyncio as aioredis
from .task_schema import Task

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis = aioredis.from_url(REDIS_URL)

app = FastAPI(title="Master Chief Orchestrator")


@app.post("/tasks")
async def create_task(task: Task):
    task_id = str(uuid.uuid4())
    payload = task.dict()
    payload.update({"id": task_id, "status": "queued"})
    await redis.lpush("tasks", json.dumps(payload))
    return {"task_id": task_id, "status": "queued"}


@app.get("/health")
async def health():
    return {"status": "ok", "role": "Master Chief Orchestrator"}

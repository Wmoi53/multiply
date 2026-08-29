"""Schedule planner agent: polls Redis for tasks labeled 'schedule'.
Generates simple timeline suggestions and writes output.
"""
import os
import time
import json
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_client = redis.from_url(REDIS_URL)

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))


def handle_schedule_task(task: dict):
    payload = task.get("payload", {})
    project = payload.get("project", "Unnamed Project")
    milestones = payload.get("milestones", [])

    # Simple timeline generation (placeholder)
    timeline = f"Schedule for {project}\n"
    for i, m in enumerate(milestones, start=1):
        timeline += f"- Week {i}: {m}\n"

    print("[schedule_agent] Completed task:", task.get("id"))
    out_dir = os.getenv("OUTPUT_DIR", "outputs")
    os.makedirs(out_dir, exist_ok=True)
    fname = os.path.join(out_dir, f"schedule_{task.get('id')}.md")
    with open(fname, "w") as f:
        f.write(timeline)
    print("Wrote output to", fname)


def poll_loop():
    print("[schedule_agent] Starting poll loop. Watching Redis list 'tasks'")
    while True:
        item = redis_client.rpop("tasks")
        if item:
            task = json.loads(item)
            if task.get("agent_label") == "schedule":
                handle_schedule_task(task)
            else:
                # not for us — requeue
                redis_client.lpush("tasks", json.dumps(task))
        else:
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    poll_loop()

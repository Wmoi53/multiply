"""Marketing agent adapter: polls Redis for tasks labeled 'marketing'.

This is a minimal example that demonstrates polling, handling, and optional
GitHub issue creation if GITHUB_TOKEN is provided.
"""
import os
import time
import json
import requests
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_client = redis.from_url(REDIS_URL)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")  # e.g. Wmoi53/multiply

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))


def create_github_issue(title: str, body: str):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("GitHub credentials not provided, skipping issue creation")
        return None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    data = {"title": title, "body": body, "labels": ["agent:marketing"]}
    r = requests.post(url, headers=headers, json=data)
    if r.status_code == 201:
        return r.json().get("html_url")
    else:
        print("Failed to create issue:", r.status_code, r.text)
        return None


def handle_marketing_task(task: dict):
    # Example: synthesize a marketing brief from payload
    payload = task.get("payload", {})
    topic = payload.get("topic", "(no topic)")
    audience = payload.get("audience", "general")
    deliverable = payload.get("deliverable", "social-post")

    # Fake generation logic — replace with calls to LLMs or templates.
    content = f"Marketing deliverable for '{topic}'\nAudience: {audience}\nType: {deliverable}\n\nSuggested copy:\n"
    content += f"Short: Introducing {topic} — designed for {audience}. Learn more at <link>. #multiply\n"

    print("[marketing_agent] Completed task:", task.get("id"))

    # Optionally create a GitHub issue to record the output
    issue_url = create_github_issue(f"Marketing: {topic}", content)
    if issue_url:
        print("Created issue:", issue_url)
    else:
        # fallback: write to outputs/ directory
        out_dir = os.getenv("OUTPUT_DIR", "outputs")
        os.makedirs(out_dir, exist_ok=True)
        fname = os.path.join(out_dir, f"marketing_{task.get('id')}.md")
        with open(fname, "w") as f:
            f.write(content)
        print("Wrote output to", fname)


def poll_loop():
    print("[marketing_agent] Starting poll loop. Watching Redis list 'tasks'")
    while True:
        item = redis_client.rpop("tasks")
        if item:
            task = json.loads(item)
            if task.get("agent_label") == "marketing":
                handle_marketing_task(task)
            else:
                # not for us — requeue
                redis_client.lpush("tasks", json.dumps(task))
        else:
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    poll_loop()

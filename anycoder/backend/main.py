"""
AnyCoder-lite backend: FastAPI service that streams AI-generated code from
Hugging Face-hosted models, and can one-click-deploy the result to a new
Hugging Face Space.

Run locally:
    pip install -r requirements.txt
    HF_TOKEN=hf_xxx uvicorn main:app --reload --port 7860

See ../README.md for the full setup (env vars, running the frontend,
deploying this whole app to a Space).
"""

import json
import os
from pathlib import Path
from typing import Iterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from huggingface_hub import HfApi, InferenceClient
from pydantic import BaseModel

app = FastAPI(title="AnyCoder-lite")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to your frontend's origin in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Same model lineup AnyCoder itself advertises (huggingface.co/spaces/akhaliq/anycoder).
SUPPORTED_MODELS = {
    "MiniMax M2.5": "MiniMaxAI/MiniMax-M2.5",
    "GLM 5": "zai-org/GLM-5",
    "Qwen3 Coder Next": "Qwen/Qwen3-Coder-Next",
    "Kimi K2.5": "moonshotai/Kimi-K2.5",
    "GLM 4.7 Flash": "zai-org/GLM-4.7-Flash",
    "GLM 4.7": "zai-org/GLM-4.7",
    "MiniMax M2.1": "MiniMaxAI/MiniMax-M2.1",
    "GLM 4.6": "zai-org/GLM-4.6",
    "DeepSeek V3": "deepseek-ai/DeepSeek-V3",
    "DeepSeek R1": "deepseek-ai/DeepSeek-R1",
    "MiniMax M2": "MiniMaxAI/MiniMax-M2",
    "Kimi K2 Thinking": "moonshotai/Kimi-K2-Thinking",
}

LANGUAGE_SYSTEM_PROMPTS = {
    "html": (
        "You are an expert frontend developer. Generate a single, complete, "
        "self-contained index.html file (inline <style> and <script>, no "
        "external build step) for the user's request. Respond with only the "
        "code, in one ```html fenced block, no explanation before or after."
    ),
    "react": (
        "You are an expert React developer. Generate a single, complete React "
        "component (App.tsx) implementing the user's request, using only "
        "React and inline styles or Tailwind utility classes (no other "
        "external dependencies). Respond with only the code, in one "
        "```tsx fenced block, no explanation before or after."
    ),
    "python-gradio": (
        "You are an expert Gradio developer. Generate a single, complete "
        "app.py implementing the user's request as a Gradio app (gr.Blocks "
        "or gr.Interface). Respond with only the code, in one ```python "
        "fenced block, no explanation before or after."
    ),
    "python-streamlit": (
        "You are an expert Streamlit developer. Generate a single, complete "
        "app.py implementing the user's request as a Streamlit app. Respond "
        "with only the code, in one ```python fenced block, no explanation "
        "before or after."
    ),
}

DEPLOY_SDK = {
    "html": "static",
    "react": "static",
    "python-gradio": "gradio",
    "python-streamlit": "streamlit",
}
DEPLOY_ENTRY_FILE = {
    "html": "index.html",
    "react": "index.html",
    "python-gradio": "app.py",
    "python-streamlit": "app.py",
}


class GenerateRequest(BaseModel):
    prompt: str
    model: str = "DeepSeek V3"
    language: str = "html"
    hf_token: str | None = None  # dev-mode: bring your own token from the browser


class DeployRequest(BaseModel):
    code: str
    space_name: str
    language: str = "html"
    hf_token: str | None = None


def _resolve_token(request_token: str | None) -> str:
    token = request_token or os.environ.get("HF_TOKEN")
    if not token:
        raise HTTPException(
            status_code=401,
            detail="No HF token available. Set HF_TOKEN on the server, or paste a "
            "token in the frontend's dev-mode field.",
        )
    return token


def _strip_code_fence(text: str) -> str:
    """Best-effort: pull the contents out of a single ```lang ... ``` block."""
    if "```" not in text:
        return text.strip()
    parts = text.split("```")
    # parts[0] is prose before the fence; parts[1] is "lang\ncode..."
    if len(parts) < 2:
        return text.strip()
    block = parts[1]
    lines = block.split("\n", 1)
    return (lines[1] if len(lines) > 1 else block).strip()


@app.get("/api/models")
def list_models() -> dict:
    return {"models": list(SUPPORTED_MODELS.keys()), "languages": list(LANGUAGE_SYSTEM_PROMPTS.keys())}


@app.post("/api/generate")
def generate(req: GenerateRequest) -> StreamingResponse:
    if req.model not in SUPPORTED_MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown model: {req.model}")
    if req.language not in LANGUAGE_SYSTEM_PROMPTS:
        raise HTTPException(status_code=400, detail=f"Unknown language: {req.language}")

    token = _resolve_token(req.hf_token)
    client = InferenceClient(model=SUPPORTED_MODELS[req.model], token=token)
    messages = [
        {"role": "system", "content": LANGUAGE_SYSTEM_PROMPTS[req.language]},
        {"role": "user", "content": req.prompt},
    ]

    def event_stream() -> Iterator[str]:
        try:
            for chunk in client.chat_completion(messages=messages, stream=True, max_tokens=4096):
                delta = chunk.choices[0].delta.content
                if delta:
                    yield f"data: {json.dumps({'token': delta})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as exc:  # surface the error to the frontend instead of a bare 500
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/deploy")
def deploy(req: DeployRequest) -> dict:
    if req.language not in DEPLOY_SDK:
        raise HTTPException(status_code=400, detail=f"Unknown language: {req.language}")

    token = _resolve_token(req.hf_token)
    api = HfApi(token=token)
    whoami = api.whoami()
    repo_id = f"{whoami['name']}/{req.space_name}"

    api.create_repo(repo_id=repo_id, repo_type="space", space_sdk=DEPLOY_SDK[req.language], exist_ok=True)
    api.upload_file(
        path_or_fileobj=req.code.encode("utf-8"),
        path_in_repo=DEPLOY_ENTRY_FILE[req.language],
        repo_id=repo_id,
        repo_type="space",
    )
    return {"space_url": f"https://huggingface.co/spaces/{repo_id}"}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# In the Docker image (see ../Dockerfile), the frontend is pre-built into
# frontend/dist and copied next to this file as ./static. Mounted last so it
# never shadows the /api/* routes above. In local dev (`npm run dev`), this
# directory doesn't exist and the frontend's own dev server is used instead.
_static_dir = Path(__file__).parent / "static"
if _static_dir.is_dir():
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")

# AnyCoder-lite

A scoped clone of [akhaliq/anycoder](https://huggingface.co/spaces/akhaliq/anycoder):
describe an app in plain English, stream back generated code from a
Hugging Face-hosted model, and deploy the result as a new Hugging Face Space
— all in one page.

What's the same as the original: the exact model lineup from its README,
streamed generation via SSE, multiple output formats, and one-click Space
deployment.

What's different / simplified: no Hugging Face OAuth (needs a registered
OAuth app to test properly) — instead there's a "dev mode" token field in
the frontend, matching what the original's own README calls its local-dev
fallback. No Next.js — a plain Vite/React frontend, which is lighter and
covers the same UI needs (prompt box, model/format pickers, streaming
output, live HTML preview, deploy button).

## Architecture

```
anycoder/
├── backend/
│   ├── main.py            # FastAPI: /api/generate (SSE stream), /api/deploy, /api/models
│   └── requirements.txt
├── frontend/               # Vite + React + TypeScript
│   └── src/{main.tsx,App.tsx,api.ts}
├── Dockerfile               # Builds frontend, serves it + the API from one port
└── .env.example
```

## Run locally

**Backend:**
```bash
cd anycoder/backend
pip install -r requirements.txt
export HF_TOKEN=hf_xxx   # https://huggingface.co/settings/tokens (needs Inference API access)
uvicorn main:app --reload --port 7860
```

**Frontend** (separate terminal):
```bash
cd anycoder/frontend
npm install
npm run dev
```
Open the URL Vite prints (typically `http://localhost:5173`). Vite proxies
`/api/*` to the backend on port 7860 (see `vite.config.ts`).

If you don't want to set `HF_TOKEN` on the backend, leave it unset and
instead paste a token into the "HF token (dev mode)" field in the UI — it's
kept in `localStorage` and sent with each request.

## Deploy as a Hugging Face Space

```bash
cd anycoder
docker build -t anycoder-lite .
docker run -p 7860:7860 --env-file .env anycoder-lite
```
Push this directory to a new Space with `sdk: docker` (matching the
`Dockerfile` here) and set `HF_TOKEN` as a Space secret — or leave it unset
and let each visitor supply their own token via dev mode.

## API

- `GET /api/models` — supported models + output formats.
- `POST /api/generate` — `{prompt, model, language, hf_token?}` → Server-Sent
  Events stream of `{token}` chunks, ending in `{done: true}` (or
  `{error}`).
- `POST /api/deploy` — `{code, space_name, language, hf_token?}` → creates
  (or updates) `<your-username>/<space_name>` on the Hub with the generated
  code and returns its URL.

#!/bin/bash
set -euo pipefail

# Only run this setup in Claude Code on the web (remote) sessions.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# All scripts in agent/ are self-contained "uv scripts" (PEP 723 inline
# metadata) run via `uv run agent/<script>.py`. Make sure uv is present.
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$CLAUDE_ENV_FILE"

# Warm uv's shared package cache with the lightweight dependencies used by
# agent/run_agent.py and agent/run_agentworld.py, so the first `uv run` of
# either script doesn't pay a cold-download cost. This is cached across
# sessions by the container, so it's a no-op after the first run.
# (Skips the heavy whisper/gmail deps — torch/transformers/accelerate/
# google-api-python-client — since those scripts are opt-in and rarely run.)
uv pip install --system --quiet huggingface_hub requests smolagents openai

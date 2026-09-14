# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "openai>=1.40",
# ]
# ///
"""
Drive Qwen-AgentWorld-35B-A3B (https://huggingface.co/Qwen/Qwen-AgentWorld-35B-A3B)
as a language world model: given an agent's action (+ prior interaction
history), it predicts the next environment observation. Talks to an
OpenAI-compatible endpoint, so it needs a server already running the model
(vLLM or SGLang) rather than loading the 35B checkpoint itself.

Start a server first, e.g. with vLLM:
    vllm serve Qwen/Qwen-AgentWorld-35B-A3B \\
        --port 8000 --tensor-parallel-size 4 \\
        --max-model-len 262144 --reasoning-parser qwen3 \\
        --language-model-only --trust-remote-code

Then, one-shot:
    python agent/run_agentworld.py --domain terminal "ls -la /home/user/project/"

Or interactively, keeping the action/observation history in context:
    python agent/run_agentworld.py --domain terminal --interactive

See agent/agentworld-setup.md for the full setup (server flags, domain
notes, HF Jobs deployment).
"""

import argparse
import os

from openai import OpenAI

BASE_URL = os.environ.get("AGENTWORLD_BASE_URL", "http://localhost:8000/v1")
API_KEY = os.environ.get("AGENTWORLD_API_KEY", "EMPTY")
MODEL = os.environ.get("AGENTWORLD_MODEL", "Qwen/Qwen-AgentWorld-35B-A3B")

# Short stand-in prompts for the 7 domains the model was trained on. Swap
# these for the official versions in prompts/<domain>/system_prompt.txt at
# https://github.com/QwenLM/Qwen-AgentWorld for best simulation fidelity.
DOMAIN_SYSTEM_PROMPTS = {
    "mcp": (
        "You are a language world model simulating an MCP (Model Context "
        "Protocol) tool-calling environment. Given the agent's tool call, "
        "predict the tool's response."
    ),
    "search": (
        "You are a language world model simulating a web search engine. "
        "Given the agent's search query, predict the search results page."
    ),
    "terminal": (
        "You are a language world model simulating a Linux terminal "
        "environment. Given the user's command, predict the terminal output."
    ),
    "swe": (
        "You are a language world model simulating a software engineering "
        "environment (a code repository plus its build/test tooling). Given "
        "the agent's action (edit, run tests, etc.), predict the resulting "
        "tool output or diff."
    ),
    "android": (
        "You are a language world model simulating an Android device UI. "
        "Given the agent's action (tap, swipe, type), predict the resulting "
        "screen state."
    ),
    "web": (
        "You are a language world model simulating a web browser. Given the "
        "agent's action (click, type, navigate), predict the resulting page "
        "state."
    ),
    "os": (
        "You are a language world model simulating a desktop operating "
        "system UI. Given the agent's action, predict the resulting screen "
        "state."
    ),
}


def simulate(client: OpenAI, domain: str, history: list[dict], action: str) -> str:
    """Send one action to the world model and return the predicted observation.

    Args:
        client: An OpenAI client pointed at the vLLM/SGLang server.
        domain: One of DOMAIN_SYSTEM_PROMPTS' keys.
        history: Prior [{"role": ..., "content": ...}, ...] turns to keep in
            context (excludes the system prompt).
        action: The agent's action for this step, e.g. a shell command.

    Returns:
        The model's predicted environment observation (its full reply).
    """
    messages = [{"role": "system", "content": DOMAIN_SYSTEM_PROMPTS[domain]}]
    messages.extend(history)
    messages.append({"role": "user", "content": action})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=32768,
        temperature=0.6,
        top_p=0.95,
    )
    return response.choices[0].message.content


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", nargs="?", help="Action to simulate, e.g. a shell command (omit with --interactive)")
    parser.add_argument("--domain", choices=sorted(DOMAIN_SYSTEM_PROMPTS), default="terminal")
    parser.add_argument("--interactive", action="store_true", help="Loop, keeping action/observation history in context")
    args = parser.parse_args()

    if not args.interactive and not args.action:
        parser.error("provide an action, or pass --interactive")

    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    history: list[dict] = []

    if not args.interactive:
        observation = simulate(client, args.domain, history, args.action)
        print(observation)
        return

    print(f"[{args.domain}] interactive world-model session — Ctrl-D to quit")
    while True:
        try:
            action = input("action> ")
        except EOFError:
            break
        if not action.strip():
            continue
        observation = simulate(client, args.domain, history, action)
        print(observation)
        history.append({"role": "user", "content": action})
        history.append({"role": "assistant", "content": observation})


if __name__ == "__main__":
    main()

# Running `run_agentworld.py` (Qwen-AgentWorld-35B-A3B)

[Qwen-AgentWorld-35B-A3B](https://huggingface.co/Qwen/Qwen-AgentWorld-35B-A3B)
is Qwen's official language world model: given an agent's action plus its
prior interaction history, it predicts the next environment observation
across 7 domains (MCP tool calling, Search, Terminal, SWE, Android, Web,
OS). `run_agentworld.py` drives it over an OpenAI-compatible endpoint.

## 1. Start a server

The model itself (35B total / 3B active params, MoE, 262K context) needs a
GPU server — `run_agentworld.py` only talks to it over HTTP, it never loads
the checkpoint locally.

**vLLM:**
```bash
pip install -U vllm
vllm serve Qwen/Qwen-AgentWorld-35B-A3B \
    --port 8000 --tensor-parallel-size 4 \
    --max-model-len 262144 --reasoning-parser qwen3 \
    --language-model-only --trust-remote-code
```
`--language-model-only` is required: the checkpoint only has language-model
weights even though the architecture defines visual components — without
the flag vLLM tries to init the vision stack and fails.

**SGLang:**
```bash
pip install -U sglang
python -m sglang.launch_server \
    --model-path Qwen/Qwen-AgentWorld-35B-A3B \
    --port 8000 --tp-size 4 --context-length 262144 \
    --reasoning-parser qwen3
```

Both expose an OpenAI-compatible API at `http://localhost:8000/v1`. Adjust
`--tensor-parallel-size`/`--tp-size` to however many GPUs you have; if you
hit OOM, reduce `--max-model-len`/`--context-length` (Qwen recommends
keeping at least 128K for genuine multi-turn simulation).

## 2. Run the script

```bash
pip install openai   # only dependency; `uv run agent/run_agentworld.py ...` also works

# One-shot: simulate a single action
python agent/run_agentworld.py --domain terminal "ls -la /home/user/project/"

# Interactive: keeps action/observation history in context across turns
python agent/run_agentworld.py --domain terminal --interactive
```

`--domain` is one of `mcp`, `search`, `terminal`, `swe`, `android`, `web`,
`os`. Point it at a remote server instead of localhost with:

```bash
AGENTWORLD_BASE_URL=http://<host>:8000/v1 python agent/run_agentworld.py ...
```

## 3. Better simulation fidelity: official domain prompts

`run_agentworld.py` ships short built-in system prompts per domain so it's
runnable out of the box. For higher-fidelity simulation, swap in the
official `system_prompt.txt` for your domain from
[QwenLM/Qwen-AgentWorld/prompts](https://github.com/QwenLM/Qwen-AgentWorld/tree/master/prompts)
— replace the relevant entry in `DOMAIN_SYSTEM_PROMPTS` in the script.

## 4. Make it recurring / run on Hugging Face Jobs

Same pattern as `run_agent.py` (`schedule.md`), but note the *server*
(vLLM/SGLang) is the part that needs a GPU — `run_agentworld.py` itself is
lightweight and can run anywhere with network access to that server,
including a `cpu-basic` HF Job:

```bash
hf jobs uv run --flavor cpu-basic \
  --env AGENTWORLD_BASE_URL="http://<your-gpu-host>:8000/v1" \
  --env AGENTWORLD_DOMAIN=terminal \
  agent/run_agentworld.py --domain terminal "ls -la /home/user/project/"
```

Use `hf jobs scheduled run --schedule "..."` (see `schedule.md`) if you want
this polling on a cadence instead of run-once.

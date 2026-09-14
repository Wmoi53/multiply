# multiply
agent multi tasking for a single project in 60days

## Recurring agent scaffold

`agent/run_agent.py` is a self-contained smolagents script (fetch odds ->
compute fair probabilities -> append to a HF dataset tracker). It runs
locally or as a one-off/recurring Hugging Face Job — see
[`agent/schedule.md`](agent/schedule.md) for the exact commands and
[`agent/.env.example`](agent/.env.example) for required config.

## Qwen-AgentWorld environment simulator

`agent/run_agentworld.py` drives [Qwen-AgentWorld-35B-A3B](https://huggingface.co/Qwen/Qwen-AgentWorld-35B-A3B),
Qwen's official language world model, over an OpenAI-compatible endpoint:
give it an action (a shell command, a click, a tool call) plus prior
history and it predicts the next environment observation, across 7 domains
(MCP, Search, Terminal, SWE, Android, Web, OS). See
[`agent/agentworld-setup.md`](agent/agentworld-setup.md) for starting the
vLLM/SGLang server and running the script one-shot or interactively.

## Semantic textual similarity

`agent/semantic_similarity.py` scores how similar a source sentence is to a
list of candidate sentences, via HF's sentence-similarity Inference API
(`sentence-transformers/msmarco-distilbert-base-tas-b` by default, or pass
`--model` for another, e.g. `sentence-transformers/all-MiniLM-L6-v2`). Pass
`--local` to run fully offline instead (needs
`pip install sentence-transformers`). Requires `HF_TOKEN` for the API path
(see [`agent/.env.example`](agent/.env.example)).

```bash
python agent/semantic_similarity.py "That is a happy person" \
    "That is a happy dog" "That is a very happy person" "Today is a sunny day"
```

## Whisper → Gmail voice transcription

`agent/whisper_transcribe.py` runs [openai/whisper-large-v3](https://huggingface.co/openai/whisper-large-v3)
(locally or via HF's hosted Inference API) and `agent/gmail_voice_transcribe.py`
wires it into Gmail: scans for unread emails with an audio attachment,
transcribes each one, and saves a draft reply with the transcript. See
[`agent/whisper-gmail-setup.md`](agent/whisper-gmail-setup.md) for setup
(Google Cloud OAuth credentials + install steps).

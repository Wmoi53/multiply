# multiply
agent multi tasking for a single project in 60days

## Recurring agent scaffold

`agent/run_agent.py` is a self-contained smolagents script (fetch odds ->
compute fair probabilities -> append to a HF dataset tracker). It runs
locally or as a one-off/recurring Hugging Face Job — see
[`agent/schedule.md`](agent/schedule.md) for the exact commands and
[`agent/.env.example`](agent/.env.example) for required config.

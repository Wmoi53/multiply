# multiply
agent multi tasking for a single project in 60days

## Recurring agent scaffold

`agent/run_agent.py` is a self-contained smolagents script (fetch odds ->
compute fair probabilities -> append to a HF dataset tracker). It runs
locally or as a one-off/recurring Hugging Face Job — see
[`agent/schedule.md`](agent/schedule.md) for the exact commands and
[`agent/.env.example`](agent/.env.example) for required config.

## Whisper → Gmail voice transcription

`agent/whisper_transcribe.py` runs [openai/whisper-large-v3](https://huggingface.co/openai/whisper-large-v3)
(locally or via HF's hosted Inference API) and `agent/gmail_voice_transcribe.py`
wires it into Gmail: scans for unread emails with an audio attachment,
transcribes each one, and saves a draft reply with the transcript. See
[`agent/whisper-gmail-setup.md`](agent/whisper-gmail-setup.md) for setup
(Google Cloud OAuth credentials + install steps).

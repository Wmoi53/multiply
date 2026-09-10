# Whisper Large v3 → Gmail voice transcription

Two scripts:

- **`whisper_transcribe.py`** — standalone Whisper Large v3 transcription
  (from the [model card](https://huggingface.co/openai/whisper-large-v3)),
  local or via HF's hosted Inference API.
- **`gmail_voice_transcribe.py`** — scans your Gmail inbox for unread emails
  with an audio attachment, transcribes each one, and saves a draft reply
  containing the transcript.

## 1. Run Whisper on its own

```bash
pip install transformers torch accelerate huggingface_hub

python agent/whisper_transcribe.py path/to/audio.mp3
```

That downloads `openai/whisper-large-v3` (~6GB) and runs it locally — GPU
strongly recommended (it'll run on CPU but slowly). To skip the local
download entirely, transcribe via HF's hosted Inference API instead:

```bash
export HF_TOKEN=hf_xxx   # from https://huggingface.co/settings/tokens
python agent/whisper_transcribe.py path/to/audio.mp3 --hosted
```

## 2. Wire it into Gmail

This uses the official Gmail API (separate from any Gmail connector this
chat session itself has — that connector's tools aren't callable from a
script you run on your own machine).

**One-time setup:**

1. In [Google Cloud Console](https://console.cloud.google.com/), create a
   project → **APIs & Services → Library** → enable **Gmail API**.
2. **APIs & Services → Credentials → Create Credentials → OAuth client ID**,
   application type **Desktop app**. Download the JSON, save it as
   `agent/credentials.json`.
3. Install deps:
   ```bash
   pip install google-api-python-client google-auth-httplib2 \
       google-auth-oauthlib transformers torch accelerate
   ```

**Run it:**

```bash
cd agent
python gmail_voice_transcribe.py
```

First run opens a browser to authorize Gmail access, then caches a
`token.json` so later runs are non-interactive.

By default it matches `is:unread has:attachment` with an mp3/wav/m4a/ogg
filename — override with `--query` for a different Gmail search. Add
`--hosted` to transcribe via the Inference API instead of downloading the
model locally. Processed emails get labeled `Transcribed` and marked read,
so re-running the script is safe (won't reprocess the same message).

**Note on scope:** the script requests `gmail.modify` (read, label, create
drafts) — it never sends anything itself; you review and send each draft
yourself.

## 3. Make it recurring

Same pattern as `run_agent.py` (see `schedule.md`): put this on a cron job
or `hf jobs scheduled run` if you want it to poll automatically rather than
running by hand. `credentials.json` and `token.json` must be present
wherever it runs — treat both as secrets (already covered by
`agent/.gitignore` alongside `.env`).

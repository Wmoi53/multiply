# Running `run_agent.py` on a recurring schedule (Hugging Face Jobs)

`run_agent.py` is a self-contained [uv script](https://docs.astral.sh/uv/guides/scripts/)
(dependencies declared inline at the top of the file), so Hugging Face Jobs
can run it directly on HF-managed compute with no Docker image to build.

## 1. One-off run (sanity check)

```bash
hf jobs uv run \
  --flavor cpu-basic \
  --secrets HF_TOKEN \
  --env FIXTURES="Arsenal vs Newcastle,Man City vs Chelsea" \
  --env ODDS_DATASET_REPO="<your-username>/epl-ah-tracker" \
  agent/run_agent.py
```

- `--flavor cpu-basic` is enough — the agent only makes API calls, no local
  inference.
- `--secrets HF_TOKEN` pulls your token from `hf auth login` / the HF Jobs
  secrets store rather than putting it in plaintext.
- Add `ODDS_API_URL` / `ODDS_API_KEY` as further `--env`/`--secrets` once a
  real odds provider is wired into `fetch_odds` in `run_agent.py`.

Watch logs with `hf jobs logs <job-id>`, list running jobs with `hf jobs ps`.

## 2. Make it recurring

Hugging Face Jobs' scheduling feature runs the same command on a cron
expression instead of once:

```bash
hf jobs scheduled run \
  --flavor cpu-basic \
  --schedule "0 */6 * * *" \
  --secrets HF_TOKEN \
  --env FIXTURES="Arsenal vs Newcastle,Man City vs Chelsea" \
  --env ODDS_DATASET_REPO="<your-username>/epl-ah-tracker" \
  agent/run_agent.py
```

The example schedule (`0 */6 * * *`) fires every 6 hours. Manage schedules
with:

```bash
hf jobs scheduled ls               # list your scheduled jobs
hf jobs scheduled suspend <id>     # pause
hf jobs scheduled resume  <id>     # resume
hf jobs scheduled delete  <id>     # remove
```

> The `hf jobs scheduled` subcommands are a newer part of the CLI. If your
> installed `huggingface_hub` predates them, run `pip install -U
> huggingface_hub` and confirm with `hf jobs scheduled --help`; the exact
> flags can shift as the feature matures out of beta.

## 3. What "done" looks like

Each run appends one `runs/<timestamp>.jsonl` file to the
`ODDS_DATASET_REPO` dataset on the Hub — a durable, append-only log you (or
another agent) can read back for the fair-probability tracker, without
re-triggering anything by hand. That closes the loop described earlier:
smolagents decides *what* to do each run, HF Jobs' schedule decides *when*.

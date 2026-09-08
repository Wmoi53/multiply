# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "smolagents>=1.15",
#   "huggingface_hub>=0.27",
#   "requests",
# ]
# ///
"""
Recurring smolagents job: fetch fixture odds, compute no-vig fair
probabilities, and append the result to a Hugging Face dataset repo.

Run once, locally:
    HF_TOKEN=hf_xxx FIXTURES="Arsenal vs Newcastle,Man City vs Chelsea" \
        python agent/run_agent.py

Run once, on Hugging Face Jobs (no local machine needed):
    hf jobs uv run --flavor cpu-basic \
        --secrets HF_TOKEN --env FIXTURES="Arsenal vs Newcastle" \
        agent/run_agent.py

Run on a recurring schedule: see agent/schedule.md.
"""

import json
import os
from datetime import datetime, timezone

from huggingface_hub import CommitOperationAdd, HfApi
from smolagents import CodeAgent, InferenceClientModel, tool

DATASET_REPO = os.environ.get("ODDS_DATASET_REPO", "")  # e.g. "your-username/epl-ah-tracker"
FIXTURES = [f.strip() for f in os.environ.get("FIXTURES", "").split(",") if f.strip()]


@tool
def fetch_odds(fixture: str) -> str:
    """Fetch 1X2 odds for one fixture from the configured odds provider.

    Reads ODDS_API_URL / ODDS_API_KEY from the environment. If neither is
    set, returns deterministic mock odds so the pipeline is runnable end
    to end before a real provider is wired in.

    Args:
        fixture: Fixture name, e.g. "Arsenal vs Newcastle".

    Returns:
        A JSON string: {"fixture": ..., "home": ..., "draw": ..., "away": ...}
    """
    api_url = os.environ.get("ODDS_API_URL")
    api_key = os.environ.get("ODDS_API_KEY")

    if api_url:
        import requests

        resp = requests.get(
            api_url,
            params={"fixture": fixture},
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return json.dumps(
            {"fixture": fixture, "home": data["home"], "draw": data["draw"], "away": data["away"]}
        )

    # TODO: replace with your real odds source (e.g. Oddspedia scrape/API).
    mock = {"fixture": fixture, "home": 2.10, "draw": 3.40, "away": 3.20}
    return json.dumps(mock)


@tool
def fair_probabilities(odds_json: str) -> str:
    """Convert 1X2 decimal odds into no-vig ("fair") probabilities.

    Args:
        odds_json: JSON string as returned by fetch_odds, containing
            fixture, home, draw, away decimal odds.

    Returns:
        A JSON string adding fair_home, fair_draw, fair_away (0-1 floats).
    """
    data = json.loads(odds_json)
    inv = {k: 1.0 / data[k] for k in ("home", "draw", "away")}
    overround = sum(inv.values())
    data["fair_home"] = round(inv["home"] / overround, 4)
    data["fair_draw"] = round(inv["draw"] / overround, 4)
    data["fair_away"] = round(inv["away"] / overround, 4)
    return json.dumps(data)


@tool
def append_to_tracker(rows_json: str) -> str:
    """Append rows to the Hugging Face dataset repo used as the tracker.

    Writes one timestamped JSONL file per run under `runs/`. Requires
    ODDS_DATASET_REPO and a write-scoped HF_TOKEN to be set; otherwise
    the rows are only printed (dry run).

    Args:
        rows_json: JSON string of a list of row dicts to append.

    Returns:
        A short status message.
    """
    rows = json.loads(rows_json)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = "\n".join(json.dumps(r) for r in rows).encode("utf-8")

    if not DATASET_REPO:
        print(f"[dry run] would append {len(rows)} rows:\n{payload.decode()}")
        return "dry run: ODDS_DATASET_REPO not set, nothing pushed"

    api = HfApi()
    api.create_repo(DATASET_REPO, repo_type="dataset", exist_ok=True)
    api.create_commit(
        repo_id=DATASET_REPO,
        repo_type="dataset",
        operations=[CommitOperationAdd(path_in_repo=f"runs/{stamp}.jsonl", path_or_fileobj=payload)],
        commit_message=f"Add odds snapshot {stamp}",
    )
    return f"pushed {len(rows)} rows to {DATASET_REPO}/runs/{stamp}.jsonl"


def main() -> None:
    fixtures = FIXTURES or ["Arsenal vs Newcastle"]  # sensible default for a dry run

    model = InferenceClientModel()  # uses HF_TOKEN; default provider model
    agent = CodeAgent(tools=[fetch_odds, fair_probabilities, append_to_tracker], model=model)

    task = (
        "For each of these fixtures: " + ", ".join(fixtures) + ". "
        "Use fetch_odds to get odds, then fair_probabilities to convert them, "
        "collect all resulting dicts into a list, and call append_to_tracker "
        "once with that list as a JSON string. Finish with a one-line summary."
    )
    result = agent.run(task)
    print(result)


if __name__ == "__main__":
    main()

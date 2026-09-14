# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "requests",
# ]
# ///
"""
Semantic Textual Similarity: score how similar a source sentence is to a
list of candidate sentences, via Hugging Face's Inference API.

Two sentence-similarity models are commonly used for this:
- sentence-transformers/msmarco-distilbert-base-tas-b
- sentence-transformers/all-MiniLM-L6-v2

Usage:
    export HF_TOKEN=hf_xxx   # from https://huggingface.co/settings/tokens
    python agent/semantic_similarity.py "That is a happy person" \
        "That is a happy dog" "That is a very happy person" "Today is a sunny day"

    # pick a different model
    python agent/semantic_similarity.py --model sentence-transformers/all-MiniLM-L6-v2 \
        "I'm very happy" "I'm filled with happiness" "I'm happy"

For fully local inference (no API call, needs `pip install sentence-transformers`),
see local_similarity() below.
"""

import argparse
import os

import requests

DEFAULT_MODEL = "sentence-transformers/msmarco-distilbert-base-tas-b"


def query(model: str, source_sentence: str, sentences: list[str]) -> list[float]:
    """Score source_sentence against each of sentences via the HF Inference API.

    Args:
        model: A sentence-similarity model id, e.g.
            "sentence-transformers/all-MiniLM-L6-v2".
        source_sentence: The sentence to compare against.
        sentences: Candidate sentences to score.

    Returns:
        A list of similarity scores (0-1), one per candidate sentence.
    """
    api_url = f"https://router.huggingface.co/hf-inference/models/{model}"
    headers = {"Authorization": f"Bearer {os.environ['HF_TOKEN']}"}
    payload = {"inputs": {"source_sentence": source_sentence, "sentences": sentences}}
    response = requests.post(api_url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def local_similarity(source_sentence: str, sentences: list[str]) -> list[float]:
    """Same task, run locally with sentence-transformers (no API call).

    Requires: pip install sentence-transformers
    """
    from sentence_transformers import SentenceTransformer, util

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    source_embedding = model.encode(source_sentence, convert_to_tensor=True)
    embeddings = model.encode(sentences, convert_to_tensor=True)
    return util.pytorch_cos_sim(source_embedding, embeddings)[0].tolist()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source_sentence", help="Sentence to compare against")
    parser.add_argument("sentences", nargs="+", help="Candidate sentences to score")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Sentence-similarity model id (default: {DEFAULT_MODEL})")
    parser.add_argument("--local", action="store_true", help="Run locally with sentence-transformers instead of the HF Inference API")
    args = parser.parse_args()

    if args.local:
        scores = local_similarity(args.source_sentence, args.sentences)
    else:
        scores = query(args.model, args.source_sentence, args.sentences)

    for sentence, score in zip(args.sentences, scores):
        print(f"{score:.3f}  {sentence}")


if __name__ == "__main__":
    main()

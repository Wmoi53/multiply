# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "transformers>=4.40",
#   "torch",
#   "accelerate",
#   "huggingface_hub>=0.27",
# ]
# ///
"""
Transcribe an audio file with openai/whisper-large-v3.

Two modes:
- Local inference (default): downloads and runs the ~1.5B-param model on this
  machine. Needs ~6GB disk and is far faster on a GPU; CPU works but is slow.
- Hosted inference (--hosted): calls the model via Hugging Face's Inference
  API instead of downloading it — lighter locally, needs HF_TOKEN and network.

Usage:
    pip install transformers torch accelerate huggingface_hub
    python agent/whisper_transcribe.py path/to/audio.mp3

    # or, without a local model download:
    HF_TOKEN=hf_xxx python agent/whisper_transcribe.py path/to/audio.mp3 --hosted
"""

import argparse
import os


def transcribe_local(audio_path: str) -> str:
    import torch
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    model_id = "openai/whisper-large-v3"
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
    )
    model.to(device)
    processor = AutoProcessor.from_pretrained(model_id)

    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        torch_dtype=torch_dtype,
        device=device,
    )
    return pipe(audio_path)["text"].strip()


def transcribe_hosted(audio_path: str) -> str:
    from huggingface_hub import InferenceClient

    client = InferenceClient(token=os.environ["HF_TOKEN"])
    result = client.automatic_speech_recognition(audio_path, model="openai/whisper-large-v3")
    return result.text.strip()


def transcribe(audio_path: str, hosted: bool = False) -> str:
    return transcribe_hosted(audio_path) if hosted else transcribe_local(audio_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio_path", help="Path to an audio file (mp3, wav, m4a, ...)")
    parser.add_argument(
        "--hosted", action="store_true", help="Use HF Inference API instead of a local model"
    )
    args = parser.parse_args()
    print(transcribe(args.audio_path, hosted=args.hosted))


if __name__ == "__main__":
    main()

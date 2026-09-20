import os

import requests
from dotenv import load_dotenv

load_dotenv()

HF_RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
HF_INFERENCE_URL = f"https://router.huggingface.co/hf-inference/models/{HF_RERANK_MODEL}"


def rerank_chunks(question: str, chunks: list[dict], top_n: int) -> list[dict]:
    """Re-score a shortlist of already-retrieved chunks against the question
    with a Hugging Face-hosted cross-encoder reranker. Unlike RRF (which only
    combines two independently-computed rankings) or the embedding search
    (which compares two independently-computed vectors), the reranker reads
    the question and each chunk's text together in a single pass, so it can
    catch relevant chunks that ranked just outside the cutoff on either
    signal alone.

    Returns the top_n chunks, each carrying a rerank_score, sorted best-first.
    """
    if not chunks:
        return []

    response = requests.post(
        HF_INFERENCE_URL,
        headers={"Authorization": f"Bearer {os.environ['HF_API_TOKEN']}"},
        json={"inputs": [{"text": question, "text_pair": c["chunk_text"]} for c in chunks]},
        timeout=30,
    )
    response.raise_for_status()
    scores = [r["score"] for r in response.json()[0]]

    scored = sorted(zip(chunks, scores), key=lambda pair: pair[1], reverse=True)
    return [{**c, "rerank_score": score} for c, score in scored[:top_n]]

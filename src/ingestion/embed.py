import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Attach an "embedding" field to each chunk dict via batched OpenAI calls."""
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        response = client.embeddings.create(
            model=EMBEDDING_MODEL, input=[c["chunk_text"] for c in batch]
        )
        for chunk, item in zip(batch, response.data):
            chunk["embedding"] = item.embedding
    return chunks

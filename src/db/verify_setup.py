import os

from dotenv import load_dotenv
from openai import OpenAI

from src.db.connection import get_snowflake_connection
from src.db.pinecone_client import get_pinecone_index

load_dotenv()


def main():
    conn = get_snowflake_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1")
    print("Snowflake OK:", cur.fetchone())
    conn.close()

    index = get_pinecone_index()
    stats = index.describe_index_stats()
    print("Pinecone OK, vector count:", stats.total_vector_count)

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    embedding = client.embeddings.create(model="text-embedding-3-small", input="test")
    print("OpenAI embeddings OK, dims:", len(embedding.data[0].embedding))


if __name__ == "__main__":
    main()

import argparse

from src.db.stage import get_from_stage
from src.ingestion.chunk import chunk_sections
from src.ingestion.clean import clean_sections
from src.ingestion.embed import embed_chunks
from src.ingestion.extract import extract_sections
from src.ingestion.load import load_chunks, load_document


def ingest(*, company: str, year: int, document_type: str, stage_path: str, source_filename: str):
    document_id = f"{company.lower()}_{year}_{document_type.lower()}"

    local_path = get_from_stage(stage_path, f"data/raw/{company.lower()}/{year}")
    sections = extract_sections(local_path)
    sections = clean_sections(sections)
    chunks = chunk_sections(
        sections, company=company, year=year, document_type=document_type, document_id=document_id
    )
    chunks = embed_chunks(chunks)

    load_document(
        document_id=document_id,
        company=company,
        year=year,
        document_type=document_type,
        source_filename=source_filename,
    )
    load_chunks(chunks)

    print(f"Ingested {len(chunks)} chunks for {company} {year} {document_type}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest a filing from the raw stage into Snowflake + Pinecone")
    parser.add_argument("--company", required=True)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--document-type", required=True)
    parser.add_argument("--stage-path", required=True, help="Path under the RAW_FILINGS stage, e.g. apple/2025/aapl-20250927.htm")
    parser.add_argument("--source-filename", required=True)
    args = parser.parse_args()

    ingest(
        company=args.company,
        year=args.year,
        document_type=args.document_type,
        stage_path=args.stage_path,
        source_filename=args.source_filename,
    )

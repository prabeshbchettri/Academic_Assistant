from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ai.llm.factory import build_provider
from ai.retriever import RagRetriever
from database.db import get_session, init_db
from database.models import ReferenceDocumentTable
from integrations.file_parser import parse_file


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Index academic reference documents into ChromaDB RAG."
    )
    parser.add_argument("--course", required=True, help="Course identifier (e.g. physics_201)")
    parser.add_argument("--file", required=True, help="Path to PDF, DOCX, or TXT file to index")
    parser.add_argument("--mock", action="store_true", help="Use deterministic mock embeddings")
    args = parser.parse_args()

    file_path = Path(args.file).resolve()
    if not file_path.exists():
        print(f"Error: File not found at {file_path}", file=sys.stderr)
        return 1

    print(f"Parsing document: {file_path.name}...")
    parsed = parse_file(file_path)
    print(f"Extracted {len(parsed.text)} characters.")

    print(f"Indexing into course collection '{args.course}'...")
    retriever = RagRetriever(llm=build_provider(use_mock=args.mock))
    chunk_count = retriever.index_document(args.course, file_path.name, parsed.text)

    # Persist in DB
    init_db()
    with get_session() as session:
        ref_doc = ReferenceDocumentTable(
            course_id=args.course,
            filename=file_path.name,
            path=str(file_path),
            chunk_count=chunk_count,
        )
        session.add(ref_doc)
        session.commit()

    print(f"Successfully indexed {chunk_count} chunks into ChromaDB!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

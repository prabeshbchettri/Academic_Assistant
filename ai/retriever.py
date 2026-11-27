from __future__ import annotations

import logging
from pathlib import Path

from ai.llm.base import LLMProvider
from app.settings import settings

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


class RagRetriever:
    def __init__(self, persist_dir: Path | None = None, llm: LLMProvider | None = None):
        self.persist_dir = persist_dir or (settings.storage_dir / "rag")
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.llm = llm
        self._client = None

    def _get_client(self):
        if self._client is None:
            import chromadb
            self._client = chromadb.PersistentClient(path=str(self.persist_dir))
        return self._client

    def index_document(self, course_id: str, doc_name: str, text: str) -> int:
        try:
            client = self._get_client()
            collection = client.get_or_create_collection(name=course_id.lower().replace(" ", "_"))
            chunks = chunk_text(text)
            if not chunks:
                return 0

            ids = [f"{doc_name}_{i}" for i in range(len(chunks))]
            metadatas = [{"source": doc_name, "chunk_index": i} for i in range(len(chunks))]

            if self.llm:
                embeddings = self.llm.embed(chunks)
                collection.add(ids=ids, documents=chunks, embeddings=embeddings, metadatas=metadatas)
            else:
                collection.add(ids=ids, documents=chunks, metadatas=metadatas)

            logger.info("Indexed %d chunks for doc '%s' in course '%s'", len(chunks), doc_name, course_id)
            return len(chunks)
        except Exception as exc:
            logger.warning("Could not index document in ChromaDB: %s", exc)
            return 0

    def retrieve(self, course_id: str, query: str, top_k: int = 3) -> list[str]:
        try:
            client = self._get_client()
            collection_name = course_id.lower().replace(" ", "_")
            # Check if collection exists
            existing = [c.name for c in client.list_collections()]
            if collection_name not in existing:
                return []

            collection = client.get_collection(name=collection_name)
            if collection.count() == 0:
                return []

            if self.llm:
                query_vec = self.llm.embed([query], input_type="query")[0]
                results = collection.query(query_embeddings=[query_vec], n_results=min(top_k, collection.count()))
            else:
                results = collection.query(query_texts=[query], n_results=min(top_k, collection.count()))

            documents = results.get("documents", [[]])
            return documents[0] if documents else []
        except Exception as exc:
            logger.warning("RAG retrieval failed: %s", exc)
            return []

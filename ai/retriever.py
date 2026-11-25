from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ai.llm.base import LLMProvider
from app.settings import settings

logger = logging.getLogger(__name__)


class RetrievedChunk(BaseModel):
    text: str
    source: str
    chunk_index: int = 0
    score: float = 0.0


def sanitize_collection_name(course_id: str) -> str:
    """Normalizes any course name or ID into a valid ChromaDB collection name (3-63 chars)."""
    raw = (course_id or "general").strip().lower()
    cleaned = re.sub(r"[^a-z0-9_-]+", "_", raw)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_-")
    if len(cleaned) < 3:
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]
        cleaned = f"course_{cleaned}_{digest}".strip("_")
    if len(cleaned) > 63:
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:6]
        cleaned = f"{cleaned[:56].rstrip('_-')}_{digest}"
    return cleaned


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    if not text:
        return []
    step = max(1, chunk_size - overlap)
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        if end < len(text):
            # Prefer breaking on paragraph or sentence boundary near the end of the window
            min_break = start + max(1, chunk_size // 2)
            break_pos = max(
                text.rfind("\n\n", min_break, end),
                text.rfind(". ", min_break, end),
                text.rfind("\n", min_break, end),
            )
            if break_pos > min_break:
                end = break_pos + 1
        chunk = text[start:end]
        chunks.append(chunk)
        if end >= len(text):
            break
        start = max(start + step, end - overlap)
    return chunks


class RagRetriever:
    def __init__(self, persist_dir: Path | None = None, llm: LLMProvider | None = None):
        self.persist_dir = persist_dir or (settings.storage_dir / "rag")
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.llm = llm
        self._client: Any = None

    def _get_client(self):
        if self._client is None:
            import chromadb

            self._client = chromadb.PersistentClient(path=str(self.persist_dir))
        return self._client

    def index_document(self, course_id: str, doc_name: str, text: str) -> int:
        try:
            client = self._get_client()
            collection_name = sanitize_collection_name(course_id)
            collection = client.get_or_create_collection(name=collection_name)
            chunks = chunk_text(text)
            if not chunks:
                return 0

            safe_doc = re.sub(r"[^a-zA-Z0-9_.-]+", "_", doc_name)
            ids = [f"{safe_doc}_{i}" for i in range(len(chunks))]
            metadatas = [{"source": doc_name, "chunk_index": i} for i in range(len(chunks))]

            if self.llm:
                embeddings = self.llm.embed(chunks)
                collection.upsert(
                    ids=ids,
                    documents=chunks,
                    embeddings=embeddings,
                    metadatas=metadatas,
                )
            else:
                collection.upsert(ids=ids, documents=chunks, metadatas=metadatas)

            logger.info(
                "Indexed %d chunks for doc '%s' in collection '%s'",
                len(chunks),
                doc_name,
                collection_name,
            )
            return len(chunks)
        except Exception as exc:
            logger.warning("Could not index document in ChromaDB: %s", exc)
            return 0

    def retrieve_with_sources(
        self, course_id: str, query: str, top_k: int = 3
    ) -> list[RetrievedChunk]:
        try:
            client = self._get_client()
            collection_name = sanitize_collection_name(course_id)
            existing = [c.name for c in client.list_collections()]
            if collection_name not in existing:
                return []

            collection = client.get_collection(name=collection_name)
            count = collection.count()
            if count == 0:
                return []

            if self.llm:
                query_vec = self.llm.embed([query])[0]
                results = collection.query(
                    query_embeddings=[query_vec],
                    n_results=min(top_k, count),
                    include=["documents", "metadatas", "distances"],
                )
            else:
                results = collection.query(
                    query_texts=[query],
                    n_results=min(top_k, count),
                    include=["documents", "metadatas", "distances"],
                )

            docs = (results.get("documents") or [[]])[0]
            metas = (results.get("metadatas") or [[]])[0]
            dists = (results.get("distances") or [[]])[0]

            retrieved: list[RetrievedChunk] = []
            for idx, doc_text in enumerate(docs):
                meta = metas[idx] if idx < len(metas) and isinstance(metas[idx], dict) else {}
                dist = float(dists[idx]) if idx < len(dists) else 0.0
                score = round(1.0 / (1.0 + max(0.0, dist)), 4)
                retrieved.append(
                    RetrievedChunk(
                        text=str(doc_text),
                        source=str(meta.get("source", "Course Material")),
                        chunk_index=int(meta.get("chunk_index", idx)),
                        score=score,
                    )
                )
            return retrieved
        except Exception as exc:
            logger.warning("RAG retrieval failed: %s", exc)
            return []

    def retrieve(self, course_id: str, query: str, top_k: int = 3) -> list[str]:
        return [chunk.text for chunk in self.retrieve_with_sources(course_id, query, top_k=top_k)]

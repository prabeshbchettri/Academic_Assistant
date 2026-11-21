import tempfile
from pathlib import Path
from ai.llm.mock import MockProvider
from ai.retriever import RagRetriever, chunk_text


def test_chunking():
    text = "A" * 2500
    chunks = chunk_text(text, chunk_size=1000, overlap=150)
    assert len(chunks) >= 3
    assert all(len(c) <= 1000 for c in chunks)


def test_rag_index_and_retrieve():
    with tempfile.TemporaryDirectory() as tmpdir:
        retriever = RagRetriever(persist_dir=Path(tmpdir), llm=MockProvider())
        course = "physics_test"
        doc_name = "lab_manual.txt"
        content = (
            "The Wheatstone bridge is an electrical circuit used to measure an unknown electrical resistance "
            "by balancing two legs of a bridge circuit. Ohm's law states that current is directly proportional to voltage."
        )

        chunk_count = retriever.index_document(course, doc_name, content)
        assert chunk_count > 0

        # Retrieve
        results = retriever.retrieve(course, "Wheatstone bridge", top_k=2)
        assert len(results) > 0
        assert any("Wheatstone" in doc for doc in results)

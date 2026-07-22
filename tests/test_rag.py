"""Offline retrieval tests use a deterministic local embedding, not a network model."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ir_copilot.rag.embeddings import HashEmbeddingFunction
from ir_copilot.rag.indexer import RunbookIndexer
from ir_copilot.rag.retriever import RunbookRetriever


class RunbookRetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        cls._temporary_dir = tempfile.TemporaryDirectory()
        cls.persist_dir = Path(cls._temporary_dir.name) / "chroma"
        cls.embedding = HashEmbeddingFunction()
        count = RunbookIndexer(
            runbook_dir=repo_root / "data/runbooks",
            persist_dir=cls.persist_dir,
            embedding_function=cls.embedding,
        ).rebuild()
        if count <= 0:
            raise RuntimeError("expected at least one indexed runbook chunk")
        cls.retriever = RunbookRetriever(
            persist_dir=cls.persist_dir, embedding_function=cls.embedding
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temporary_dir.cleanup()

    def test_connection_pool_query_returns_database_runbook(self) -> None:
        results = self.retriever.retrieve("database connection pool exhausted", top_k=3)
        self.assertIn("db-pool.md", [result.source for result in results])

    def test_dependency_outage_query_returns_dependency_runbook(self) -> None:
        results = self.retriever.retrieve("upstream dependency outage and downstream 503", top_k=3)
        self.assertIn("dependency-outage.md", [result.source for result in results])

    def test_chunk_metadata_preserves_headers(self) -> None:
        result = self.retriever.retrieve("memory leak after deploy", top_k=1)[0]
        self.assertTrue(result.headers)

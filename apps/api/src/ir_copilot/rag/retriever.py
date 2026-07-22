"""Retrieve a small, grounded set of runbook chunks from local Chroma."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb

from .indexer import COLLECTION_NAME


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    content: str
    source: str
    title: str
    headers: str
    distance: float


class RunbookRetriever:
    """Cosine retrieval with a small title/header keyword boost."""

    def __init__(
        self,
        *,
        persist_dir: Path,
        embedding_function: Any,
    ) -> None:
        client = chromadb.PersistentClient(path=str(persist_dir))
        self.collection = client.get_collection(
            COLLECTION_NAME, embedding_function=embedding_function
        )

    def retrieve(self, query: str, *, top_k: int = 3) -> list[RetrievedChunk]:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        count = self.collection.count()
        if not count:
            return []
        result = self.collection.query(
            query_texts=[query],
            n_results=min(count, max(top_k, top_k * 3)),
            include=["documents", "metadatas", "distances"],
        )
        query_words = set(re.findall(r"[a-z0-9_]+", query.lower()))
        chunks = [
            RetrievedChunk(
                chunk_id=chunk_id,
                content=document,
                source=metadata["source"],
                title=metadata["title"],
                headers=metadata["headers"],
                distance=float(distance),
            )
            for chunk_id, document, metadata, distance in zip(
                result["ids"][0],
                result["documents"][0],
                result["metadatas"][0],
                result["distances"][0],
                strict=True,
            )
        ]
        return sorted(
            chunks,
            key=lambda chunk: (
                -len(query_words & set(re.findall(r"[a-z0-9_]+", f"{chunk.title} {chunk.headers}".lower()))),
                chunk.distance,
            ),
        )[:top_k]

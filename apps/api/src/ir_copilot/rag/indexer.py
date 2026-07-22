"""Build a persistent Chroma index from local markdown runbooks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb
from chromadb.errors import NotFoundError

from .chunker import MarkdownChunker
from .embeddings import MiniLMEmbeddingFunction

COLLECTION_NAME = "ir_copilot_runbooks"


class RunbookIndexer:
    """Rebuild the small, local Chroma collection in one explicit operation."""

    def __init__(
        self,
        *,
        runbook_dir: Path | None = None,
        persist_dir: Path | None = None,
        embedding_function: Any | None = None,
        chunker: MarkdownChunker | None = None,
    ) -> None:
        repo_root = Path(__file__).resolve().parents[5]
        self.runbook_dir = runbook_dir or repo_root / "data/runbooks"
        self.persist_dir = persist_dir or repo_root / "data/chroma"
        self.embedding_function = embedding_function or MiniLMEmbeddingFunction()
        self.chunker = chunker or MarkdownChunker()

    def rebuild(self) -> int:
        client = chromadb.PersistentClient(path=str(self.persist_dir))
        try:
            client.delete_collection(COLLECTION_NAME)
        except NotFoundError:
            pass
        collection = client.create_collection(
            COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
            embedding_function=self.embedding_function,
        )
        chunks = [
            chunk
            for path in sorted(self.runbook_dir.glob("*.md"))
            for chunk in self.chunker.chunk_file(path)
        ]
        if not chunks:
            raise ValueError(f"no markdown runbooks found in {self.runbook_dir}")
        collection.add(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.content for chunk in chunks],
            metadatas=[
                {
                    "source": chunk.source,
                    "title": chunk.title,
                    "headers": chunk.headers,
                    "chunk_index": chunk.chunk_index,
                }
                for chunk in chunks
            ],
        )
        return len(chunks)


def main() -> None:
    count = RunbookIndexer().rebuild()
    print(f"Indexed {count} runbook chunks into data/chroma using all-MiniLM-L6-v2.")


if __name__ == "__main__":
    main()

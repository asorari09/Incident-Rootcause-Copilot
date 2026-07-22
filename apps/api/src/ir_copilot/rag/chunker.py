"""Header-aware markdown chunking for the small local runbook corpus."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunbookChunk:
    chunk_id: str
    source: str
    title: str
    headers: str
    chunk_index: int
    content: str


class MarkdownChunker:
    """Split markdown into approximately 500-token chunks with token overlap."""

    def __init__(self, *, chunk_size: int = 500, overlap: int = 60) -> None:
        if not 400 <= chunk_size <= 600:
            raise ValueError("chunk_size must be between 400 and 600 tokens")
        if not 0 <= overlap < chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_file(self, path: Path) -> list[RunbookChunk]:
        return self.chunk_text(path.name, path.read_text(encoding="utf-8"))

    def chunk_text(self, source: str, markdown: str) -> list[RunbookChunk]:
        headers = self._headers(markdown)
        title = headers[0] if headers else Path(source).stem.replace("-", " ")
        words = markdown.split()
        if not words:
            return []

        chunks: list[RunbookChunk] = []
        start = 0
        index = 0
        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunks.append(
                RunbookChunk(
                    chunk_id=f"runbook:{source}#{index}",
                    source=source,
                    title=title,
                    headers=" | ".join(headers),
                    chunk_index=index,
                    content=" ".join(words[start:end]),
                )
            )
            if end == len(words):
                break
            start = end - self.overlap
            index += 1
        return chunks

    @staticmethod
    def _headers(markdown: str) -> list[str]:
        return [
            line.lstrip("#").strip()
            for line in markdown.splitlines()
            if line.startswith("#") and line.lstrip("#").strip()
        ]

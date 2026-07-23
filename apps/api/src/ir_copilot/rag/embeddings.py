"""Local embedding functions. No hosted embedding provider is used."""

from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Sequence
from typing import Any


class MiniLMEmbeddingFunction:
    """Lazy CPU-only all-MiniLM-L6-v2 embedding function for Chroma."""

    model_name = "all-MiniLM-L6-v2"

    def __init__(self) -> None:
        self._model = None

    def __call__(self, input: Sequence[str]) -> list[list[float]]:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            allow_download = os.getenv("IR_COPILOT_ALLOW_MODEL_DOWNLOAD", "false").lower() == "true"
            self._model = SentenceTransformer(
                self.model_name, device="cpu", local_files_only=not allow_download
            )
        return self._model.encode(list(input), normalize_embeddings=True).tolist()

    def embed_documents(self, input: Sequence[str]) -> list[list[float]]:
        return self(input)

    def embed_query(self, input: Sequence[str]) -> list[list[float]]:
        return self(input)

    @staticmethod
    def name() -> str:
        return "sentence-transformers/all-MiniLM-L6-v2"

    def is_legacy(self) -> bool:
        return False

    def supported_spaces(self) -> list[str]:
        return ["cosine"]

    def get_config(self) -> dict[str, Any]:
        return {"model_name": self.model_name}

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> "MiniLMEmbeddingFunction":
        del config
        return MiniLMEmbeddingFunction()


class HashEmbeddingFunction:
    """Deterministic local test embedding; avoids model downloads in unit tests."""

    def __init__(self, dimensions: int = 256) -> None:
        self.dimensions = dimensions

    def __call__(self, input: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in input:
            vector = [0.0] * self.dimensions
            for token in re.findall(r"[a-z0-9_]+", text.lower()):
                bucket = int(hashlib.sha256(token.encode()).hexdigest(), 16) % self.dimensions
                vector[bucket] += 1.0
            norm = sum(value * value for value in vector) ** 0.5
            vectors.append([value / norm for value in vector] if norm else vector)
        return vectors

    def embed_documents(self, input: Sequence[str]) -> list[list[float]]:
        return self(input)

    def embed_query(self, input: Sequence[str]) -> list[list[float]]:
        return self(input)

    @staticmethod
    def name() -> str:
        return "ir-copilot-hash"

    def is_legacy(self) -> bool:
        return False

    def supported_spaces(self) -> list[str]:
        return ["cosine"]

    def get_config(self) -> dict[str, Any]:
        return {"dimensions": self.dimensions}

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> "HashEmbeddingFunction":
        return HashEmbeddingFunction(dimensions=int(config["dimensions"]))

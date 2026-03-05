"""
Multi-backend Embedding Provider
Supports OpenAI-compatible APIs (OpenAI / Qwen / DeepSeek / Ollama)
and local sentence-transformers models.

Configure via environment variables:
    EMBEDDING_PROVIDER=openai          # openai | sentence-transformers
    EMBEDDING_MODEL=text-embedding-3-small
    EMBEDDING_API_BASE=https://api.openai.com/v1
    EMBEDDING_API_KEY=sk-xxx
    EMBEDDING_DIMENSION=1536
"""
import os
from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        ...

    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        ...


class OpenAICompatibleProvider(EmbeddingProvider):
    """
    OpenAI-compatible API provider.
    Works with OpenAI, Qwen (via aiping.cn), DeepSeek, Ollama, vLLM, etc.
    """

    def __init__(self, model: str = "", api_base: str = "", api_key: str = "",
                 dimension: int = 0):
        self.model = model or os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
        self.api_base = api_base or os.environ.get("EMBEDDING_API_BASE", "https://api.openai.com/v1")
        self.api_key = api_key or os.environ.get("EMBEDDING_API_KEY", "")
        self._dimension = dimension or int(os.environ.get("EMBEDDING_DIMENSION", "0"))
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(base_url=self.api_base, api_key=self.api_key)
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:
        client = self._get_client()
        resp = client.embeddings.create(model=self.model, input=texts)
        sorted_data = sorted(resp.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]

    def dimension(self) -> int:
        if self._dimension == 0:
            # Auto-detect dimension with a test embedding
            test = self.embed(["test"])
            self._dimension = len(test[0])
        return self._dimension


class SentenceTransformerProvider(EmbeddingProvider):
    """
    Local sentence-transformers models.
    No API key needed — runs entirely offline.
    """

    def __init__(self, model: str = ""):
        self.model_name = model or os.environ.get(
            "EMBEDDING_MODEL", "all-MiniLM-L6-v2"
        )
        self._model = None
        self._dimension = 0

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._load_model()
        embeddings = model.encode(texts, show_progress_bar=False)
        return [e.tolist() for e in embeddings]

    def dimension(self) -> int:
        if self._dimension == 0:
            self._load_model()
        return self._dimension


class EmbeddingFactory:
    """Factory for creating embedding providers from config or env vars."""

    @staticmethod
    def create(provider: str = "", **kwargs) -> EmbeddingProvider:
        """
        Create an embedding provider.

        Args:
            provider: "openai" or "sentence-transformers".
                      If empty, reads from EMBEDDING_PROVIDER env var.
            **kwargs: Passed to the provider constructor
                      (model, api_base, api_key, dimension).

        Returns:
            EmbeddingProvider instance
        """
        provider = provider or os.environ.get("EMBEDDING_PROVIDER", "openai")

        if provider in ("openai", "api"):
            return OpenAICompatibleProvider(**kwargs)
        elif provider in ("sentence-transformers", "local", "st"):
            return SentenceTransformerProvider(**kwargs)
        else:
            raise ValueError(
                f"Unknown provider: {provider}. "
                f"Supported: openai, sentence-transformers"
            )


# Convenience: module-level singleton
_default_provider: EmbeddingProvider | None = None


def get_provider(**kwargs) -> EmbeddingProvider:
    """Get or create the default embedding provider."""
    global _default_provider
    if _default_provider is None:
        _default_provider = EmbeddingFactory.create(**kwargs)
    return _default_provider


def set_provider(provider: EmbeddingProvider):
    """Set a custom embedding provider as the default."""
    global _default_provider
    _default_provider = provider

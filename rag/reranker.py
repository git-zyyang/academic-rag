"""
Result Reranker — Cross-encoder reranking for search results.
"""
from typing import Optional


class Reranker:
    """Cross-encoder reranker using sentence-transformers."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-large"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name)
            except ImportError:
                return False
        return True

    def rerank(self, query: str, results: list, top_k: Optional[int] = None) -> list:
        """
        Rerank retrieval results using cross-encoder.

        Args:
            query: Original query
            results: List of RetrievalResult
            top_k: Return top k results

        Returns:
            Reranked results
        """
        if not results:
            return results

        if not self._load_model():
            return results

        pairs = [(query, r.content[:500]) for r in results]
        scores = self._model.predict(pairs)

        for result, score in zip(results, scores):
            result.score = float(score)

        results.sort(key=lambda x: x.score, reverse=True)

        if top_k:
            results = results[:top_k]

        return results


class SimpleReranker:
    """Lightweight reranker (no external model dependency)."""

    @staticmethod
    def rerank(query: str, results: list, top_k: Optional[int] = None) -> list:
        """Keyword-based reranking with recency bonus."""
        keywords = set(query.replace('\uff0c', ' ').replace(',', ' ').split())

        for result in results:
            content = result.content + " " + result.title
            match_count = sum(1 for kw in keywords if kw in content)
            year_bonus = 0
            if result.year and result.year >= 2020:
                year_bonus = (result.year - 2019) * 0.1
            result.score = match_count / max(len(keywords), 1) + year_bonus

        results.sort(key=lambda x: x.score, reverse=True)

        if top_k:
            results = results[:top_k]

        return results

from __future__ import annotations

from typing import List, Optional

from rank_bm25 import BM25Okapi

from .state import Snippet


class GuideRetriever:
    def __init__(self, snippets: List[Snippet]):
        self.snippets = snippets
        # champ name will be used to rank the snippets
        tokenized = [s.champ.lower().split() for s in snippets]
        self._bm25 = BM25Okapi(tokenized)

    def search(self, query: str, k: int = 5, bias_terms: Optional[List[str]] = None) -> List[Snippet]:
        """
        Search for snippets (guides) matching the query.
        """
        tokens = query.lower().split()
        if bias_terms:
            tokens += [t.lower() for t in bias_terms]
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(zip(scores, self.snippets), key=lambda x: x[0], reverse=True)
        return [s for _, s in ranked[:k]]



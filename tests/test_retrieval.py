from app.retrieval import GuideRetriever
from app.state import Snippet


def test_bm25_orders_relevant():
    snippets = [
        Snippet(id="1", champ=None, text="Ahri charm pick potential"),
        Snippet(id="2", champ=None, text="Garen front to back tank"),
        Snippet(id="3", champ=None, text="Soraka healing sustain"),
    ]
    r = GuideRetriever(snippets)
    top = r.search("Ahri charm", k=1)
    assert top and top[0].id == "1"


from app.threat import compute_threat_scores


def test_compute_threat_scores_basic():
    ally = ["Garen"]
    enemy = ["Ziggs", "Sion", "Janna"]
    scores = compute_threat_scores(ally, enemy)
    by_name = {s.unit: s for s in scores}
    assert by_name["Ziggs"].score >= 2.0
    assert by_name["Sion"].score >= 2.0
    assert by_name["Janna"].score >= 2.0


"""
test_app.py – integrationstest av Flask-routesarna, end-to-end men
utan nätverk och utan att starta en riktig server.

Flask har ett inbyggt "test client" (app.test_client()) som låter oss
anropa routes direkt i python, som om vi gjorde HTTP-requests, men
allt händer i samma process – snabbt och inget riktigt nätverk behövs.

Vi monkeypatchar overpass.get_nearby_places (byter ut den mot en
fejk-funktion) eftersom riktiga Overpass-anrop kräver nätverksåtkomst
som inte alltid finns tillgänglig.

Kör testet:
    python3 test_app.py
"""

import os
from unittest.mock import patch

# Använd en egen testdatabas, så vi aldrig skriver i reseapp.db av misstag.
TEST_DB = "test_reseapp.db"
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

import db
db.DB_PATH = db.Path(TEST_DB)  # peka om databasen INNAN vi importerar app

import app as flask_app_module  # noqa: E402  (import efter db.DB_PATH-ändringen, medvetet)

FAKE_PLACES = [
    {"osm_id": "node/1", "name": "Utsikten", "category": "viewpoint",
     "lat": 45.1, "lon": 9.1},
]


def test_nearby_returns_places_with_vote_counts():
    db.init_db()
    client = flask_app_module.app.test_client()

    with patch("app.overpass.get_nearby_places", return_value=FAKE_PLACES):
        response = client.get("/api/nearby?lat=45.1&lon=9.1")

    assert response.status_code == 200
    body = response.get_json()
    assert len(body) == 1
    assert body[0]["name"] == "Utsikten"
    assert body[0]["votes"] == {"up": 0, "down": 0}
    print("test_nearby_returns_places_with_vote_counts: OK")


def test_vote_then_nearby_reflects_count():
    db.init_db()
    client = flask_app_module.app.test_client()

    vote_payload = {
        "osm_id": "node/1", "name": "Utsikten", "category": "viewpoint",
        "lat": 45.1, "lon": 9.1, "person": "Reza", "vote": 1,
    }
    vote_response = client.post("/api/vote", json=vote_payload)
    assert vote_response.status_code == 200
    assert vote_response.get_json() == {"up": 1, "down": 0}

    # Samma person rostar om -> uppdaterar, skapar inte en andra rad.
    vote_payload["vote"] = -1
    vote_response = client.post("/api/vote", json=vote_payload)
    assert vote_response.get_json() == {"up": 0, "down": 1}

    print("test_vote_then_nearby_reflects_count: OK")


def test_vote_missing_fields_returns_400():
    client = flask_app_module.app.test_client()
    response = client.post("/api/vote", json={"osm_id": "node/1"})
    assert response.status_code == 400
    print("test_vote_missing_fields_returns_400: OK")


if __name__ == "__main__":
    test_nearby_returns_places_with_vote_counts()
    test_vote_then_nearby_reflects_count()
    test_vote_missing_fields_returns_400()
    os.remove(TEST_DB)
    print("Alla tester gick igenom ✅")

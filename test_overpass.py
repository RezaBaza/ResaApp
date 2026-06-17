"""
test_overpass.py – verifierar att vi tolkar Overpass-svar korrekt,
UTAN att behöva ett riktigt nätverksanrop.

Tekniken kallas "mocking": vi byter tillfälligt ut requests.post mot
en låtsasfunktion som returnerar exakt den JSON vi vill testa med.
Då kan vi testa _categorize och parsningen i get_nearby_places
deterministiskt, snabbt, och utan att vara beroende av att
overpass-api.de svarar (eller att vi har nätverksåtkomst alls).

Kör testet:
    python3 test_overpass.py
"""

from unittest.mock import patch, MagicMock

import overpass


FAKE_OVERPASS_RESPONSE = {
    "elements": [
        {
            "type": "node",
            "id": 111,
            "lat": 45.101,
            "lon": 9.201,
            "tags": {"name": "Utsiktsplats Bellagio", "tourism": "viewpoint"},
        },
        {
            "type": "way",
            "id": 222,
            "center": {"lat": 45.102, "lon": 9.202},
            "tags": {"name": "Gamla fästningen", "historic": "fort"},
        },
        {
            "type": "node",
            "id": 333,
            "lat": 45.103,
            "lon": 9.203,
            "tags": {
                "name": "Trattoria Bella Vista",
                "amenity": "restaurant",
                "cuisine": "italian",
            },
        },
        # Ska hoppas över: ingen "name"-tagg
        {
            "type": "node",
            "id": 444,
            "lat": 45.104,
            "lon": 9.204,
            "tags": {"amenity": "restaurant"},
        },
        # Strand taggad på det "andra" sättet (leisure=beach_resort,
        # inte natural=beach) – ska ändå hamna i kategorin "beach".
        {
            "type": "node",
            "id": 555,
            "lat": 45.105,
            "lon": 9.205,
            "tags": {"name": "Solstrandens badplats", "leisure": "beach_resort"},
        },
    ]
}


def test_categorize():
    assert overpass._categorize({"tourism": "viewpoint"}) == "viewpoint"
    assert overpass._categorize({"historic": "fort"}) == "historic"
    assert overpass._categorize({"natural": "beach"}) == "beach"
    assert overpass._categorize({"leisure": "beach_resort"}) == "beach"
    assert overpass._categorize({"amenity": "restaurant"}) == "restaurant"
    assert overpass._categorize({"leisure": "marina"}) == "marina"
    assert overpass._categorize({"shop": "ice_cream"}) == "sweets"
    assert overpass._categorize({"shop": "bakery"}) == "sweets"
    assert overpass._categorize({"leisure": "park"}) == "park"
    assert overpass._categorize({"tourism": "garden"}) == "park"
    assert overpass._categorize({"man_made": "lighthouse"}) == "lighthouse"
    assert overpass._categorize({"amenity": "parking"}) == "parking"
    assert overpass._categorize({"shop": "shoes"}) is None
    print("test_categorize: OK")


def test_get_nearby_places_parsing():
    fake_response = MagicMock()
    fake_response.json.return_value = FAKE_OVERPASS_RESPONSE
    fake_response.raise_for_status.return_value = None

    # Byter ut requests.post i overpass-modulen mot vår fejk under testet.
    with patch("overpass.requests.post", return_value=fake_response) as mock_post:
        places = overpass.get_nearby_places(45.1, 9.2, radius_m=1500)

    # Bekräfta att vi faktiskt anropade Overpass med rätt URL.
    mock_post.assert_called_once()
    called_url = mock_post.call_args.args[0]
    assert called_url == overpass.OVERPASS_URL

    # Vi förväntar oss 4 platser (den utan namn ska vara bortfiltrerad).
    assert len(places) == 4
    names = {p["name"] for p in places}
    assert names == {
        "Utsiktsplats Bellagio",
        "Gamla fästningen",
        "Trattoria Bella Vista",
        "Solstrandens badplats",
    }

    viewpoint = next(p for p in places if p["category"] == "viewpoint")
    assert viewpoint["osm_id"] == "node/111"
    assert viewpoint["lat"] == 45.101

    historic = next(p for p in places if p["category"] == "historic")
    assert historic["osm_id"] == "way/222"  # center-koordinat funkade

    beach = next(p for p in places if p["category"] == "beach")
    assert beach["osm_id"] == "node/555"

    restaurant = next(p for p in places if p["category"] == "restaurant")
    assert restaurant["cuisine"] == "italian"

    # Historic-platsen hade ingen "cuisine"-tagg – ska bli None, inte krascha.
    assert historic["cuisine"] is None

    print("test_get_nearby_places_parsing: OK")


if __name__ == "__main__":
    test_categorize()
    test_get_nearby_places_parsing()
    print("Alla tester gick igenom ✅")

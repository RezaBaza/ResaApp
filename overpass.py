"""
overpass.py – hämtar platser nära en given GPS-position från
OpenStreetMap via Overpass API (https://overpass-api.de).

Overpass är gratis och kräver ingen API-nyckel, men man skickar en
fråga i ett eget frågespråk ("Overpass QL") istället för vanliga
URL-parametrar. Tänk på det som SQL, men för kartdata.

Notera: i utvecklingssandboxen var utgående nätverkstrafik begränsad
till en allow-list, så det riktiga anropet mot overpass-api.de gick
inte att testa därifrån. Koden följer Overpass API:s dokumenterade
format rad för rad – på din egen dator (vanlig internetåtkomst) ska
den fungera direkt. test_overpass.py verifierar PARSNINGEN utan att
behöva nätverk.
"""

import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Vilka OpenStreetMap-taggar som motsvarar våra kategorier.
# key/value enligt OSM:s taggningskonventioner, se wiki.openstreetmap.org.
#
# Varje kategori pekar på en LISTA av (key, value)-par istället för bara
# ett enda par. Det gör att en kategori kan matcha flera olika sätt att
# tagga samma sak i OpenStreetMap – t.ex. "beach" matchar både
# natural=beach (en strand som naturobjekt) och leisure=beach_resort
# (ett anlagt badställe), så fler riktiga stränder dyker upp i listan.
#
# Utökad inför road trip-läget (Ligurien -> Nice): hamnar, glass/bageri,
# parker/trädgårdar, fyrar och parkeringsplatser – praktiskt och
# trevligt vid en kustresa.
CATEGORY_TAGS = {
    "viewpoint": [("tourism", "viewpoint")],
    "historic": [("historic", None)],       # None = "historic" finns, oavsett värde
    "beach": [("natural", "beach"), ("leisure", "beach_resort")],
    "restaurant": [("amenity", "restaurant")],
    "marina": [("leisure", "marina")],
    "sweets": [("shop", "ice_cream"), ("shop", "bakery")],
    "park": [("leisure", "park"), ("tourism", "garden")],
    "lighthouse": [("man_made", "lighthouse")],
    "parking": [("amenity", "parking")],
}


def _build_query(lat, lon, radius_m):
    """
    Bygger Overpass QL-frågan som textsträng.

    nwr = "node, way eller relation" (OSM:s tre sätt att representera
    en plats/yta). around:RADIUS,LAT,LON filtrerar till allt inom en
    cirkel. "out center tags;" ber Overpass returnera tags (namn,
    kategori) plus en centrumkoordinat även för ytor (ways/relations),
    inte bara enskilda punkter (nodes).
    """
    clauses = []
    for tag_pairs in CATEGORY_TAGS.values():
        for key, value in tag_pairs:
            if value is None:
                clauses.append(f'nwr["{key}"](around:{radius_m},{lat},{lon});')
            else:
                clauses.append(f'nwr["{key}"="{value}"](around:{radius_m},{lat},{lon});')

    return f"""
[out:json][timeout:25];
(
  {' '.join(clauses)}
);
out center tags;
""".strip()


def _categorize(tags):
    """
    Tittar på en plats taggar och avgör vilken av våra fyra kategorier
    den hör till. En plats kan tekniskt matcha flera (t.ex. en
    restaurang som också är en historisk byggnad) – vi väljer den
    första som matchar, enklast för V1.
    """
    for category, tag_pairs in CATEGORY_TAGS.items():
        for key, value in tag_pairs:
            if key in tags and (value is None or tags[key] == value):
                return category
    return None


def get_nearby_places(lat, lon, radius_m=1500):
    """
    Frågar Overpass om platser inom radius_m meter från (lat, lon)
    och returnerar en lista av enkla dict:ar, redo att skickas som
    JSON till mobilen:

        [{"osm_id": "node/123", "name": "...", "category": "viewpoint",
          "lat": 45.1, "lon": 9.2}, ...]

    Platser utan namn i OpenStreetMap hoppas över – en "Restaurang"
    utan namn är inte särskilt användbar att rösta på.
    """
    query = _build_query(lat, lon, radius_m)
    # Overpass-API:s dokumentation rekommenderar en beskrivande User-Agent
    # (standard-UA:n från requests-biblioteket, "python-requests/x.x", kan
    # i vissa fall bli blockerad av brandväggar/proxyer som filtrerar bort
    # uppenbar script-trafik).
    headers = {"User-Agent": "ReseappFamily/1.0 (privat familjeresa-app)"}
    response = requests.post(
        OVERPASS_URL, data={"data": query}, headers=headers, timeout=30
    )
    response.raise_for_status()  # Kasta ett fel om Overpass svarar med t.ex. 500
    data = response.json()

    places = []
    for element in data.get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name")
        if not name:
            continue

        category = _categorize(tags)
        if category is None:
            continue

        # Nodes har lat/lon direkt. Ways/relations har det i "center"
        # (det vi bad om med "out center" ovan).
        if element["type"] == "node":
            place_lat, place_lon = element["lat"], element["lon"]
        else:
            center = element.get("center", {})
            place_lat, place_lon = center.get("lat"), center.get("lon")
        if place_lat is None:
            continue

        places.append({
            "osm_id": f"{element['type']}/{element['id']}",
            "name": name,
            "category": category,
            "lat": place_lat,
            "lon": place_lon,
            # "cuisine" är en OSM-tagg på restauranger, t.ex. "italian",
            # "seafood", "pizza" – kan saknas (None), då vet vi bara att
            # det är en restaurang men inte vilken typ av mat.
            "cuisine": tags.get("cuisine"),
        })

    return places

"""
app.py – Flask-appens "huvudfil". Här kopplas webbadresser (routes)
till python-funktioner.

V1 lägger till två API-routes (de returnerar JSON, inte HTML – det är
det mobilsidans Javascript pratar med):

  GET  /api/nearby?lat=..&lon=..   -> lista platser nära den positionen
  POST /api/vote                    -> spara en röst
"""

import math

from flask import Flask, jsonify, render_template, request

import db
import overpass
import plans as plans_module

app = Flask(__name__)

# Skapar databastabellen om den inte redan finns. Måste ligga HÄR (inte
# bara inne i "if __name__ == '__main__'" längre ner) – när appen körs på
# Railway/i produktion startar gunicorn appen genom att importera DENNA
# fil som en modul, och kör ALDRIG __main__-blocket. Utan denna rad
# skulle tabellen "votes" aldrig skapas i produktion och första rösten
# skulle krascha med "no such table: votes".
db.init_db()
db.init_packing_table()


def _distance_m(lat1, lon1, lat2, lon2):
    """
    Beräknar ungefärligt avstånd i meter mellan två GPS-koordinater,
    med "Haversine"-formeln (tar hänsyn till att jorden är ett klot,
    inte en platt karta). Används för att sortera platser så de
    NÄRMASTE visas först – särskilt viktigt nu när vi bara visar
    max 20 platser per kategori (se static/app.js).
    """
    earth_radius_m = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return round(2 * earth_radius_m * math.asin(math.sqrt(a)))


@app.route("/")
def index():
    """Startsidan – all logik körs i Javascript i templates/index.html."""
    return render_template("index.html")


@app.route("/api/nearby")
def nearby():
    """
    Tar emot ?lat=...&lon=... (och valfritt &radius=...) som
    query-parametrar i URL:en, t.ex:
        /api/nearby?lat=45.47&lon=9.18&radius=1500

    request.args är en dict-liknande struktur Flask bygger automatiskt
    från query-strängen. .get() med default-värde gör att radius är
    valfritt att skicka med.
    """
    try:
        lat = float(request.args["lat"])
        lon = float(request.args["lon"])
    except (KeyError, ValueError):
        # 400 Bad Request = "det du skickade går inte att använda"
        return jsonify({"error": "lat och lon krävs som tal"}), 400

    radius = int(request.args.get("radius", 1500))

    places = overpass.get_nearby_places(lat, lon, radius_m=radius)

    # Slå ihop platserna med hur många röster de redan har fått, och
    # räkna ut avståndet från användarens position till varje plats.
    osm_ids = [p["osm_id"] for p in places]
    votes = db.get_vote_summary(osm_ids)
    for place in places:
        place["votes"] = votes.get(
            place["osm_id"], {"up": 0, "down": 0, "up_names": [], "down_names": []}
        )
        place["distance_m"] = _distance_m(lat, lon, place["lat"], place["lon"])

    # Sortera så de NÄRMASTE platserna kommer först i listan. Frontend
    # visar bara de 20 första per kategori, så ordningen avgör vilka
    # 20 det blir.
    places.sort(key=lambda p: p["distance_m"])

    return jsonify(places)


@app.route("/api/plans")
def get_plans():
    """
    Returnerar de fyra färdiga reseplans-ALTERNATIVEN (se plans.py) ihop
    med hur många röster varje HEL PLAN redan fått. Vi återanvänder
    samma votes-tabell/logik som platserna – en plan är "bara" en plats
    med ett konstigt osm_id (t.ex. "plan-a") och en dummy-koordinat.
    """
    plan_list, lat, lon = plans_module.get_plans_with_lat_lon()

    plan_ids = [p["id"] for p in plan_list]
    votes = db.get_vote_summary(plan_ids)

    result = []
    for plan in plan_list:
        result.append(
            {
                **plan,
                "lat": lat,
                "lon": lon,
                "votes": votes.get(
                    plan["id"],
                    {"up": 0, "down": 0, "up_names": [], "down_names": []},
                ),
            }
        )

    return jsonify(result)


@app.route("/api/vote", methods=["POST"])
def vote():
    """
    Tar emot en röst som JSON i request-body, t.ex:
        {"osm_id": "node/123", "name": "Utsikt", "category": "viewpoint",
         "lat": 45.1, "lon": 9.2, "person": "Reza", "vote": 1}

    request.get_json() tolkar body som JSON och ger oss en python-dict.
    """
    payload = request.get_json(silent=True) or {}

    required_fields = ["osm_id", "name", "category", "lat", "lon", "person", "vote"]
    missing = [f for f in required_fields if f not in payload]
    if missing:
        return jsonify({"error": f"saknar falt: {', '.join(missing)}"}), 400

    if payload["vote"] not in (1, -1):
        return jsonify({"error": "vote maste vara 1 eller -1"}), 400

    # Toggle-logik: om personen klickar på SAMMA röst igen (t.ex. gillar,
    # ångrar sig, klickar 👍 en gång till) ska rösten tas bort istället
    # för att bara skrivas över med samma värde. Klickar de istället på
    # den ANDRA knappen (bytte från 👍 till 👎) byts rösten ut som
    # vanligt – det är fortfarande EN röst per person och plats.
    existing_vote = db.get_vote_for_person(payload["osm_id"], payload["person"])
    if existing_vote == payload["vote"]:
        db.remove_vote(payload["osm_id"], payload["person"])
    else:
        db.record_vote(
            osm_id=payload["osm_id"],
            name=payload["name"],
            category=payload["category"],
            lat=payload["lat"],
            lon=payload["lon"],
            person=payload["person"],
            vote=payload["vote"],
        )

    # Skicka tillbaka den uppdaterade summan (siffror + namn på vem som
    # röstat vad) så frontend kan visa nya siffror direkt utan att hämta
    # om hela listan.
    summary = db.get_vote_summary([payload["osm_id"]])
    return jsonify(summary[payload["osm_id"]])


@app.route("/api/packing", methods=["GET"])
def get_packing():
    """Hämtar hela den delade packlistan."""
    return jsonify(db.get_packing_items())


@app.route("/api/packing", methods=["POST"])
def add_packing():
    """
    Lägger till en ny rad i packlistan, t.ex:
        {"item": "Solkräm", "person": "Sadna"}
    """
    payload = request.get_json(silent=True) or {}
    item = (payload.get("item") or "").strip()
    person = (payload.get("person") or "").strip()
    if not item or not person:
        return jsonify({"error": "item och person krävs"}), 400

    new_id = db.add_packing_item(item, person)
    return jsonify({"id": new_id, "item": item, "added_by": person, "done": False})


@app.route("/api/packing/<int:item_id>/toggle", methods=["POST"])
def toggle_packing(item_id):
    """Bockar av/på en rad i packlistan."""
    new_done = db.toggle_packing_item(item_id)
    if new_done is None:
        return jsonify({"error": "hittade ingen sådan rad"}), 404
    return jsonify({"id": item_id, "done": new_done})


@app.route("/api/packing/<int:item_id>", methods=["DELETE"])
def delete_packing(item_id):
    """Tar bort en rad ur packlistan."""
    db.delete_packing_item(item_id)
    return jsonify({"ok": True})


if __name__ == "__main__":
    db.init_db()
    # ssl_context="adhoc" startar servern med ett självsignerat HTTPS-
    # certifikat. Webbläsare kräver "secure origin" (https eller
    # localhost) för att tillåta GPS-åtkomst (navigator.geolocation) –
    # vanlig http över wifi räcker inte. Kräver: pip install pyopenssl.
    # Webbläsaren visar en varning om "osäker anslutning" första gången
    # (eftersom certifikatet är självsignerat, inte utfärdat av en
    # erkänd certifikatutfärdare) – klicka "Avancerat" -> "Fortsätt",
    # det är förväntat och okej för test inom familjen.
    #
    # use_reloader=False: debug-läget startar normalt en "reloader" som
    # vakar på filerna och startar om servern automatiskt vid ändringar.
    # I kombination med ett självsignerat HTTPS-certifikat (adhoc) kan
    # detta krocka precis när webbläsaren ansluter (servern startar om
    # mitt i handskakningen) -> sidan hänger sig/"inget händer". Extra
    # känsligt i en OneDrive-synkad mapp, där synkningen också rör vid
    # filerna och kan trigga reloadern i onödan. Stänger vi av den
    # behöver du själv köra om `python app.py` när du ändrar kod, men
    # https blir stabilt.
    #
    # threaded=True: webbläsaren öppnar ofta FLERA samtidiga anslutningar
    # till servern (t.ex. själva sidan + en för favicon.ico samtidigt).
    # Flasks dev-server hanterar annars EN anslutning i taget – om den
    # första TLS-anslutningen inte stängs direkt (vanligt över HTTPS)
    # blockeras den andra och webbläsaren får ERR_TIMED_OUT. threaded=True
    # låter servern hantera flera anslutningar parallellt istället.
    app.run(
        debug=True,
        use_reloader=False,
        threaded=True,
        host="0.0.0.0",
        port=5000,
        ssl_context="adhoc",
    )

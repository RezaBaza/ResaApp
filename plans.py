"""
plans.py – de färdiga reseplans-ALTERNATIVEN familjen kan rösta på.

Det här är INTE platser man hittar automatiskt (det gör overpass.py) –
det är hela resrutter, byggda av etapper (en stad/region + hotellförslag
+ pris + karta), hämtade från researchen i Google Drive-dokumentet
"Reseplan_Italien_Frankrike_2026.md". Samma flyg (Stockholm <-> Bergamo,
16 juli - 5 augusti, 20 nätter) ligger bakom alla fyra alternativen –
skillnaden är HUR de 20 nätterna delas upp: färre/längre etapper (mer
avslappnat, mer strand) eller fler/kortare etapper (mer variation, mer
körning).

Varje plan har ett stabilt "id" (t.ex. "plan-a") som används som
osm_id i röst-databasen – samma vote-tabell och samma /api/vote-route
som platserna återanvänds, vi later bara som om varje HEL PLAN är en
"plats" man kan gilla/ogilla.

V2 lägger till två saker per etapp/plan, så familjen kan jämföra
alternativen utan att själva googla runt:
  - "drive": ungefärlig körsträcka/körtid från FÖREGÅENDE stopp (första
    etappen räknas från Bergamo flygplats, där hyrbilen hämtas).
  - "highlights": några korta förslag på vad man kan göra/besöka där.
Plus en sammanfattande text ("summary") och total körsträcka/körtid
("total_drive") för hela planen.

V3: sista övernattningen är nu i MILANO (inte Bergamo) – mer att göra
sista kvällen innan hemflyget. Sista dagen kör man sedan tillbaka till
Bergamo flygplats för att lämna hyrbilen och flyga hem
("departure_transfer"). Varje plan har också fått en "route_map" – EN
Google Maps-länk som visar hela bilrutten i ordning (Bergamo flygplats
-> etapp A -> etapp B -> ... -> Milano -> Bergamo flygplats), så man
kan se hela slingan på kartan istället för bara enskilda hotellnålar.

OBS: körsträckorna/-tiderna är UPPSKATTADE bilvägs-avstånd (ingen
ruttplanerare/API är inkopplad), avrundade till närmaste 5 km/5 min och
markerade med "ca" – verklig tid beror på trafik, vägval och stopp.
"""

import urllib.parse

# Dummy-koordinat (Bergamo flygplats) – krävs av votes-tabellen men
# används inte till något för planer (ingen karta visas baserat på den).
_BERGAMO_LAT = 45.6739
_BERGAMO_LON = 9.7042

# Bergamo Orio al Serio (BGY) – här hämtas och lämnas hyrbilen, så det är
# start- OCH slutpunkt för varje plans bilrutt (route_map nedan).
_BGY_AIRPORT_ADDRESS = "Aeroporto di Bergamo Orio al Serio (BGY), Italy"


def _maps_link(address):
    """Enkel Google Maps-sökning på EN adress (en hotellnål)."""
    return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(address)}"


def _beach(name, address):
    """
    En badstrand/strandpromenad man kan tipsa om i sammanfattningen, med
    namnet som en klickbar Google Maps-länk (sökt fram via webben, se
    research-anteckning i README/PR – inga koordinater gissade).
    """
    return {"name": name, "maps_query": _maps_link(address)}


def _route_map_link(addresses):
    """
    Bygger EN Google Maps-länk (körvägsbeskrivning) som kedjar ihop flera
    adresser i ordning: start -> mellanstopp -> ... -> slut. Det här är
    "se hela rutten Bergamo till A, A till B, B till C osv" på en gång,
    istället för att behöva öppna varje hotells karta för sig.
    """
    encoded = [urllib.parse.quote(a) for a in addresses]
    origin = encoded[0]
    destination = encoded[-1]
    waypoints = "|".join(encoded[1:-1])
    url = (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={origin}&destination={destination}&travelmode=driving"
    )
    if waypoints:
        url += f"&waypoints={waypoints}"
    return url


def _fmt_drive_time(minutes):
    """T.ex. 160 -> 'ca 2 tim 40 min', 50 -> 'ca 50 min'."""
    hours, mins = divmod(minutes, 60)
    if hours == 0:
        return f"ca {mins} min"
    if mins == 0:
        return f"ca {hours} tim"
    return f"ca {hours} tim {mins} min"


def _drive(from_name, km, minutes):
    """Körsträcka/körtid FRÅN föregående stopp till den här etappen."""
    return {
        "from": from_name,
        "km": km,
        "minutes": minutes,
        "time": _fmt_drive_time(minutes),
    }


def _total_drive(legs, departure_transfer=None):
    """
    Summerar alla "drive"-poster i en plan till en total km/tid, plus
    sista dagens transfer tillbaka till flygplatsen (om angiven) så
    totalen stämmer med ALL körning under resan, inte bara mellan
    övernattningarna.
    """
    total_km = sum(leg["drive"]["km"] for leg in legs if leg.get("drive"))
    total_minutes = sum(
        leg["drive"]["minutes"] for leg in legs if leg.get("drive")
    )
    if departure_transfer:
        total_km += departure_transfer["km"]
        total_minutes += departure_transfer["minutes"]
    return {
        "km": total_km,
        "minutes": total_minutes,
        "time": _fmt_drive_time(total_minutes),
    }


# Parkeringsinfo per hotell (sökt fram via webben – ingen av hotellen har
# gratis parkering i egen lobby/garage, så bra att veta i förväg).
_PARKING_LA_SPEZIA = "🅿️ Inget eget garage – betald utomhusparkering/valet ca 200 m bort, ca 12 €/dygn."
_PARKING_NICE = "🅿️ Inget eget garage – närmaste parkeringshus (Sulzer/Corvesy) ca 5 min promenad, ca 25–32 €/dygn."
_PARKING_COMO = "🅿️ Inget eget garage – t.ex. systerhotellet Palace 200 m bort, ca 18–24 €/dygn."
_PARKING_SAINTE_MAXIME = "🅿️ Egen bevakad parkering på området (bokas i förväg), ca 18–25 €/dygn."
_PARKING_COURMAYEUR = "🅿️ Gratis parkering vid infarten (ca 12 platser) eller bokningsbart garage, ca 20 €/dygn."
_PARKING_MILANO = "🅿️ Inget eget garage – parkeringshus ca 200 m bort, ca 25 €/dygn (ingen förbokning behövs)."


# Fina stränder för sol och bad, en lista per etapp-område. Namnen är
# klickbara Google Maps-länkar i frontend (se "beaches" på varje plan
# nedan) så man snabbt kan slå upp läget på kartan.
_BEACH_MONTEROSSO = _beach("Monterosso al Mare", "Spiaggia di Monterosso al Mare, Italy")
_BEACH_VERNAZZA = _beach("Vernazza", "Spiaggia di Vernazza, Italy")
_BEACH_CASTEL_PLAGE = _beach("Castel Plage, Nice", "Castel Plage, Quai des Etats-Unis, 06300 Nice, France")
_BEACH_PONCHETTES = _beach("Plage des Ponchettes, Nice", "Plage des Ponchettes, 06300 Nice, France")
_BEACH_PAMPELONNE = _beach("Pampelonne, Saint-Tropez", "Plage de Pampelonne, 83350 Ramatuelle, France")
_BEACH_VILLA_OLMO = _beach("Lido Villa Olmo, Como", "Lido di Villa Olmo, Via Cernobbio 2, 22100 Como, Italy")


# Milano-etappen är likadan i alla fyra planer (sista övernattningen,
# 3-5 augusti), så vi bygger den en gång och återanvänder.
_MILANO_ADDRESS = "NH Milano Touring, Via Ugo Tarchetti 2, 20121 Milano, Italy"


def _milano_leg(from_name, km, minutes):
    return {
        "name": "Milano",
        "nights": "2 nätter, 3–5 augusti",
        "hotel": "NH Milano Touring (4★, gångavstånd till centrum, frukost)",
        "price": "ca 1 900–2 500 kr/natt",
        "parking": _PARKING_MILANO,
        "address": _MILANO_ADDRESS,
        "maps_query": _maps_link(_MILANO_ADDRESS),
        "drive": _drive(from_name, km, minutes),
        "highlights": [
            "Duomo di Milano + takterrassen med utsikt",
            "Galleria Vittorio Emanuele II",
            "Glass nära Piazza del Duomo",
        ],
    }


# Sista dagen (5 augusti): kör tillbaka från Milano till Bergamo
# flygplats, lämna hyrbilen och flyg hem. Samma för alla fyra planer.
_DEPARTURE_TRANSFER = _drive("Milano", 50, 45)


PLANS = [
    {
        "id": "plan-a",
        "title": "A. Lugn & solig",
        "subtitle": "3 etapper – max strand & avslappning, inga berg, kort stadsstopp sista kvällen. Perfekt om Viana får bestämma.",
        "summary": (
            "Den mest avslappnade rutten: inga berg – bara vandring längs "
            "kustleden och bad i Cinque Terre, sol och bad längs Franska "
            "Rivieran, och ett kort stopp i Milano sista kvällen innan "
            "hemflyget. Minst körning av alla fyra planer."
        ),
        "beaches": [_BEACH_MONTEROSSO, _BEACH_VERNAZZA, _BEACH_CASTEL_PLAGE, _BEACH_PONCHETTES],
        "legs": [
            {
                "name": "Cinque Terre / Ligurien",
                "nights": "9 nätter, 16–25 juli",
                "hotel": "NH La Spezia (4★, vid hamnen, frukost)",
                "price": "ca 1 700–2 400 kr/natt",
                "parking": _PARKING_LA_SPEZIA,
                "address": "NH La Spezia, Via XX Settembre 2, 19124 La Spezia, Italy",
                "maps_query": _maps_link("NH La Spezia, Via XX Settembre 2, 19124 La Spezia, Italy"),
                "drive": _drive("Bergamo flygplats", 225, 160),
                "highlights": [
                    "Vandra Sentiero Azzurro (kustleden) mellan byarna",
                    "Bada i Monterosso eller Vernazza",
                    "Båt mellan de fem byarna",
                    "Glass i Manarola med utsikt",
                ],
            },
            {
                "name": "Nice & Franska Rivieran",
                "nights": "9 nätter, 25 juli–3 augusti",
                "hotel": "Albert 1er Hotel Nice (4★, 2 min till stranden, triple-rum)",
                "price": "ca 1 800–2 400 kr/natt",
                "parking": _PARKING_NICE,
                "address": "Albert 1er Hotel Nice, 4 Avenue Max Gallo, 06000 Nice, France",
                "maps_query": _maps_link("Albert 1er Hotel Nice, 4 Avenue Max Gallo, 06000 Nice, France"),
                "drive": _drive("Cinque Terre / Ligurien", 230, 165),
                "highlights": [
                    "Bad vid Castel Plage eller Promenade des Anglais",
                    "Promenera Vieux Nice och marknaden Cours Saleya",
                    "Dagsutflykt till Antibes eller Villefranche-sur-Mer",
                    "Glass på gamla stans gränder",
                ],
            },
            _milano_leg("Nice & Franska Rivieran", 340, 225),
        ],
    },
    {
        "id": "plan-b",
        "title": "B. Balanserad klassiker",
        "subtitle": "4 etapper – en skvätt Comosjön, sen gott om strandtid i Ligurien och Nice, kort stadsstopp sista kvällen.",
        "summary": (
            "Samma lugna kustkänsla som "
            "“A” men med en kort, vacker inledning vid Comosjön "
            "innan stranden tar vid. Plus en dagsutflykt till Saint-Tropez "
            "inbakad i Nice-etappen, och ett kort stopp i Milano sista "
            "kvällen innan hemflyget."
        ),
        "beaches": [_BEACH_VILLA_OLMO, _BEACH_MONTEROSSO, _BEACH_CASTEL_PLAGE, _BEACH_PAMPELONNE],
        "legs": [
            {
                "name": "Comosjön",
                "nights": "2 nätter, 16–18 juli",
                "hotel": "Hotel Barchetta Excelsior (4★, vid sjön, frukost)",
                "price": "ca 2 200–2 600 kr/natt",
                "parking": _PARKING_COMO,
                "address": "Hotel Barchetta Excelsior, Piazza Cavour 1, 22100 Como, Italy",
                "maps_query": _maps_link("Hotel Barchetta Excelsior, Piazza Cavour 1, 22100 Como, Italy"),
                "drive": _drive("Bergamo flygplats", 50, 50),
                "highlights": [
                    "Båttur på Comosjön",
                    "Bad vid sjöns stränder",
                    "Dagsutflykt till Bellagio",
                    "Glass längs hamnpromenaden",
                ],
            },
            {
                "name": "Cinque Terre / Ligurien",
                "nights": "7 nätter, 18–25 juli",
                "hotel": "NH La Spezia (4★, vid hamnen, frukost)",
                "price": "ca 1 700–2 400 kr/natt",
                "parking": _PARKING_LA_SPEZIA,
                "address": "NH La Spezia, Via XX Settembre 2, 19124 La Spezia, Italy",
                "maps_query": _maps_link("NH La Spezia, Via XX Settembre 2, 19124 La Spezia, Italy"),
                "drive": _drive("Comosjön", 185, 130),
                "highlights": [
                    "Vandra Sentiero Azzurro (kustleden) mellan byarna",
                    "Bada i Monterosso eller Vernazza",
                    "Båt mellan de fem byarna",
                    "Glass i Manarola med utsikt",
                ],
            },
            {
                "name": "Nice & Franska Rivieran (inkl. dagsutflykt Saint-Tropez)",
                "nights": "9 nätter, 25 juli–3 augusti",
                "hotel": "Albert 1er Hotel Nice (4★, 2 min till stranden, triple-rum)",
                "price": "ca 1 800–2 400 kr/natt",
                "parking": _PARKING_NICE,
                "address": "Albert 1er Hotel Nice, 4 Avenue Max Gallo, 06000 Nice, France",
                "maps_query": _maps_link("Albert 1er Hotel Nice, 4 Avenue Max Gallo, 06000 Nice, France"),
                "drive": _drive("Cinque Terre / Ligurien", 230, 165),
                "highlights": [
                    "Bad vid Castel Plage eller Promenade des Anglais",
                    "Promenera Vieux Nice och marknaden Cours Saleya",
                    "Dagsutflykt med bil till Saint-Tropez (ca 1 tim 30 min enkel väg)",
                    "Glass på gamla stans gränder",
                ],
            },
            _milano_leg("Nice & Franska Rivieran", 340, 225),
        ],
    },
    {
        "id": "plan-c",
        "title": "C. Lite mer äventyr",
        "subtitle": "5 etapper – samma strandtid som klassikern, men med ett extra stopp i Alperna och kort stadsstopp sista kvällen.",
        "summary": (
            "Lika mycket strandtid i Ligurien och Nice som de andra "
            "planerna, men med ett eget stopp i Saint-Tropez och en "
            "svalkande avstickare till Courmayeur i Alperna, innan ett "
            "kort stopp i Milano sista kvällen – mer omväxling, men också "
            "mer körning."
        ),
        "beaches": [_BEACH_MONTEROSSO, _BEACH_CASTEL_PLAGE, _BEACH_PAMPELONNE],
        "legs": [
            {
                "name": "Cinque Terre / Ligurien",
                "nights": "6 nätter, 16–22 juli",
                "hotel": "NH La Spezia (4★, vid hamnen, frukost)",
                "price": "ca 1 700–2 400 kr/natt",
                "parking": _PARKING_LA_SPEZIA,
                "address": "NH La Spezia, Via XX Settembre 2, 19124 La Spezia, Italy",
                "maps_query": _maps_link("NH La Spezia, Via XX Settembre 2, 19124 La Spezia, Italy"),
                "drive": _drive("Bergamo flygplats", 225, 160),
                "highlights": [
                    "Vandra Sentiero Azzurro (kustleden) mellan byarna",
                    "Bada i Monterosso eller Vernazza",
                    "Båt mellan de fem byarna",
                    "Glass i Manarola med utsikt",
                ],
            },
            {
                "name": "Nice & Franska Rivieran",
                "nights": "7 nätter, 22–29 juli",
                "hotel": "Albert 1er Hotel Nice (4★, 2 min till stranden, triple-rum)",
                "price": "ca 1 800–2 400 kr/natt",
                "parking": _PARKING_NICE,
                "address": "Albert 1er Hotel Nice, 4 Avenue Max Gallo, 06000 Nice, France",
                "maps_query": _maps_link("Albert 1er Hotel Nice, 4 Avenue Max Gallo, 06000 Nice, France"),
                "drive": _drive("Cinque Terre / Ligurien", 230, 165),
                "highlights": [
                    "Bad vid Castel Plage eller Promenade des Anglais",
                    "Promenera Vieux Nice och marknaden Cours Saleya",
                    "Dagsutflykt till Antibes eller Villefranche-sur-Mer",
                    "Glass på gamla stans gränder",
                ],
            },
            {
                "name": "Saint-Tropez / Provence",
                "nights": "2 nätter, 29–31 juli",
                "hotel": "Best Western Premier Montfleuri (4★, vid havet, familjerum)",
                "price": "ca 2 000–2 700 kr/natt",
                "parking": _PARKING_SAINTE_MAXIME,
                "address": "Best Western Premier Montfleuri, 3 Avenue Montfleuri, 83120 Sainte-Maxime, France",
                "maps_query": _maps_link("Best Western Premier Montfleuri, 3 Avenue Montfleuri, 83120 Sainte-Maxime, France"),
                "drive": _drive("Nice & Franska Rivieran", 110, 90),
                "highlights": [
                    "Bad på Pampelonnestranden",
                    "Promenera gamla hamnen i Saint-Tropez",
                    "Marknad på Place des Lices",
                ],
            },
            {
                "name": "Courmayeur / Alperna",
                "nights": "3 nätter, 31 juli–3 augusti",
                "hotel": "Hotel Berthod (4★, mitt i centrum, frukost)",
                "price": "ca 2 700–3 100 kr/natt",
                "parking": _PARKING_COURMAYEUR,
                "address": "Hotel Berthod, Via Mario Puchoz 11, 11013 Courmayeur, Italy",
                "maps_query": _maps_link("Hotel Berthod, Via Mario Puchoz 11, 11013 Courmayeur, Italy"),
                "drive": _drive("Saint-Tropez / Provence", 330, 225),
                "highlights": [
                    "Skyway Monte Bianco – linbana med utsikt över Mont Blanc",
                    "Lätta vandringar med svalkande bergsluft",
                    "Glass i centrum av Courmayeur",
                ],
            },
            _milano_leg("Courmayeur / Alperna", 160, 115),
        ],
    },
    {
        "id": "plan-d",
        "title": "D. Stora turen",
        "subtitle": "6 etapper – mest variation: sjö, strand, storstad, ytterligare strand, berg och kort stadsstopp sista kvällen.",
        "summary": (
            "Allt på en resa: Comosjön, Cinque Terre, Nice, Saint-Tropez, "
            "Courmayeur i Alperna och ett kort stopp i Milano sista "
            "kvällen – mest omväxling av alla planer, men också mest "
            "körning (ca 14 timmar totalt). Bäst om familjen gillar att "
            "se mycket olika och inte är rädd för bilkörning."
        ),
        "beaches": [_BEACH_VILLA_OLMO, _BEACH_MONTEROSSO, _BEACH_CASTEL_PLAGE, _BEACH_PAMPELONNE],
        "legs": [
            {
                "name": "Comosjön",
                "nights": "2 nätter, 16–18 juli",
                "hotel": "Hotel Barchetta Excelsior (4★, vid sjön, frukost)",
                "price": "ca 2 200–2 600 kr/natt",
                "parking": _PARKING_COMO,
                "address": "Hotel Barchetta Excelsior, Piazza Cavour 1, 22100 Como, Italy",
                "maps_query": _maps_link("Hotel Barchetta Excelsior, Piazza Cavour 1, 22100 Como, Italy"),
                "drive": _drive("Bergamo flygplats", 50, 50),
                "highlights": [
                    "Båttur på Comosjön",
                    "Bad vid sjöns stränder",
                    "Dagsutflykt till Bellagio",
                    "Glass längs hamnpromenaden",
                ],
            },
            {
                "name": "Cinque Terre / Ligurien",
                "nights": "5 nätter, 18–23 juli",
                "hotel": "NH La Spezia (4★, vid hamnen, frukost)",
                "price": "ca 1 700–2 400 kr/natt",
                "parking": _PARKING_LA_SPEZIA,
                "address": "NH La Spezia, Via XX Settembre 2, 19124 La Spezia, Italy",
                "maps_query": _maps_link("NH La Spezia, Via XX Settembre 2, 19124 La Spezia, Italy"),
                "drive": _drive("Comosjön", 185, 130),
                "highlights": [
                    "Vandra Sentiero Azzurro (kustleden) mellan byarna",
                    "Bada i Monterosso eller Vernazza",
                    "Båt mellan de fem byarna",
                    "Glass i Manarola med utsikt",
                ],
            },
            {
                "name": "Nice & Franska Rivieran",
                "nights": "6 nätter, 23–29 juli",
                "hotel": "Albert 1er Hotel Nice (4★, 2 min till stranden, triple-rum)",
                "price": "ca 1 800–2 400 kr/natt",
                "parking": _PARKING_NICE,
                "address": "Albert 1er Hotel Nice, 4 Avenue Max Gallo, 06000 Nice, France",
                "maps_query": _maps_link("Albert 1er Hotel Nice, 4 Avenue Max Gallo, 06000 Nice, France"),
                "drive": _drive("Cinque Terre / Ligurien", 230, 165),
                "highlights": [
                    "Bad vid Castel Plage eller Promenade des Anglais",
                    "Promenera Vieux Nice och marknaden Cours Saleya",
                    "Dagsutflykt till Antibes eller Villefranche-sur-Mer",
                    "Glass på gamla stans gränder",
                ],
            },
            {
                "name": "Saint-Tropez / Provence",
                "nights": "2 nätter, 29–31 juli",
                "hotel": "Best Western Premier Montfleuri (4★, vid havet, familjerum)",
                "price": "ca 2 000–2 700 kr/natt",
                "parking": _PARKING_SAINTE_MAXIME,
                "address": "Best Western Premier Montfleuri, 3 Avenue Montfleuri, 83120 Sainte-Maxime, France",
                "maps_query": _maps_link("Best Western Premier Montfleuri, 3 Avenue Montfleuri, 83120 Sainte-Maxime, France"),
                "drive": _drive("Nice & Franska Rivieran", 110, 90),
                "highlights": [
                    "Bad på Pampelonnestranden",
                    "Promenera gamla hamnen i Saint-Tropez",
                    "Marknad på Place des Lices",
                ],
            },
            {
                "name": "Courmayeur / Alperna",
                "nights": "3 nätter, 31 juli–3 augusti",
                "hotel": "Hotel Berthod (4★, mitt i centrum, frukost)",
                "price": "ca 2 700–3 100 kr/natt",
                "parking": _PARKING_COURMAYEUR,
                "address": "Hotel Berthod, Via Mario Puchoz 11, 11013 Courmayeur, Italy",
                "maps_query": _maps_link("Hotel Berthod, Via Mario Puchoz 11, 11013 Courmayeur, Italy"),
                "drive": _drive("Saint-Tropez / Provence", 330, 225),
                "highlights": [
                    "Skyway Monte Bianco – linbana med utsikt över Mont Blanc",
                    "Lätta vandringar med svalkande bergsluft",
                    "Glass i centrum av Courmayeur",
                ],
            },
            _milano_leg("Courmayeur / Alperna", 160, 115),
        ],
    },
]

# Lägg på "total_drive" (summerad körsträcka/-tid, inkl. sista dagens
# transfer Milano -> flygplats), "departure_transfer" samt "route_map"
# (en Google Maps-länk med hela bilrutten i ordning) på varje plan, så
# frontend inte behöver räkna/bygga ihop det själv.
for _plan in PLANS:
    _plan["departure_transfer"] = _DEPARTURE_TRANSFER
    _plan["total_drive"] = _total_drive(_plan["legs"], _DEPARTURE_TRANSFER)
    _plan["route_map"] = _route_map_link(
        [_BGY_AIRPORT_ADDRESS]
        + [leg["address"] for leg in _plan["legs"]]
        + [_BGY_AIRPORT_ADDRESS]
    )


def get_plans_with_lat_lon():
    """Returnerar PLANS samt den dummy-koordinat röst-tabellen kräver."""
    return PLANS, _BERGAMO_LAT, _BERGAMO_LON

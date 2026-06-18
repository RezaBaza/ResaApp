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

OBS: körsträckorna/-tiderna är UPPSKATTADE bilvägs-avstånd (ingen
ruttplanerare/API är inkopplad), avrundade till närmaste 5 km/5 min och
markerade med "ca" – verklig tid beror på trafik, vägval och stopp.
"""

# Dummy-koordinat (Bergamo flygplats) – krävs av votes-tabellen men
# används inte till något för planer (ingen karta visas baserat på den).
_BERGAMO_LAT = 45.6739
_BERGAMO_LON = 9.7042


def _maps_link(address):
    return f"https://www.google.com/maps/search/?api=1&query={address}"


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


def _total_drive(legs):
    """Summerar alla "drive"-poster i en plan till en total km/tid."""
    total_km = sum(leg["drive"]["km"] for leg in legs if leg.get("drive"))
    total_minutes = sum(
        leg["drive"]["minutes"] for leg in legs if leg.get("drive")
    )
    return {
        "km": total_km,
        "minutes": total_minutes,
        "time": _fmt_drive_time(total_minutes),
    }


PLANS = [
    {
        "id": "plan-a",
        "title": "A. Lugn & solig",
        "subtitle": "3 etapper – max strand & avslappning, inga berg, ingen storstad. Perfekt om Viana får bestämma.",
        "summary": (
            "Den mest avslappnade rutten: ingen storstad, inga berg – bara "
            "vandring längs kustleden och bad i Cinque Terre, sol och bad "
            "längs Franska Rivieran, och ett kort, lugnt stopp i Bergamos "
            "gamla stad innan hemflyget. Minst körning av alla fyra planer."
        ),
        "legs": [
            {
                "name": "Cinque Terre / Ligurien",
                "nights": "9 nätter, 16–25 juli",
                "hotel": "NH La Spezia (4★, vid hamnen, frukost)",
                "price": "ca 1 700–2 400 kr/natt",
                "maps_query": _maps_link("NH+La+Spezia%2C+Via+XX+Settembre+2%2C+19124+La+Spezia%2C+Italy"),
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
                "maps_query": _maps_link("Albert+1er+Hotel+Nice%2C+4+Avenue+Max+Gallo%2C+06000+Nice%2C+France"),
                "drive": _drive("Cinque Terre / Ligurien", 230, 165),
                "highlights": [
                    "Bad vid Castel Plage eller Promenade des Anglais",
                    "Promenera Vieux Nice och marknaden Cours Saleya",
                    "Dagsutflykt till Antibes eller Villefranche-sur-Mer",
                    "Glass på gamla stans gränder",
                ],
            },
            {
                "name": "Bergamo",
                "nights": "2 nätter, 3–5 augusti",
                "hotel": "Hotel Excelsior San Marco (4★, centralt, frukost)",
                "price": "ca 1 700–2 300 kr/natt",
                "maps_query": _maps_link("Hotel+Excelsior+San+Marco%2C+Piazzale+della+Repubblica+6%2C+24122+Bergamo%2C+Italy"),
                "drive": _drive("Nice & Franska Rivieran", 390, 255),
                "highlights": [
                    "Åk linbanan upp till Città Alta (gamla stan)",
                    "Utsikt från stadsmurarna",
                    "Glass på Piazza Vecchia",
                ],
            },
        ],
    },
    {
        "id": "plan-b",
        "title": "B. Balanserad klassiker",
        "subtitle": "4 etapper – en skvätt Comosjön, sen gott om strandtid i Ligurien och Nice.",
        "summary": (
            "Samma lugna kustkänsla som "
            "“A” men med en kort, vacker inledning vid Comosjön "
            "innan stranden tar vid. Plus en dagsutflykt till Saint-Tropez "
            "inbakad i Nice-etappen, utan att lägga till ett eget hotellstopp."
        ),
        "legs": [
            {
                "name": "Comosjön",
                "nights": "2 nätter, 16–18 juli",
                "hotel": "Hotel Barchetta Excelsior (4★, vid sjön, frukost)",
                "price": "ca 2 200–2 600 kr/natt",
                "maps_query": _maps_link("Hotel+Barchetta+Excelsior%2C+Piazza+Cavour+1%2C+22100+Como%2C+Italy"),
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
                "maps_query": _maps_link("NH+La+Spezia%2C+Via+XX+Settembre+2%2C+19124+La+Spezia%2C+Italy"),
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
                "maps_query": _maps_link("Albert+1er+Hotel+Nice%2C+4+Avenue+Max+Gallo%2C+06000+Nice%2C+France"),
                "drive": _drive("Cinque Terre / Ligurien", 230, 165),
                "highlights": [
                    "Bad vid Castel Plage eller Promenade des Anglais",
                    "Promenera Vieux Nice och marknaden Cours Saleya",
                    "Dagsutflykt med bil till Saint-Tropez (ca 1 tim 30 min enkel väg)",
                    "Glass på gamla stans gränder",
                ],
            },
            {
                "name": "Bergamo",
                "nights": "2 nätter, 3–5 augusti",
                "hotel": "Hotel Excelsior San Marco (4★, centralt, frukost)",
                "price": "ca 1 700–2 300 kr/natt",
                "maps_query": _maps_link("Hotel+Excelsior+San+Marco%2C+Piazzale+della+Repubblica+6%2C+24122+Bergamo%2C+Italy"),
                "drive": _drive("Nice & Franska Rivieran", 390, 255),
                "highlights": [
                    "Åk linbanan upp till Città Alta (gamla stan)",
                    "Utsikt från stadsmurarna",
                    "Glass på Piazza Vecchia",
                ],
            },
        ],
    },
    {
        "id": "plan-c",
        "title": "C. Lite mer äventyr",
        "subtitle": "5 etapper – samma strandtid som klassikern, men med ett extra stopp i Alperna.",
        "summary": (
            "Lika mycket strandtid i Ligurien och Nice som de andra "
            "planerna, men med ett eget stopp i Saint-Tropez och en "
            "svalkande avstickare till Courmayeur i Alperna innan "
            "hemresan – mer omväxling, men också mer körning."
        ),
        "legs": [
            {
                "name": "Cinque Terre / Ligurien",
                "nights": "6 nätter, 16–22 juli",
                "hotel": "NH La Spezia (4★, vid hamnen, frukost)",
                "price": "ca 1 700–2 400 kr/natt",
                "maps_query": _maps_link("NH+La+Spezia%2C+Via+XX+Settembre+2%2C+19124+La+Spezia%2C+Italy"),
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
                "maps_query": _maps_link("Albert+1er+Hotel+Nice%2C+4+Avenue+Max+Gallo%2C+06000+Nice%2C+France"),
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
                "maps_query": _maps_link("Best+Western+Premier+Montfleuri%2C+3+Avenue+Montfleuri%2C+83120+Sainte-Maxime%2C+France"),
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
                "maps_query": _maps_link("Hotel+Berthod%2C+Via+Mario+Puchoz+11%2C+11013+Courmayeur%2C+Italy"),
                "drive": _drive("Saint-Tropez / Provence", 330, 225),
                "highlights": [
                    "Skyway Monte Bianco – linbana med utsikt över Mont Blanc",
                    "Lätta vandringar med svalkande bergsluft",
                    "Glass i centrum av Courmayeur",
                ],
            },
            {
                "name": "Bergamo",
                "nights": "2 nätter, 3–5 augusti",
                "hotel": "Hotel Excelsior San Marco (4★, centralt, frukost)",
                "price": "ca 1 700–2 300 kr/natt",
                "maps_query": _maps_link("Hotel+Excelsior+San+Marco%2C+Piazzale+della+Repubblica+6%2C+24122+Bergamo%2C+Italy"),
                "drive": _drive("Courmayeur / Alperna", 165, 130),
                "highlights": [
                    "Åk linbanan upp till Città Alta (gamla stan)",
                    "Utsikt från stadsmurarna",
                    "Glass på Piazza Vecchia",
                ],
            },
        ],
    },
    {
        "id": "plan-d",
        "title": "D. Stora turen",
        "subtitle": "6 etapper – mest variation: sjö, strand, storstad, ytterligare strand och berg.",
        "summary": (
            "Allt på en resa: Comosjön, Cinque Terre, Nice, Saint-Tropez "
            "och Courmayeur i Alperna – mest omväxling av alla planer, men "
            "också mest körning (ca 13 timmar totalt). Bäst om familjen "
            "gillar att se mycket olika och inte är rädd för bilkörning."
        ),
        "legs": [
            {
                "name": "Comosjön",
                "nights": "2 nätter, 16–18 juli",
                "hotel": "Hotel Barchetta Excelsior (4★, vid sjön, frukost)",
                "price": "ca 2 200–2 600 kr/natt",
                "maps_query": _maps_link("Hotel+Barchetta+Excelsior%2C+Piazza+Cavour+1%2C+22100+Como%2C+Italy"),
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
                "maps_query": _maps_link("NH+La+Spezia%2C+Via+XX+Settembre+2%2C+19124+La+Spezia%2C+Italy"),
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
                "maps_query": _maps_link("Albert+1er+Hotel+Nice%2C+4+Avenue+Max+Gallo%2C+06000+Nice%2C+France"),
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
                "maps_query": _maps_link("Best+Western+Premier+Montfleuri%2C+3+Avenue+Montfleuri%2C+83120+Sainte-Maxime%2C+France"),
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
                "maps_query": _maps_link("Hotel+Berthod%2C+Via+Mario+Puchoz+11%2C+11013+Courmayeur%2C+Italy"),
                "drive": _drive("Saint-Tropez / Provence", 330, 225),
                "highlights": [
                    "Skyway Monte Bianco – linbana med utsikt över Mont Blanc",
                    "Lätta vandringar med svalkande bergsluft",
                    "Glass i centrum av Courmayeur",
                ],
            },
            {
                "name": "Bergamo",
                "nights": "2 nätter, 3–5 augusti",
                "hotel": "Hotel Excelsior San Marco (4★, centralt, frukost)",
                "price": "ca 1 700–2 300 kr/natt",
                "maps_query": _maps_link("Hotel+Excelsior+San+Marco%2C+Piazzale+della+Repubblica+6%2C+24122+Bergamo%2C+Italy"),
                "drive": _drive("Courmayeur / Alperna", 165, 130),
                "highlights": [
                    "Åk linbanan upp till Città Alta (gamla stan)",
                    "Utsikt från stadsmurarna",
                    "Glass på Piazza Vecchia",
                ],
            },
        ],
    },
]

# Lägg på "total_drive" (summerad körsträcka/-tid) på varje plan, så
# frontend inte behöver räkna ihop det själv.
for _plan in PLANS:
    _plan["total_drive"] = _total_drive(_plan["legs"])


def get_plans_with_lat_lon():
    """Returnerar PLANS samt den dummy-koordinat röst-tabellen kräver."""
    return PLANS, _BERGAMO_LAT, _BERGAMO_LON

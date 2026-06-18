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
"""

# Dummy-koordinat (Bergamo flygplats) – krävs av votes-tabellen men
# används inte till något för planer (ingen karta visas baserat på den).
_BERGAMO_LAT = 45.6739
_BERGAMO_LON = 9.7042


def _maps_link(address):
    return f"https://www.google.com/maps/search/?api=1&query={address}"


PLANS = [
    {
        "id": "plan-a",
        "title": "A. Lugn & solig",
        "subtitle": "3 etapper – max strand & avslappning, inga berg, ingen storstad. Perfekt om Viana får bestämma.",
        "legs": [
            {
                "name": "Cinque Terre / Ligurien",
                "nights": "9 nätter, 16–25 juli",
                "hotel": "NH La Spezia (4★, vid hamnen, frukost)",
                "price": "ca 1 700–2 400 kr/natt",
                "maps_query": _maps_link("NH+La+Spezia%2C+Via+XX+Settembre+2%2C+19124+La+Spezia%2C+Italy"),
            },
            {
                "name": "Nice & Franska Rivieran",
                "nights": "9 nätter, 25 juli–3 augusti",
                "hotel": "Albert 1er Hotel Nice (4★, 2 min till stranden, triple-rum)",
                "price": "ca 1 800–2 400 kr/natt",
                "maps_query": _maps_link("Albert+1er+Hotel+Nice%2C+4+Avenue+Max+Gallo%2C+06000+Nice%2C+France"),
            },
            {
                "name": "Bergamo",
                "nights": "2 nätter, 3–5 augusti",
                "hotel": "Hotel Excelsior San Marco (4★, centralt, frukost)",
                "price": "ca 1 700–2 300 kr/natt",
                "maps_query": _maps_link("Hotel+Excelsior+San+Marco%2C+Piazzale+della+Repubblica+6%2C+24122+Bergamo%2C+Italy"),
            },
        ],
    },
    {
        "id": "plan-b",
        "title": "B. Balanserad klassiker",
        "subtitle": "4 etapper – en skvätt Comosjön, sen gott om strandtid i Ligurien och Nice.",
        "legs": [
            {
                "name": "Comosjön",
                "nights": "2 nätter, 16–18 juli",
                "hotel": "Hotel Barchetta Excelsior (4★, vid sjön, frukost)",
                "price": "ca 2 200–2 600 kr/natt",
                "maps_query": _maps_link("Hotel+Barchetta+Excelsior%2C+Piazza+Cavour+1%2C+22100+Como%2C+Italy"),
            },
            {
                "name": "Cinque Terre / Ligurien",
                "nights": "7 nätter, 18–25 juli",
                "hotel": "NH La Spezia (4★, vid hamnen, frukost)",
                "price": "ca 1 700–2 400 kr/natt",
                "maps_query": _maps_link("NH+La+Spezia%2C+Via+XX+Settembre+2%2C+19124+La+Spezia%2C+Italy"),
            },
            {
                "name": "Nice & Franska Rivieran (inkl. dagsutflykt Saint-Tropez)",
                "nights": "9 nätter, 25 juli–3 augusti",
                "hotel": "Albert 1er Hotel Nice (4★, 2 min till stranden, triple-rum)",
                "price": "ca 1 800–2 400 kr/natt",
                "maps_query": _maps_link("Albert+1er+Hotel+Nice%2C+4+Avenue+Max+Gallo%2C+06000+Nice%2C+France"),
            },
            {
                "name": "Bergamo",
                "nights": "2 nätter, 3–5 augusti",
                "hotel": "Hotel Excelsior San Marco (4★, centralt, frukost)",
                "price": "ca 1 700–2 300 kr/natt",
                "maps_query": _maps_link("Hotel+Excelsior+San+Marco%2C+Piazzale+della+Repubblica+6%2C+24122+Bergamo%2C+Italy"),
            },
        ],
    },
    {
        "id": "plan-c",
        "title": "C. Lite mer äventyr",
        "subtitle": "5 etapper – samma strandtid som klassikern, men med ett extra stopp i Alperna.",
        "legs": [
            {
                "name": "Cinque Terre / Ligurien",
                "nights": "6 nätter, 16–22 juli",
                "hotel": "NH La Spezia (4★, vid hamnen, frukost)",
                "price": "ca 1 700–2 400 kr/natt",
                "maps_query": _maps_link("NH+La+Spezia%2C+Via+XX+Settembre+2%2C+19124+La+Spezia%2C+Italy"),
            },
            {
                "name": "Nice & Franska Rivieran",
                "nights": "7 nätter, 22–29 juli",
                "hotel": "Albert 1er Hotel Nice (4★, 2 min till stranden, triple-rum)",
                "price": "ca 1 800–2 400 kr/natt",
                "maps_query": _maps_link("Albert+1er+Hotel+Nice%2C+4+Avenue+Max+Gallo%2C+06000+Nice%2C+France"),
            },
            {
                "name": "Saint-Tropez / Provence",
                "nights": "2 nätter, 29–31 juli",
                "hotel": "Best Western Premier Montfleuri (4★, vid havet, familjerum)",
                "price": "ca 2 000–2 700 kr/natt",
                "maps_query": _maps_link("Best+Western+Premier+Montfleuri%2C+3+Avenue+Montfleuri%2C+83120+Sainte-Maxime%2C+France"),
            },
            {
                "name": "Courmayeur / Alperna",
                "nights": "3 nätter, 31 juli–3 augusti",
                "hotel": "Hotel Berthod (4★, mitt i centrum, frukost)",
                "price": "ca 2 700–3 100 kr/natt",
                "maps_query": _maps_link("Hotel+Berthod%2C+Via+Mario+Puchoz+11%2C+11013+Courmayeur%2C+Italy"),
            },
            {
                "name": "Bergamo",
                "nights": "2 nätter, 3–5 augusti",
                "hotel": "Hotel Excelsior San Marco (4★, centralt, frukost)",
                "price": "ca 1 700–2 300 kr/natt",
                "maps_query": _maps_link("Hotel+Excelsior+San+Marco%2C+Piazzale+della+Repubblica+6%2C+24122+Bergamo%2C+Italy"),
            },
        ],
    },
    {
        "id": "plan-d",
        "title": "D. Stora turen",
        "subtitle": "6 etapper – mest variation: sjö, strand, storstad, ytterligare strand och berg.",
        "legs": [
            {
                "name": "Comosjön",
                "nights": "2 nätter, 16–18 juli",
                "hotel": "Hotel Barchetta Excelsior (4★, vid sjön, frukost)",
                "price": "ca 2 200–2 600 kr/natt",
                "maps_query": _maps_link("Hotel+Barchetta+Excelsior%2C+Piazza+Cavour+1%2C+22100+Como%2C+Italy"),
            },
            {
                "name": "Cinque Terre / Ligurien",
                "nights": "5 nätter, 18–23 juli",
                "hotel": "NH La Spezia (4★, vid hamnen, frukost)",
                "price": "ca 1 700–2 400 kr/natt",
                "maps_query": _maps_link("NH+La+Spezia%2C+Via+XX+Settembre+2%2C+19124+La+Spezia%2C+Italy"),
            },
            {
                "name": "Nice & Franska Rivieran",
                "nights": "6 nätter, 23–29 juli",
                "hotel": "Albert 1er Hotel Nice (4★, 2 min till stranden, triple-rum)",
                "price": "ca 1 800–2 400 kr/natt",
                "maps_query": _maps_link("Albert+1er+Hotel+Nice%2C+4+Avenue+Max+Gallo%2C+06000+Nice%2C+France"),
            },
            {
                "name": "Saint-Tropez / Provence",
                "nights": "2 nätter, 29–31 juli",
                "hotel": "Best Western Premier Montfleuri (4★, vid havet, familjerum)",
                "price": "ca 2 000–2 700 kr/natt",
                "maps_query": _maps_link("Best+Western+Premier+Montfleuri%2C+3+Avenue+Montfleuri%2C+83120+Sainte-Maxime%2C+France"),
            },
            {
                "name": "Courmayeur / Alperna",
                "nights": "3 nätter, 31 juli–3 augusti",
                "hotel": "Hotel Berthod (4★, mitt i centrum, frukost)",
                "price": "ca 2 700–3 100 kr/natt",
                "maps_query": _maps_link("Hotel+Berthod%2C+Via+Mario+Puchoz+11%2C+11013+Courmayeur%2C+Italy"),
            },
            {
                "name": "Bergamo",
                "nights": "2 nätter, 3–5 augusti",
                "hotel": "Hotel Excelsior San Marco (4★, centralt, frukost)",
                "price": "ca 1 700–2 300 kr/natt",
                "maps_query": _maps_link("Hotel+Excelsior+San+Marco%2C+Piazzale+della+Repubblica+6%2C+24122+Bergamo%2C+Italy"),
            },
        ],
    },
]


def get_plans_with_lat_lon():
    """Returnerar PLANS samt den dummy-koordinat röst-tabellen kräver."""
    return PLANS, _BERGAMO_LAT, _BERGAMO_LON
